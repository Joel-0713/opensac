import os
from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

from langchain_core.messages import AnyMessage, ToolMessage, HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

# Mocked Health Table
SERVICE_HEALTH = {
    "auth": "degraded - high latency",
    "database": "healthy",
    "payments": "healthy"
}

@tool
def query_service_health(service_name: str) -> str:
    """Checks the health of a specific backend service."""
    if service_name not in SERVICE_HEALTH:
        return f"Unknown service: {service_name}"
    return f"Service {service_name} is {SERVICE_HEALTH[service_name]}"

@tool
def search_remediation_runbooks(query: str) -> str:
    """Searches internal runbooks for remediation steps matching the query."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return "Database URL not configured."
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        task_type="RETRIEVAL_QUERY",
    )
    vector = embeddings.embed_query(query)
    
    with ConnectionPool(db_url, min_size=1, max_size=5, kwargs={"prepare_threshold": None}) as pool:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT content FROM match_incident_docs(%s, %s, %s)",
                    (str(vector), 2, "{}")
                )
                results = cur.fetchall()
                if not results:
                    return "No relevant runbooks found."
                return "\n".join([r[0] for r in results])

@tool
def escalate_ticket(ticket_title: str, severity: str) -> str:
    """Escalates the incident by opening a ticket and paging the on-call team. CRITICAL: requires approval."""
    return f"Ticket '{ticket_title}' (Severity {severity}) escalated to on-call team."

safe_tools_list = [query_service_health, search_remediation_runbooks]
sensitive_tools_list = [escalate_ticket]
all_tools = safe_tools_list + sensitive_tools_list

llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
llm_with_tools = llm.bind_tools(all_tools)

def extract_text(content) -> str:
    if isinstance(content, list):
        return " ".join([c.get("text", "") for c in content if "text" in c])
    return str(content)

def agent_node(state: AgentState):
    messages = state["messages"]
    if not messages:
        return {"messages": []}
    
    # System prompt enforcing health check then runbooks
    sys_prompt = HumanMessage(content="You are an autonomous incident triage agent. Always check service health first, then search runbooks. If manual intervention is needed or service stays degraded, use escalate_ticket.")
    
    response = llm_with_tools.invoke([sys_prompt] + messages)
    return {"messages": [response]}

def route_tools(state: AgentState) -> Literal["safe_tools", "sensitive_tools", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return END
    
    # Change 6: If ANY tool call is sensitive, route the whole message to sensitive_tools
    sensitive_names = [t.name for t in sensitive_tools_list]
    for tc in last_message.tool_calls:
        if tc["name"] in sensitive_names:
            return "sensitive_tools"
            
    return "safe_tools"

def execute_tools(state: AgentState, tools_to_run):
    messages = state["messages"]
    last_message = messages[-1]
    responses = []
    
    tool_map = {t.name: t for t in tools_to_run}
    for tc in last_message.tool_calls:
        tool_fn = tool_map.get(tc["name"])
        if tool_fn:
            result = tool_fn.invoke(tc["args"])
            responses.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
        else:
            # If tool is not in the allowed list for this node, return error
            responses.append(ToolMessage(content=f"Error: Tool {tc['name']} not available in this node.", tool_call_id=tc["id"]))
            
    return {"messages": responses}

def safe_tools_node(state: AgentState):
    return execute_tools(state, safe_tools_list)

def sensitive_tools_node(state: AgentState):
    return execute_tools(state, all_tools)

def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("safe_tools", safe_tools_node)
    builder.add_node("sensitive_tools", sensitive_tools_node)
    
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_tools)
    builder.add_edge("safe_tools", "agent")
    builder.add_edge("sensitive_tools", "agent")
    
    return builder

def get_agent_app():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL must be set.")
        
    pool = ConnectionPool(db_url, max_size=10, autocommit=True, kwargs={"prepare_threshold": None})
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    
    builder = build_graph()
    app = builder.compile(checkpointer=checkpointer, interrupt_before=["sensitive_tools"])
    return app

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import gradio as gr
from langchain_core.messages import HumanMessage, ToolMessage
from agent import get_agent_app, sensitive_tools_list

app = FastAPI()

try:
    agent_graph = get_agent_app()
except ValueError as e:
    print(f"Warning: {e} - Application may not function correctly.")
    agent_graph = None

class ChatRequest(BaseModel):
    thread_id: str
    message: str

class ApproveRequest(BaseModel):
    thread_id: str
    approved: bool
    rejection_reason: str = None

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/chat")
def chat(req: ChatRequest):
    if not agent_graph:
        raise HTTPException(status_code=500, detail="Agent graph not initialized")
        
    config = {"configurable": {"thread_id": req.thread_id}}
    state = agent_graph.get_state(config)
    
    # If starting fresh, invoke with the human message
    if not state.next:
        result = agent_graph.invoke({"messages": [HumanMessage(content=req.message)]}, config)
        state = agent_graph.get_state(config)
    
    if "sensitive_tools" in state.next:
        last_msg = state.values["messages"][-1]
        pending = [tc for tc in last_msg.tool_calls if tc["name"] in [t.name for t in sensitive_tools_list]]
        return {"status": "AWAITING_APPROVAL", "pending_actions": pending}
        
    return {"status": "COMPLETED", "response": state.values["messages"][-1].content}

@app.post("/approve")
def approve(req: ApproveRequest):
    if not agent_graph:
        raise HTTPException(status_code=500, detail="Agent graph not initialized")
        
    config = {"configurable": {"thread_id": req.thread_id}}
    state = agent_graph.get_state(config)
    
    if "sensitive_tools" not in state.next:
        raise HTTPException(status_code=400, detail="Nothing pending for this thread")
        
    if req.approved:
        agent_graph.invoke(None, config)
        return {"status": "RESOLVED"}
    else:
        last_msg = state.values["messages"][-1]
        tool_messages = []
        for tc in last_msg.tool_calls:
            tool_messages.append(ToolMessage(
                content=f"Rejected by engineer: {req.rejection_reason}",
                tool_call_id=tc["id"]
            ))
        
        agent_graph.update_state(config, {"messages": tool_messages}, as_node="sensitive_tools")
        agent_graph.invoke(None, config)
        return {"status": "REJECTED_AND_RESUMED"}

# Gradio UI
def trigger_triage(thread_id, message):
    if not thread_id or not message:
        return "Please provide both Thread ID and Message", "Error"
        
    import httpx
    try:
        resp = httpx.post("http://localhost:7860/chat", json={"thread_id": thread_id, "message": message}, timeout=30.0)
        data = resp.json()
        if data["status"] == "AWAITING_APPROVAL":
            return f"Agent paused. Pending actions: {data['pending_actions']}", data["status"]
        return data.get("response", "Error"), data["status"]
    except Exception as e:
        return str(e), "Error"

def handle_approve(thread_id, approved, reason):
    if not thread_id:
        return "Need Thread ID", "Error"
        
    import httpx
    try:
        resp = httpx.post("http://localhost:7860/approve", json={
            "thread_id": thread_id,
            "approved": approved,
            "rejection_reason": reason if not approved else None
        }, timeout=30.0)
        if resp.status_code == 400:
            return resp.json()["detail"], "Error"
        return "Action Processed", resp.json()["status"]
    except Exception as e:
        return str(e), "Error"

with gr.Blocks() as ui:
    gr.Markdown("# Autonomous Incident Triage Agent")
    with gr.Row():
        thread_id = gr.Textbox(label="Thread ID", value="thread-1")
        message = gr.Textbox(label="Incident Description", value="Auth service is timing out. Escalate immediately.")
    
    with gr.Row():
        btn_trigger = gr.Button("Trigger Triage", variant="primary")
        
    status_label = gr.Label(label="Workflow State")
    output_log = gr.Markdown(label="Agent Log")
    
    with gr.Row():
        btn_approve = gr.Button("Approve Escalation", variant="secondary")
        btn_reject = gr.Button("Reject Action", variant="stop")
    reject_reason = gr.Textbox(label="Rejection Reason")
    
    btn_trigger.click(trigger_triage, inputs=[thread_id, message], outputs=[output_log, status_label])
    btn_approve.click(lambda tid: handle_approve(tid, True, ""), inputs=[thread_id], outputs=[output_log, status_label])
    btn_reject.click(lambda tid, r: handle_approve(tid, False, r), inputs=[thread_id, reject_reason], outputs=[output_log, status_label])

# Mount gradio
app = gr.mount_gradio_app(app, ui, path="/")

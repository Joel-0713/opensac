import pytest
from langchain_core.messages import AIMessage, ToolCall, ToolMessage
from agent import route_tools, AgentState

def test_route_tools_mixed_calls():
    # Simulate the LLM returning a mixed batch of tools
    tool_calls = [
        ToolCall(name="query_service_health", args={"service_name": "auth"}, id="call_1"),
        ToolCall(name="escalate_ticket", args={"ticket_title": "Down", "severity": "High"}, id="call_2")
    ]
    message = AIMessage(content="", tool_calls=tool_calls)
    state = AgentState(messages=[message])
    
    # Should route to sensitive_tools because escalate_ticket is present
    result = route_tools(state)
    assert result == "sensitive_tools"

def test_route_tools_safe_only():
    # Simulate the LLM returning only safe tools
    tool_calls = [
        ToolCall(name="query_service_health", args={"service_name": "auth"}, id="call_1")
    ]
    message = AIMessage(content="", tool_calls=tool_calls)
    state = AgentState(messages=[message])
    
    # Should route to safe_tools
    result = route_tools(state)
    assert result == "safe_tools"

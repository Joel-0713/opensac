# Design

The current logic assumes a single tool call per model generation or only checks the first call. If the model emits `[safe_tool, sensitive_tool]`, the entire message might bypass approval.

We will iterate over every tool call in `last_message.tool_calls`.
- If **any** tool is sensitive, route to `sensitive_tools`.
- Update `/chat` to extract all sensitive tool names for the `pending_actions` payload.
- Update `/approve` so that on rejection, we iterate over every pending tool call in the message and inject a `ToolMessage` for each one to satisfy LangGraph's requirement that every tool call ID receives a response.

# Proposal: harden-hitl-routing

## Scope
Modify the HITL approval routing behavior to strictly capture any sensitive tool call, even if it is batched with safe tool calls. This affects the `hitl-approval` capability.

## Rollback
Revert `route_tools` to only inspect `tool_calls[0]` and undo updates to the `/chat` and `/approve` handlers.

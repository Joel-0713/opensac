# Delta for hitl-approval

## MODIFIED Requirements

### Requirement: Sensitive actions require human approval
The agent MUST pause before executing a model message if ANY of its tool calls is sensitive,
and MUST NOT execute any sensitive tool without explicit approval for that thread.
(Previously: only the first tool call was inspected.)

#### Scenario: Mixed safe and sensitive calls
- GIVEN the model returns [query_service_health, escalate_ticket] in one message
- WHEN the graph runs
- THEN execution pauses for approval
- AND the approval payload lists escalate_ticket

#### Scenario: Rejection answers every pending call
- GIVEN a paused message with two tool calls
- WHEN an engineer rejects
- THEN each tool call receives a ToolMessage and no sensitive tool executes

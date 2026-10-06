# Delta for deployment

## ADDED Requirements

### Requirement: Bind to environment port
The service SHALL bind to the port provided in the `$PORT` environment variable.

#### Scenario: Port binding
- GIVEN the `$PORT` environment variable is set to 8080
- WHEN the service starts
- THEN it listens on port 8080

### Requirement: Secrets via environment
Secrets SHALL come only from environment variables; `.env` SHALL NOT be committed.

#### Scenario: No secrets in repo
- GIVEN the repository is checked out
- WHEN searching for `.env` or hardcoded keys
- THEN none are found in tracked files

### Requirement: Health check endpoint
The service SHALL expose a `GET /healthz` endpoint returning a 200 OK status without calling Gemini or the database.

#### Scenario: Render health check
- GIVEN the service is running
- WHEN a `GET /healthz` request is made
- THEN it returns a 200 OK status immediately

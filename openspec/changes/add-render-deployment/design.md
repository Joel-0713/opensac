# Design

We use a `render.yaml` blueprint to define a free web service.
- **Port:** Render passes the port as an environment variable `$PORT`. We must configure Uvicorn to listen on this port.
- **Health check:** Render requires a lightweight endpoint to confirm the service is running. We use `/healthz` which bypasses Gemini and the DB to ensure it responds quickly even during cold starts.

# Proposal: add-render-deployment

## Scope
Prepare deployment to Render's free tier. This affects the `deployment` capability.

## Rollback
Remove `render.yaml` and rollback any `/healthz` endpoints.

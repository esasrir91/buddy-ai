# Cloud Platforms

Any platform that runs a container can host a Buddy app. Build the image once
(see [Docker](docker.md)), push it, and supply your API keys as environment
secrets. The app serves `GET /status` and `POST /runs` on the port you expose
(default `7777`).

!!! note "Generic guidance"
    Buddy does not provide platform-specific deploy commands. The notes below
    are standard container-deployment steps — consult each provider's docs for
    exact CLI flags.

## Common checklist

1. **Build & push** your image to a registry the platform can pull from.
2. **Expose the port** your app serves on (`7777` in the examples).
3. **Set secrets** as environment variables (`OPENAI_API_KEY`, etc.) — never in
   the image.
4. **Bind to `0.0.0.0`** in `serve(...)`.
5. **Point health checks at `/status`**.

## Platform notes

| Platform | How you deploy | Secrets |
|----------|----------------|---------|
| **Render** | Web Service from a Dockerfile or image; set the port to `7777` | Environment tab / secret files |
| **Fly.io** | `fly launch` / `fly deploy` with a `[http_service]` `internal_port = 7777` | `fly secrets set OPENAI_API_KEY=...` |
| **Google Cloud Run** | Deploy the container image; Cloud Run injects `PORT` | Secret Manager → env vars |
| **AWS ECS / Fargate** | Task definition referencing the image, container port `7777` | Secrets Manager / SSM parameters |
| **Azure Container Instances** | Container group from the image | `--secure-environment-variables` |

!!! tip "Respect an injected PORT"
    Some platforms (e.g. Cloud Run) tell you which port to listen on via the
    `PORT` environment variable. Read it in your app script and pass it to
    `serve(...)`:

    ```python
    import os
    fastapi_app.serve(app, host="0.0.0.0", port=int(os.getenv("PORT", "7777")))
    ```

## Managed backends

For anything beyond a single instance, use the platform's managed services for
state instead of the pod's filesystem:

- **Postgres** (sessions, memory) via `DATABASE_URL`
- **Redis** via `REDIS_URL`
- A hosted **vector database** (e.g. Qdrant, Pinecone) for knowledge

This keeps multiple instances consistent and lets them restart safely.

## The workspace resources system

Buddy includes a workspace/infrastructure layer (`buddy.infra`,
`buddy.workspace`) driven by a `resources.py` file and the `buddy ws` /
`buddy start` CLI commands. It can declare and deploy resources across
environments (e.g. `dev`/`prd`) and infra types (e.g. `docker`, `aws`). If your
team already uses this workflow, see [Workspace Management](../cli/workspace.md);
otherwise the container-based approach above is the simplest path to production.

## See also

- [Docker](docker.md) · [Kubernetes](kubernetes.md)

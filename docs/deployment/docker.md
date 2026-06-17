# Docker Deployment

Containerize a Buddy app so it runs the same everywhere. The repo ships a
`Dockerfile` and a `docker-compose.yml` you can use as a starting point.

## A Dockerfile for your app

The pattern is: install `buddy-ai`, copy your agent script, expose the API
port, and run the script. Your script must build a `FastAPIApp` and call
`serve()` (see [FastAPI Apps](fastapi.md)).

```dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --upgrade pip && pip install "buddy-ai"

# Copy your agent app (must serve on 0.0.0.0:7777)
COPY my_agent.py .

EXPOSE 7777

CMD ["python", "my_agent.py"]
```

A minimal `my_agent.py`:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.app.fastapi import FastAPIApp

agent = Agent(agent_id="api_agent", model=OpenAIChat(id="gpt-4o-mini"))
fastapi_app = FastAPIApp(agents=[agent])
app = fastapi_app.get_app()

if __name__ == "__main__":
    fastapi_app.serve(app, host="0.0.0.0", port=7777)
```

!!! warning "Bind to 0.0.0.0"
    Inside a container, serve on `host="0.0.0.0"` — the default `localhost`
    is not reachable from outside the container.

## API keys via environment

Never bake secrets into the image. Pass them at runtime:

```bash
docker build -t my-buddy-app .

docker run --rm -p 7777:7777 \
  -e OPENAI_API_KEY=sk-... \
  my-buddy-app
```

Or keep them in an env file and mount it:

```bash
docker run --rm -p 7777:7777 --env-file .env my-buddy-app
```

See [`.env.example`](https://github.com/esasrir91/buddy-ai/blob/main/.env.example)
for the full list of supported variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`GOOGLE_API_KEY`, `DATABASE_URL`, `REDIS_URL`, …).

## Verifying the container

The FastAPI app exposes `GET /status` (see [endpoints](fastapi.md#endpoints)):

```bash
curl http://localhost:7777/status
# {"status":"available"}
```

## docker-compose

The bundled `docker-compose.yml` brings up the agent API alongside common
backing services:

```bash
cp .env.example .env   # set OPENAI_API_KEY (and any others you use)
docker compose up -d
docker compose ps
docker compose logs -f buddy
```

| Service | Port | Image |
|---------|------|-------|
| `buddy` | 7777 | built from `Dockerfile` |
| `playground` | 8501 | built from `Dockerfile` |
| `postgres` | 5432 | `postgres:15-alpine` |
| `redis` | 6379 | `redis:7-alpine` |
| `qdrant` | 6333 | `qdrant/qdrant:latest` |

Variables from `.env` are passed to the containers via `env_file: .env`.

```bash
docker compose down       # stop
docker compose down -v    # stop and remove volumes
```

!!! note "Match the healthcheck to your routes"
    The Compose file's `buddy` healthcheck targets `/health`. The FastAPI app
    serves `/status`, not `/health` — point your healthcheck (and any load
    balancer probe) at `/status` unless you add a `/health` route yourself.

## See also

- [Kubernetes](kubernetes.md)
- [Cloud Platforms](cloud.md)

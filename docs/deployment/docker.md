# Docker Deployment

## Prerequisites

- Docker 24+
- Docker Compose v2

## Quick Start

```bash
# Clone the repo
git clone https://github.com/esasrir91/buddy-ai.git
cd buddy-ai

# Copy and configure environment
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY

# Start all services
docker-compose up -d
```

Services started:
- **buddy** — FastAPI agent server on `localhost:7777`
- **playground** — Playground server on `localhost:8501`
- **postgres** — PostgreSQL on `localhost:5432`
- **redis** — Redis on `localhost:6379`
- **qdrant** — Qdrant vector DB on `localhost:6333`

## Check Status

```bash
docker-compose ps
curl http://localhost:7777/health
```

## Logs

```bash
docker-compose logs -f buddy
```

## Stop

```bash
docker-compose down
# Remove volumes too:
docker-compose down -v
```

## Custom Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
RUN pip install "buddy-ai[irag]"
COPY buddy/ ./buddy/
COPY my_agent.py .
CMD ["python", "my_agent.py"]
```

## Environment Variables in Docker

All variables in `.env` are automatically passed to the container via `env_file: .env` in `docker-compose.yml`.

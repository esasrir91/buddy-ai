# Standalone container for the Varam License & Entitlement API.
# Build from the repo root:  docker build -f buddy/licensing/Dockerfile -t varam-license .
# Run:  docker run -p 8800:8800 -e BUDDY_LICENSE_PRIVKEY="$(cat private.pem)" varam-license
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PORT=8800

COPY buddy/licensing/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Only the package code is needed (buddy/__init__ is lazy and lightweight).
COPY buddy /app/buddy

# Persist keys + sqlite db on a mounted volume in production.
ENV BUDDY_LICENSE_KEYDIR=/data BUDDY_LICENSE_DB=/data/licenses.db
VOLUME ["/data"]

EXPOSE 8800
CMD ["sh", "-c", "uvicorn buddy.licensing.server.app:create_app --factory --host 0.0.0.0 --port ${PORT}"]

# Kubernetes

Deploy the Buddy container (see [Docker](docker.md)) to Kubernetes with a
standard Deployment + Service. Buddy ships no Kubernetes-specific tooling — the
manifests below are generic and work with any container image you build.

## Secret for API keys

Keep provider keys out of the image and pod spec:

```bash
kubectl create secret generic buddy-secrets \
  --from-literal=OPENAI_API_KEY=sk-...
```

## Deployment + Service

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: buddy
  labels:
    app: buddy
spec:
  replicas: 2
  selector:
    matchLabels:
      app: buddy
  template:
    metadata:
      labels:
        app: buddy
    spec:
      containers:
        - name: buddy
          image: my-registry/my-buddy-app:latest
          ports:
            - containerPort: 7777
          envFrom:
            - secretRef:
                name: buddy-secrets
          readinessProbe:
            httpGet:
              path: /status
              port: 7777
            initialDelaySeconds: 10
            periodSeconds: 15
          livenessProbe:
            httpGet:
              path: /status
              port: 7777
            initialDelaySeconds: 20
            periodSeconds: 30
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1"
              memory: "1Gi"
---
apiVersion: v1
kind: Service
metadata:
  name: buddy
spec:
  selector:
    app: buddy
  ports:
    - port: 80
      targetPort: 7777
  type: ClusterIP
```

Apply it:

```bash
kubectl apply -f buddy.yaml
kubectl get pods -l app=buddy
```

!!! note "Probe the real route"
    The FastAPI app serves `GET /status`, so the readiness/liveness probes above
    target `/status`. Make sure your app binds to `0.0.0.0:7777` inside the
    container.

## Scaling

Because the API is stateless per request, scale horizontally by raising
`replicas` or with a `HorizontalPodAutoscaler`:

```bash
kubectl scale deployment/buddy --replicas=4
```

!!! warning "Externalize state"
    Conversation memory, sessions, and knowledge should live in shared backends
    (Postgres, Redis, a vector DB) — not on the pod's local disk — so replicas
    behave consistently and survive restarts.

## Exposing the service

Use an `Ingress` or change the `Service` `type` to `LoadBalancer` to reach the
API from outside the cluster, then send requests to `POST /runs` as described in
[FastAPI Apps](fastapi.md).

## See also

- [Docker](docker.md) · [Cloud Platforms](cloud.md)

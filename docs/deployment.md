# Production Setup & Docker Deployment

This guide outlines the deployment options for **AgenticPMO** to production and staging environments, utilizing containerization and professional WSGI/ASGI server configurations.

---

## 🐋 Docker Containerization

To run the AgenticPMO FastAPI service inside a isolated container, create a `Dockerfile` and a `docker-compose.yml` file in the root directory.

### 1. `Dockerfile`
A multi-stage, secure `Dockerfile` that runs the app under a non-root user:

```dockerfile
# Use a lightweight official Python image
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final runner stage
FROM python:3.11-slim as runner

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /root/.local /root/.local
COPY . .

# Set environment paths
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# Expose API port
EXPOSE 8000

# Run FastAPI app using Uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. `docker-compose.yml`
For orchestrating the API container alongside reverse proxies or local environment dependencies:

```yaml
version: '3.8'

services:
  agenticpmo:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - PYTHONPATH=/app
    restart: unless-stopped
```

---

## ⚙️ Environment Variables Reference

Configure these environment variables in your server or `.env` file:

| Variable | Type | Description | Mandatory |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | String | Google Gemini API credentials. | Optional (triggers offline mock fallback if missing) |
| `OPENAI_API_KEY` | String | OpenAI API credentials. | Optional (checked if Gemini key is unset) |
| `PORT` | Integer | Network port for the FastAPI server (default: `8000`). | No |
| `HOST` | String | Bind address for server (default: `127.0.0.1` locally, `0.0.0.0` in Docker). | No |

---

## 🛡️ Production Security & Performance Best Practices

1. **Production Server Wrapper**:
   In high-traffic environments, run Uvicorn workers behind a **Gunicorn** manager:
   ```bash
   gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
   ```
2. **Reverse Proxy SSL Termination**:
   Always run Gunicorn/Uvicorn behind a reverse proxy (such as Nginx, Caddy, or an AWS Application Load Balancer) to terminate SSL/TLS connections securely.
3. **API Rate Limiting**:
   Since LLM token usage can generate significant costs, restrict the FastAPI `/chat` endpoint with rate-limiting middleware (e.g. `slowapi`) or web application firewalls (WAF).

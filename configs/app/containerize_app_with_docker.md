# Containerize App with Docker Specification
# Build Docker images and docker-compose setup

## Dockerfile

```dockerfile
# Dockerfile (FastAPI backend)

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY src/ src/
COPY configs/ configs/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run app
CMD ["uvicorn", "src.qlib_research.app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# Dockerfile.frontend (React frontend)

FROM node:18 AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      PYTHONUNBUFFERED: "1"
      LOG_LEVEL: "INFO"
      DATA_PATH: "/data"
      QLIB_DATA_PATH: "/data/qlib"
    volumes:
      - ./src:/app/src
      - ./configs:/app/configs
      - qlib_data:/data/qlib
      - mlruns:/app/mlruns
    depends_on:
      - redis
    networks:
      - qlib_network

  frontend:
    build:
      context: ./src/app/frontend
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - qlib_network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - qlib_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  qlib_data:
  mlruns:
  redis_data:

networks:
  qlib_network:
    driver: bridge
```

## Build and Run

```bash
# Build images
docker-compose build

# Start services
docker-compose up

# View logs
docker-compose logs -f backend

# Stop
docker-compose down

# Cleanup
docker-compose down -v
```

## Acceptance Criteria

- [ ] Backend Dockerfile builds
- [ ] Frontend Dockerfile builds
- [ ] docker-compose up successful
- [ ] All services healthy
- [ ] Backend reachable at :8000
- [ ] Frontend reachable at :3000
- [ ] Logs show no errors

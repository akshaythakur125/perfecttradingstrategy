# Deployment Guide

## Production Checklist

- [ ] Strong JWT_SECRET (32+ bytes, randomly generated)
- [ ] Exchange API keys configured (testnet initially)
- [ ] PostgreSQL connection string configured
- [ ] Redis connection string configured
- [ ] DEBUG=false
- [ ] CORS origins restricted to frontend domain
- [ ] Rate limiting enabled
- [ ] HTTPS configured
- [ ] Database backed up
- [ ] Monitoring set up

## Docker Deployment

### Production Docker Compose

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: perfecttrading
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DEBUG=false
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
```

### Environment Variables (.env)

```bash
# Production settings
DEBUG=false
JWT_SECRET=<generate-with-python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=postgresql+asyncpg://user:${DB_PASSWORD}@postgres:5432/perfecttrading
```

## Cloud Deployment

### AWS ECS

1. Push Docker image to ECR:
```bash
aws ecr create-repository --repository-name perfecttrading-backend
docker tag perfecttrading-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/perfecttrading-backend:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/perfecttrading-backend:latest
```

2. Create ECS task definition with the image and environment variables

3. Set up RDS PostgreSQL and ElastiCache Redis

4. Configure Application Load Balancer with HTTPS (ACM certificate)

### Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: perfecttrading-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: perfecttrading-backend
  template:
    metadata:
      labels:
        app: perfecttrading-backend
    spec:
      containers:
      - name: backend
        image: perfecttrading-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: database_url
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: jwt-secret
              key: jwt_secret
---
apiVersion: v1
kind: Service
metadata:
  name: perfecttrading-backend
spec:
  selector:
    app: perfecttrading-backend
  ports:
  - port: 8000
    targetPort: 8000
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: perfecttrading-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.perfecttrading.com
    secretName: perfecttrading-tls
  rules:
  - host: api.perfecttrading.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: perfecttrading-backend
            port:
              number: 8000
```

## Monitoring

### Health Check Endpoint

```bash
curl https://api.perfecttrading.com/health
# {"status":"ok","service":"PerfectTradingStrategy","version":"2.0.0"}
```

### Logging

Logs are output to stdout in JSON format. Use a log aggregator (CloudWatch, Datadog, ELK):

```bash
docker-compose logs -f backend
```

### Metrics to Monitor

- Request latency (p50, p95, p99)
- Error rate (5xx responses)
- Active WebSocket connections
- Database connection pool usage
- Signal generation rate
- Backtest queue depth

## Security

1. **HTTPS**: Use Let's Encrypt with cert-manager (K8s) or ACM (AWS)
2. **API Keys**: Store in secrets manager, never in code
3. **Rate Limiting**: 100 requests/minute per IP (enabled by default)
4. **Input Validation**: All endpoints validate input via Pydantic
5. **JWT**: Short-lived tokens (60 min), HS256 signing
6. **Database**: Use strong passwords, restrict network access
7. **CORS**: Restrict to specific frontend domains

## Backup Strategy

```bash
# Database backup
pg_dump -U postgres perfecttrading > backup_$(date +%Y%m%d).sql

# Automated backup with cron
0 2 * * * pg_dump -U postgres perfecttrading | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

## Scaling

- **Horizontal**: Add more backend instances behind a load balancer
- **Database**: Use RDS read replicas for query-heavy workloads
- **Scanner**: Increase scan interval or distribute across worker processes
- **Caching**: Use Redis for exchange data caching to reduce API calls

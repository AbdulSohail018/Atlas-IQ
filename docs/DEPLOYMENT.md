# Glonav Deployment Guide

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Git
- 8GB+ RAM recommended
- 20GB+ free disk space

### 1. Clone Repository
```bash
git clone <repository-url>
cd glonav
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 3. Start Services
```bash
# Start all services
make up

# Or manually with docker-compose
docker-compose up -d
```

### 4. Initialize Data
```bash
# Install Ollama models
make install-ollama

# Seed sample data
make seed
```

### 5. Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474 (neo4j/password)
- **Prefect UI**: http://localhost:4200

## Production Deployment

### Option 1: Kubernetes (Recommended)

#### Prerequisites
- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3.0+
- Container registry access

#### 1. Prepare Cluster
```bash
# Create namespaces
kubectl apply -f k8s/namespace.yaml

# Create secrets
kubectl create secret generic glonav-secrets \
  --from-literal=SECRET_KEY="your-secret-key" \
  --from-literal=JWT_SECRET_KEY="your-jwt-secret" \
  --from-literal=POSTGRES_PASSWORD="your-postgres-password" \
  --from-literal=NEO4J_AUTH="neo4j/your-neo4j-password" \
  --namespace=glonav

# Optional: Add external API keys
kubectl create secret generic api-keys \
  --from-literal=OPENAI_API_KEY="your-openai-key" \
  --from-literal=EPA_API_KEY="your-epa-key" \
  --from-literal=CENSUS_API_KEY="your-census-key" \
  --namespace=glonav
```

#### 2. Deploy Infrastructure
```bash
# Apply configuration
kubectl apply -f k8s/configmap.yaml

# Create persistent volumes
kubectl apply -f k8s/pvc.yaml

# Deploy databases and services
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

#### 3. Configure Ingress
```bash
# Install NGINX Ingress Controller (if not present)
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx --create-namespace

# Install cert-manager for SSL
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Apply ingress configuration
kubectl apply -f k8s/ingress.yaml
```

#### 4. Verify Deployment
```bash
# Check pod status
kubectl get pods -n glonav

# Check services
kubectl get services -n glonav

# View logs
kubectl logs -f deployment/glonav-backend -n glonav
```

### Option 2: Docker Swarm

#### 1. Initialize Swarm
```bash
docker swarm init
```

#### 2. Deploy Stack
```bash
# Deploy production stack
docker stack deploy -c docker-compose.prod.yml glonav
```

#### 3. Scale Services
```bash
# Scale backend instances
docker service scale glonav_backend=3

# Scale frontend instances
docker service scale glonav_frontend=2
```

### Option 3: Cloud Platforms

#### AWS ECS
```bash
# Install ECS CLI
curl -Lo ecs-cli https://amazon-ecs-cli.s3.amazonaws.com/ecs-cli-linux-amd64-latest
chmod +x ecs-cli && sudo mv ecs-cli /usr/local/bin/

# Configure ECS
ecs-cli configure --cluster glonav --default-launch-type EC2 --region us-east-1

# Deploy
ecs-cli compose --file docker-compose.aws.yml up
```

#### Google Cloud Run
```bash
# Build and push images
gcloud builds submit --tag gcr.io/PROJECT_ID/glonav-backend backend/
gcloud builds submit --tag gcr.io/PROJECT_ID/glonav-frontend frontend/

# Deploy services
gcloud run deploy glonav-backend \
  --image gcr.io/PROJECT_ID/glonav-backend \
  --platform managed \
  --region us-central1

gcloud run deploy glonav-frontend \
  --image gcr.io/PROJECT_ID/glonav-frontend \
  --platform managed \
  --region us-central1
```

#### Azure Container Instances
```bash
# Create resource group
az group create --name glonav-rg --location eastus

# Deploy container group
az container create \
  --resource-group glonav-rg \
  --file azure-container-group.yaml
```

## Environment Configuration

### Required Environment Variables

#### Core Application
```bash
# Application
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
ENVIRONMENT=production
DEBUG=false

# Database URLs
DATABASE_URL=postgresql://user:pass@host:5432/glonav
VECTOR_DB_URL=postgresql://user:pass@host:5432/glonav_vectors
NEO4J_URI=bolt://host:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
REDIS_URL=redis://host:6379

# LLM Configuration
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

#### External APIs
```bash
# Data Source APIs
EPA_API_KEY=your-epa-key
CENSUS_API_KEY=your-census-key
WHO_API_KEY=your-who-key
NOAA_API_KEY=your-noaa-key
```

#### Infrastructure
```bash
# Monitoring
SENTRY_DSN=https://...
PROMETHEUS_PORT=9090

# CORS
CORS_ORIGINS=["https://yourdomain.com"]
```

### Production Optimizations

#### Performance Settings
```bash
# Worker processes
MAX_WORKERS=4
WORKER_CONNECTIONS=1000

# Database connections
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Caching
CACHE_TTL=3600
REDIS_POOL_SIZE=10

# Request limits
REQUEST_TIMEOUT=30
MAX_REQUEST_SIZE=50MB
```

#### Security Settings
```bash
# Security headers
SECURE_SSL_REDIRECT=true
SECURE_HSTS_SECONDS=31536000
SECURE_CONTENT_TYPE_NOSNIFF=true
SECURE_BROWSER_XSS_FILTER=true

# Rate limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_BURST=20
```

## Monitoring and Logging

### Health Checks
```bash
# Application health
curl https://yourapp.com/api/v1/health

# Individual service health
curl https://yourapp.com/api/v1/health/postgres
curl https://yourapp.com/api/v1/health/neo4j
curl https://yourapp.com/api/v1/health/redis
```

### Metrics Collection

#### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'glonav-backend'
    static_configs:
      - targets: ['glonav-backend:9090']
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
  
  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:2004']
```

#### Grafana Dashboards
```bash
# Import pre-built dashboards
curl -X POST \
  http://grafana:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @grafana/glonav-dashboard.json
```

### Log Aggregation

#### ELK Stack Setup
```yaml
# docker-compose.logging.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    
  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
```

## Backup and Recovery

### Database Backups

#### PostgreSQL
```bash
# Create backup
pg_dump -h localhost -U postgres glonav > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h $DB_HOST -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/glonav_$DATE.sql.gz

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

#### Neo4j
```bash
# Stop Neo4j
neo4j stop

# Create backup
neo4j-admin database dump neo4j --to-path=/backups/neo4j/

# Start Neo4j
neo4j start
```

#### DuckDB
```bash
# Export to parquet
duckdb glonav.duckdb "EXPORT DATABASE '/backups/duckdb/' (FORMAT PARQUET)"
```

### Restore Procedures

#### PostgreSQL Restore
```bash
# Create new database
createdb -h localhost -U postgres glonav_restored

# Restore from backup
gunzip -c backup_20240115_143000.sql.gz | psql -h localhost -U postgres glonav_restored
```

#### Neo4j Restore
```bash
# Stop Neo4j
neo4j stop

# Restore from backup
neo4j-admin database load neo4j --from-path=/backups/neo4j/

# Start Neo4j
neo4j start
```

## Scaling Guidelines

### Horizontal Scaling

#### Backend Services
```bash
# Scale Kubernetes deployment
kubectl scale deployment glonav-backend --replicas=5 -n glonav

# Auto-scaling based on CPU
kubectl autoscale deployment glonav-backend \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n glonav
```

#### Database Scaling
```bash
# PostgreSQL read replicas
kubectl apply -f k8s/postgres-replica.yaml

# Redis clustering
kubectl apply -f k8s/redis-cluster.yaml
```

### Vertical Scaling
```yaml
# Increase resource limits
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
kubectl logs deployment/glonav-backend -n glonav

# Check configuration
kubectl describe configmap glonav-config -n glonav

# Check secrets
kubectl get secrets -n glonav
```

#### Database Connection Issues
```bash
# Test database connectivity
kubectl exec -it deployment/glonav-backend -n glonav -- \
  python -c "import psycopg2; conn = psycopg2.connect('$DATABASE_URL'); print('Connected!')"

# Check database status
kubectl exec -it statefulset/postgres -n glonav -- \
  psql -U postgres -c "SELECT version();"
```

#### Performance Issues
```bash
# Check resource usage
kubectl top pods -n glonav

# Check database performance
kubectl exec -it statefulset/postgres -n glonav -- \
  psql -U postgres -c "SELECT * FROM pg_stat_activity;"

# Check slow queries
kubectl logs deployment/glonav-backend -n glonav | grep "slow query"
```

### Debug Mode

#### Enable Debug Logging
```bash
kubectl patch configmap glonav-config -n glonav --patch '{"data":{"LOG_LEVEL":"DEBUG"}}'
kubectl rollout restart deployment/glonav-backend -n glonav
```

#### Access Debug Shell
```bash
# Backend container
kubectl exec -it deployment/glonav-backend -n glonav -- /bin/bash

# Database shell
kubectl exec -it statefulset/postgres -n glonav -- psql -U postgres glonav
```

## Security Checklist

### Pre-deployment Security
- [ ] Change all default passwords
- [ ] Generate strong secret keys
- [ ] Configure SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Enable audit logging
- [ ] Configure backup encryption
- [ ] Set up monitoring alerts
- [ ] Review CORS settings
- [ ] Enable rate limiting
- [ ] Configure security headers

### Post-deployment Security
- [ ] Verify SSL configuration
- [ ] Test authentication flows
- [ ] Validate API security
- [ ] Check log aggregation
- [ ] Verify backup procedures
- [ ] Test disaster recovery
- [ ] Review access controls
- [ ] Monitor security alerts
- [ ] Update dependencies
- [ ] Conduct security audit

## Maintenance

### Regular Maintenance Tasks

#### Daily
- Check system health
- Monitor error logs
- Verify backup completion
- Review performance metrics

#### Weekly
- Update security patches
- Rotate access keys
- Clean up old logs
- Review capacity planning

#### Monthly
- Full system backup test
- Security vulnerability scan
- Performance optimization review
- Disaster recovery test

#### Quarterly
- Dependency updates
- Architecture review
- Security audit
- Capacity planning review

This deployment guide provides comprehensive instructions for setting up Glonav in various environments while ensuring security, scalability, and maintainability.
# Deployment Guide

This comprehensive guide covers deploying DagLab in various environments, from local development to large-scale production deployments.

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Local Development](./local-development.md)
3. [Docker Deployment](./docker-deployment.md)
4. [Kubernetes Deployment](./kubernetes-deployment.md)
5. [Cloud Deployments](./cloud-deployments.md)
6. [High Availability Setup](./high-availability.md)
7. [Security Configuration](./security.md)
8. [Monitoring and Logging](./monitoring.md)
9. [Performance Tuning](./performance-tuning.md)
10. [Backup and Recovery](./backup-recovery.md)

## Deployment Overview

DagLab supports multiple deployment patterns to meet different operational requirements:

### Deployment Patterns

#### 1. Single Node Deployment
- **Use Case**: Development, testing, small workloads
- **Components**: All services on one machine
- **Pros**: Simple setup, low resource requirements
- **Cons**: Limited scalability, single point of failure

#### 2. Multi-Node Deployment
- **Use Case**: Production workloads, team environments
- **Components**: Distributed across multiple machines
- **Pros**: Better performance, some fault tolerance
- **Cons**: More complex setup and management

#### 3. Container Orchestration
- **Use Case**: Cloud-native deployments, auto-scaling
- **Components**: Containerized services with orchestration
- **Pros**: High scalability, automated management
- **Cons**: Requires container orchestration expertise

#### 4. Hybrid Cloud
- **Use Case**: Multi-cloud, on-premises + cloud
- **Components**: Services across multiple environments
- **Pros**: Flexibility, vendor independence
- **Cons**: Complex networking and security

## Quick Start Deployment

### Option 1: Docker Compose (Recommended for Quick Start)

```bash
# Clone repository
git clone https://github.com/openconjecture/daglab.git
cd daglab

# Start with Docker Compose
docker-compose up -d

# Verify deployment
curl http://localhost:8080/api/v1/health
```

### Option 2: Helm Chart (Kubernetes)

```bash
# Add Helm repository
helm repo add daglab https://charts.daglab.io
helm repo update

# Install DagLab
helm install daglab daglab/daglab \
  --namespace daglab \
  --create-namespace \
  --set ingress.enabled=true \
  --set persistence.enabled=true

# Check status
kubectl get pods -n daglab
```

### Option 3: Cloud Marketplace

- **AWS**: Available on AWS Marketplace
- **GCP**: Deploy via Google Cloud Marketplace
- **Azure**: Available on Azure Marketplace

## Architecture Components

### Core Services

```yaml
# Basic DagLab architecture
daglab-web:
  description: "Web UI and API server"
  ports: [8080]
  dependencies: [daglab-database, daglab-redis]
  
daglab-scheduler:
  description: "DAG scheduler service"
  dependencies: [daglab-database, daglab-redis]
  
daglab-executor:
  description: "Task execution service"
  dependencies: [daglab-database, daglab-redis]
  
daglab-worker:
  description: "Worker processes"
  replicas: 3
  dependencies: [daglab-database, daglab-redis]
```

### Supporting Services

```yaml
daglab-database:
  description: "PostgreSQL database"
  type: "postgresql"
  version: "13"
  persistence: true
  
daglab-redis:
  description: "Redis for caching and queuing"
  type: "redis"
  version: "6"
  
daglab-storage:
  description: "File storage service"
  type: "minio"  # or S3, GCS, Azure Blob
```

## Environment-Specific Configurations

### Development Environment

```yaml
# config/development.yaml
daglab:
  core:
    environment: "development"
    debug: true
    
  database:
    url: "sqlite:///dev_daglab.db"
    
  executor:
    type: "local"
    max_parallel_tasks: 2
    
  logging:
    level: "DEBUG"
    console:
      enabled: true
      
  security:
    enable_auth: false
```

### Staging Environment

```yaml
# config/staging.yaml
daglab:
  core:
    environment: "staging"
    debug: false
    
  database:
    url: "postgresql://user:pass@staging-db:5432/daglab"
    pool_size: 10
    
  executor:
    type: "celery"
    max_parallel_tasks: 8
    
  logging:
    level: "INFO"
    file:
      enabled: true
      path: "/var/log/daglab/daglab.log"
      
  security:
    enable_auth: true
    secret_key: "${STAGING_SECRET_KEY}"
```

### Production Environment

```yaml
# config/production.yaml
daglab:
  core:
    environment: "production"
    debug: false
    
  database:
    url: "postgresql://user:pass@prod-db:5432/daglab"
    pool_size: 50
    max_overflow: 30
    ssl_mode: "require"
    
  executor:
    type: "kubernetes"
    namespace: "daglab-production"
    max_parallel_tasks: 100
    
  logging:
    level: "WARNING"
    structured: true
    
  security:
    enable_auth: true
    secret_key: "${PRODUCTION_SECRET_KEY}"
    session_timeout: 1800
    
  monitoring:
    enabled: true
    metrics:
      enabled: true
      endpoint: "/metrics"
```

## Container Deployment

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  daglab-web:
    image: daglab/daglab:latest
    command: ["daglab", "web", "serve"]
    ports:
      - "8080:8080"
    environment:
      - DAGLAB_CONFIG_PATH=/app/config/production.yaml
      - DAGLAB_DATABASE_URL=postgresql://daglab:password@postgres:5432/daglab
      - DAGLAB_REDIS_URL=redis://redis:6379/0
    volumes:
      - ./config:/app/config
      - ./dags:/app/dags
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    
  daglab-scheduler:
    image: daglab/daglab:latest
    command: ["daglab", "scheduler", "start"]
    environment:
      - DAGLAB_CONFIG_PATH=/app/config/production.yaml
      - DAGLAB_DATABASE_URL=postgresql://daglab:password@postgres:5432/daglab
      - DAGLAB_REDIS_URL=redis://redis:6379/0
    volumes:
      - ./config:/app/config
      - ./dags:/app/dags
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    
  daglab-worker:
    image: daglab/daglab:latest
    command: ["daglab", "worker", "start"]
    environment:
      - DAGLAB_CONFIG_PATH=/app/config/production.yaml
      - DAGLAB_DATABASE_URL=postgresql://daglab:password@postgres:5432/daglab
      - DAGLAB_REDIS_URL=redis://redis:6379/0
    volumes:
      - ./config:/app/config
      - ./dags:/app/dags
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    deploy:
      replicas: 3
      
  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=daglab
      - POSTGRES_USER=daglab
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    
  redis:
    image: redis:6-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  minio_data:

networks:
  default:
    driver: bridge
```

### Kubernetes Deployment

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: daglab
  
---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: daglab-config
  namespace: daglab
data:
  production.yaml: |
    daglab:
      core:
        environment: "production"
      database:
        url: "postgresql://daglab:password@postgres:5432/daglab"
      executor:
        type: "kubernetes"
        namespace: "daglab"
        
---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: daglab-web
  namespace: daglab
  labels:
    app: daglab-web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: daglab-web
  template:
    metadata:
      labels:
        app: daglab-web
    spec:
      containers:
      - name: daglab-web
        image: daglab/daglab:latest
        command: ["daglab", "web", "serve"]
        ports:
        - containerPort: 8080
        env:
        - name: DAGLAB_CONFIG_PATH
          value: "/app/config/production.yaml"
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: dags
          mountPath: /app/dags
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: daglab-config
      - name: dags
        persistentVolumeClaim:
          claimName: daglab-dags-pvc
          
---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: daglab-web-service
  namespace: daglab
spec:
  selector:
    app: daglab-web
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
  
---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: daglab-ingress
  namespace: daglab
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - daglab.example.com
    secretName: daglab-tls
  rules:
  - host: daglab.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: daglab-web-service
            port:
              number: 80
```

## Cloud Platform Deployments

### AWS Deployment

#### ECS with Fargate

```yaml
# aws/ecs-task-definition.json
{
  "family": "daglab-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789012:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "daglab-web",
      "image": "daglab/daglab:latest",
      "command": ["daglab", "web", "serve"],
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DAGLAB_DATABASE_URL",
          "value": "postgresql://daglab:password@daglab-rds.cluster-xyz.us-west-2.rds.amazonaws.com:5432/daglab"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/daglab",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Terraform Configuration

```hcl
# aws/main.tf
provider "aws" {
  region = var.aws_region
}

# VPC and Networking
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "daglab-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = true
}

# RDS Database
resource "aws_db_instance" "daglab_db" {
  identifier     = "daglab-database"
  engine         = "postgres"
  engine_version = "13.7"
  instance_class = "db.t3.medium"
  
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_encrypted     = true
  
  db_name  = "daglab"
  username = "daglab"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.daglab.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "daglab-final-snapshot"
}

# ECS Cluster
resource "aws_ecs_cluster" "daglab" {
  name = "daglab-cluster"
  
  capacity_providers = ["FARGATE"]
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Application Load Balancer
resource "aws_lb" "daglab" {
  name               = "daglab-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = module.vpc.public_subnets
  
  enable_deletion_protection = true
}
```

### Google Cloud Platform Deployment

#### GKE with Helm

```bash
# Create GKE cluster
gcloud container clusters create daglab-cluster \
  --zone=us-central1-a \
  --num-nodes=3 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10 \
  --enable-autorepair \
  --enable-autoupgrade

# Get cluster credentials
gcloud container clusters get-credentials daglab-cluster --zone=us-central1-a

# Install DagLab with Helm
helm install daglab daglab/daglab \
  --namespace daglab \
  --create-namespace \
  --set cloudProvider=gcp \
  --set database.cloudSql.enabled=true \
  --set storage.gcs.enabled=true
```

### Azure Deployment

#### Azure Container Instances

```yaml
# azure/container-group.yaml
apiVersion: 2019-12-01
location: eastus
name: daglab-container-group
properties:
  containers:
  - name: daglab-web
    properties:
      image: daglab/daglab:latest
      command: ["daglab", "web", "serve"]
      ports:
      - port: 8080
      resources:
        requests:
          cpu: 1
          memoryInGb: 2
      environmentVariables:
      - name: DAGLAB_DATABASE_URL
        value: "postgresql://daglab@daglab-server:password@daglab-server.postgres.database.azure.com:5432/daglab"
  osType: Linux
  restartPolicy: Always
  ipAddress:
    type: Public
    ports:
    - protocol: tcp
      port: 8080
tags:
  environment: production
  application: daglab
```

## High Availability Configuration

### Database High Availability

#### PostgreSQL with Streaming Replication

```yaml
# postgresql-primary.yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: daglab-postgres
  namespace: daglab
spec:
  instances: 3
  
  postgresql:
    parameters:
      max_connections: "200"
      shared_buffers: "256MB"
      effective_cache_size: "1GB"
      
  bootstrap:
    initdb:
      database: daglab
      owner: daglab
      secret:
        name: daglab-db-credentials
        
  storage:
    size: 100Gi
    storageClass: fast-ssd
    
  monitoring:
    enabled: true
    
  backup:
    retentionPolicy: "30d"
    barmanObjectStore:
      destinationPath: "s3://daglab-backups/postgres"
      s3Credentials:
        accessKeyId:
          name: backup-credentials
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: backup-credentials
          key: SECRET_ACCESS_KEY
```

### Redis High Availability

```yaml
# redis-sentinel.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-sentinel-config
data:
  sentinel.conf: |
    sentinel monitor daglab-redis redis-master 6379 2
    sentinel down-after-milliseconds daglab-redis 5000
    sentinel failover-timeout daglab-redis 10000
    sentinel parallel-syncs daglab-redis 1
    
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-sentinel
spec:
  replicas: 3
  selector:
    matchLabels:
      app: redis-sentinel
  template:
    metadata:
      labels:
        app: redis-sentinel
    spec:
      containers:
      - name: redis-sentinel
        image: redis:6-alpine
        command:
        - redis-sentinel
        - /etc/redis/sentinel.conf
        volumeMounts:
        - name: config
          mountPath: /etc/redis
        ports:
        - containerPort: 26379
      volumes:
      - name: config
        configMap:
          name: redis-sentinel-config
```

## Security Hardening

### SSL/TLS Configuration

```yaml
# nginx-ssl.conf
server {
    listen 443 ssl http2;
    server_name daglab.example.com;
    
    ssl_certificate /etc/ssl/certs/daglab.crt;
    ssl_certificate_key /etc/ssl/private/daglab.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    location / {
        proxy_pass http://daglab-web:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Network Security

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: daglab-network-policy
  namespace: daglab
spec:
  podSelector:
    matchLabels:
      app: daglab-web
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

## Monitoring and Observability

### Prometheus Configuration

```yaml
# monitoring/prometheus.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
      
    rule_files:
      - "daglab_rules.yml"
      
    scrape_configs:
    - job_name: 'daglab'
      static_configs:
      - targets: ['daglab-web:8080']
      metrics_path: '/metrics'
      
    - job_name: 'postgres'
      static_configs:
      - targets: ['postgres-exporter:9187']
      
    - job_name: 'redis'
      static_configs:
      - targets: ['redis-exporter:9121']
      
    alerting:
      alertmanagers:
      - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "DagLab Operations",
    "panels": [
      {
        "title": "DAG Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(daglab_dag_success_total[5m]) / rate(daglab_dag_runs_total[5m])"
          }
        ]
      },
      {
        "title": "Task Execution Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(daglab_task_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Active Workers",
        "type": "stat",
        "targets": [
          {
            "expr": "daglab_workers_active"
          }
        ]
      }
    ]
  }
}
```

## Performance Optimization

### Resource Optimization

```yaml
# k8s/horizontal-pod-autoscaler.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: daglab-web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: daglab-web
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Database Optimization

```sql
-- PostgreSQL performance tuning
-- Connection pooling
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Indexes for DagLab tables
CREATE INDEX CONCURRENTLY idx_dag_runs_dag_id_state ON dag_runs(dag_id, state);
CREATE INDEX CONCURRENTLY idx_task_instances_dag_id_task_id ON task_instances(dag_id, task_id);
CREATE INDEX CONCURRENTLY idx_task_instances_state_start_date ON task_instances(state, start_date);

-- Regular maintenance
-- Run VACUUM and ANALYZE regularly
SELECT cron.schedule('vacuum-daglab', '0 2 * * *', 'VACUUM ANALYZE;');
```

## Backup and Disaster Recovery

### Automated Backup Strategy

```yaml
# backup/cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daglab-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:13
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: daglab-db-secret
                  key: password
            command:
            - /bin/bash
            - -c
            - |
              DATE=$(date +%Y%m%d_%H%M%S)
              pg_dump -h postgres -U daglab -d daglab > /backup/daglab_backup_$DATE.sql
              aws s3 cp /backup/daglab_backup_$DATE.sql s3://daglab-backups/database/
              # Keep only last 30 days of backups
              find /backup -name "daglab_backup_*.sql" -mtime +30 -delete
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

### Disaster Recovery Plan

```bash
#!/bin/bash
# disaster-recovery.sh

# 1. Restore database from backup
BACKUP_DATE="20240121_020000"
aws s3 cp s3://daglab-backups/database/daglab_backup_$BACKUP_DATE.sql /tmp/
psql -h new-postgres -U daglab -d daglab -f /tmp/daglab_backup_$BACKUP_DATE.sql

# 2. Restore configuration and DAGs
aws s3 sync s3://daglab-backups/config/ /app/config/
aws s3 sync s3://daglab-backups/dags/ /app/dags/

# 3. Update DNS to point to new infrastructure
# (This would typically be done through your DNS provider's API)

# 4. Start services
kubectl apply -f k8s/
kubectl rollout status deployment/daglab-web -n daglab

# 5. Verify service health
curl -f http://daglab.example.com/health || exit 1

echo "Disaster recovery completed successfully"
```

## Deployment Checklist

### Pre-Deployment

- [ ] Infrastructure provisioned and configured
- [ ] Network security groups and firewall rules configured
- [ ] SSL/TLS certificates obtained and configured
- [ ] Database instances created and configured
- [ ] Storage volumes created and mounted
- [ ] Monitoring and logging configured
- [ ] Backup systems configured and tested

### Deployment

- [ ] Configuration files validated
- [ ] Secrets and environment variables configured
- [ ] Container images built and pushed to registry
- [ ] Database migrations applied
- [ ] Services deployed in correct order
- [ ] Health checks passing
- [ ] Load balancers configured

### Post-Deployment

- [ ] Smoke tests executed successfully
- [ ] Monitoring alerts configured
- [ ] Performance baselines established
- [ ] Documentation updated
- [ ] Team trained on new deployment
- [ ] Rollback plan documented and tested

## Troubleshooting Common Issues

### Container Issues

```bash
# Check container logs
docker logs daglab-web
kubectl logs -f deployment/daglab-web -n daglab

# Debug container
docker exec -it daglab-web bash
kubectl exec -it deployment/daglab-web -n daglab -- bash

# Check resource usage
docker stats
kubectl top pods -n daglab
```

### Database Connection Issues

```bash
# Test database connectivity
psql -h postgres -U daglab -d daglab -c "SELECT 1;"

# Check connection pool
SELECT count(*) as active_connections FROM pg_stat_activity;

# Monitor slow queries
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

### Performance Issues

```bash
# Check system resources
top
htop
iostat -x 1

# Check network connectivity
netstat -an | grep 8080
ss -tuln

# Application metrics
curl http://localhost:8080/metrics
```

This deployment guide provides comprehensive coverage of DagLab deployment scenarios. For specific platform deployments, see the dedicated guides for [Docker](./docker-deployment.md), [Kubernetes](./kubernetes-deployment.md), and [Cloud Platforms](./cloud-deployments.md).
# Configuration Reference

This comprehensive guide covers all configuration options available in DagLab, from basic setup to advanced production deployments.

## Configuration Overview

DagLab uses YAML configuration files to define system behavior, execution settings, and integration parameters. The main configuration file is typically located at `config/daglab.yaml` in your project directory.

## Configuration File Structure

```yaml
# config/daglab.yaml - Main configuration file
daglab:
  # Core system settings
  core:
    version: "1.0.0"
    environment: "development"  # development, staging, production
    debug: true
    
  # Execution configuration
  executor:
    type: "local"  # local, celery, kubernetes, distributed
    max_parallel_tasks: 4
    task_timeout: 3600  # seconds
    retry_policy:
      max_retries: 3
      retry_delay: 60
      exponential_backoff: true
    
  # Database configuration
  database:
    url: "sqlite:///daglab.db"
    pool_size: 10
    max_overflow: 20
    echo: false  # Set to true for SQL logging
    
  # Storage configuration
  storage:
    type: "local"  # local, s3, gcs, azure
    path: "./data"
    compression: "gzip"
    encryption: false
    
  # Security settings
  security:
    enable_auth: false
    secret_key: "${SECRET_KEY}"
    jwt_expiration: 3600
    password_hash_algorithm: "bcrypt"
    
  # Logging configuration
  logging:
    level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_handler:
      enabled: true
      path: "./logs/daglab.log"
      max_size: "100MB"
      backup_count: 5
      
  # Monitoring and metrics
  monitoring:
    enabled: true
    metrics_backend: "prometheus"  # prometheus, statsd, datadog
    health_check_interval: 30
    
  # Scheduling configuration
  scheduler:
    type: "cron"  # cron, interval, manual
    timezone: "UTC"
    catchup: false
    max_active_runs: 1
    
  # Integration settings
  integrations:
    webhooks:
      enabled: true
      base_url: "http://localhost:8080"
    email:
      enabled: false
      smtp_server: "smtp.gmail.com"
      smtp_port: 587
    slack:
      enabled: false
      webhook_url: "${SLACK_WEBHOOK_URL}"
```

## Core Configuration

### Basic Settings

```yaml
daglab:
  core:
    version: "1.0.0"           # DagLab version compatibility
    environment: "production"  # Environment type
    debug: false               # Enable debug mode
    project_name: "my-project" # Project identifier
    description: "My DagLab project"
    
    # Global timeouts
    default_task_timeout: 1800  # 30 minutes
    dag_timeout: 7200          # 2 hours
    
    # Performance settings
    max_memory_usage: "2GB"    # Maximum memory per process
    cleanup_interval: 3600     # Cleanup interval in seconds
```

### Environment Variables

DagLab supports environment variable substitution using `${VARIABLE_NAME}` syntax:

```yaml
database:
  url: "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
  
security:
  secret_key: "${SECRET_KEY}"
  
integrations:
  aws:
    access_key: "${AWS_ACCESS_KEY_ID}"
    secret_key: "${AWS_SECRET_ACCESS_KEY}"
```

Create a `.env` file for environment variables:
```bash
# .env
DB_USER=daglab_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=daglab
SECRET_KEY=your-very-long-secret-key-here
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
```

## Executor Configuration

### Local Executor (Default)

```yaml
daglab:
  executor:
    type: "local"
    max_parallel_tasks: 4      # Number of parallel processes
    worker_timeout: 3600       # Worker timeout in seconds
    memory_limit: "1GB"        # Memory limit per worker
    
    # Process management
    process_pool_size: 4
    thread_pool_size: 8
    use_multiprocessing: true
    
    # Task execution settings
    task_retry_policy:
      max_retries: 3
      retry_delay: 60
      exponential_backoff: true
      retry_on_failure: true
```

### Celery Executor (Distributed)

```yaml
daglab:
  executor:
    type: "celery"
    
    # Celery broker configuration
    broker_url: "redis://localhost:6379/0"
    result_backend: "redis://localhost:6379/0"
    
    # Worker configuration
    worker_concurrency: 4
    worker_max_tasks_per_child: 1000
    worker_prefetch_multiplier: 1
    
    # Queue configuration
    default_queue: "default"
    queues:
      - name: "high_priority"
        routing_key: "high.*"
      - name: "low_priority" 
        routing_key: "low.*"
    
    # Task routing
    task_routes:
      "data_processing.*": {"queue": "high_priority"}
      "notifications.*": {"queue": "low_priority"}
```

### Kubernetes Executor

```yaml
daglab:
  executor:
    type: "kubernetes"
    
    # Kubernetes configuration
    namespace: "daglab"
    service_account: "daglab-worker"
    
    # Pod configuration
    worker_image: "daglab/worker:latest"
    worker_resources:
      requests:
        memory: "512Mi"
        cpu: "0.5"
      limits:
        memory: "2Gi"
        cpu: "2"
    
    # Storage configuration
    persistent_volume:
      enabled: true
      size: "10Gi"
      storage_class: "fast-ssd"
    
    # Security context
    security_context:
      run_as_user: 1000
      run_as_group: 1000
      fs_group: 1000
```

## Database Configuration

### SQLite (Development)

```yaml
daglab:
  database:
    url: "sqlite:///daglab.db"
    echo: false                # Enable SQL logging
    pool_pre_ping: true       # Verify connections
```

### PostgreSQL (Production)

```yaml
daglab:
  database:
    url: "postgresql://user:password@localhost:5432/daglab"
    pool_size: 20             # Connection pool size
    max_overflow: 30          # Additional connections
    pool_timeout: 30          # Connection timeout
    pool_recycle: 3600        # Connection recycle time
    echo: false               # SQL logging
    
    # SSL configuration
    ssl_mode: "require"
    ssl_cert: "/path/to/client-cert.pem"
    ssl_key: "/path/to/client-key.pem"
    ssl_ca: "/path/to/ca-cert.pem"
```

### MySQL/MariaDB

```yaml
daglab:
  database:
    url: "mysql+pymysql://user:password@localhost:3306/daglab"
    pool_size: 15
    max_overflow: 25
    pool_timeout: 30
    charset: "utf8mb4"
    
    # MySQL-specific settings
    sql_mode: "STRICT_TRANS_TABLES,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION"
```

## Storage Configuration

### Local Storage

```yaml
daglab:
  storage:
    type: "local"
    path: "./data"
    create_directories: true
    permissions: "0755"
    
    # File handling
    compression: "gzip"        # none, gzip, bz2, xz
    encryption: false
    max_file_size: "100MB"
    
    # Cleanup settings
    auto_cleanup: true
    retention_days: 30
```

### Amazon S3

```yaml
daglab:
  storage:
    type: "s3"
    bucket: "my-daglab-bucket"
    region: "us-west-2"
    
    # Credentials (prefer IAM roles)
    access_key: "${AWS_ACCESS_KEY_ID}"
    secret_key: "${AWS_SECRET_ACCESS_KEY}"
    
    # S3 configuration
    prefix: "daglab/"
    encryption: "AES256"
    storage_class: "STANDARD"  # STANDARD, IA, GLACIER
    
    # Transfer settings
    multipart_threshold: "64MB"
    multipart_chunksize: "16MB"
    max_concurrency: 10
```

### Google Cloud Storage

```yaml
daglab:
  storage:
    type: "gcs"
    bucket: "my-daglab-bucket"
    project_id: "my-gcp-project"
    
    # Credentials
    credentials_path: "/path/to/service-account.json"
    
    # GCS configuration
    prefix: "daglab/"
    storage_class: "STANDARD"  # STANDARD, NEARLINE, COLDLINE
```

### Azure Blob Storage

```yaml
daglab:
  storage:
    type: "azure"
    container: "daglab-container"
    account_name: "mystorageaccount"
    account_key: "${AZURE_STORAGE_KEY}"
    
    # Azure configuration
    prefix: "daglab/"
    tier: "Hot"  # Hot, Cool, Archive
```

## Security Configuration

### Authentication & Authorization

```yaml
daglab:
  security:
    enable_auth: true
    auth_backend: "database"   # database, ldap, oauth
    
    # JWT configuration
    secret_key: "${SECRET_KEY}"
    jwt_algorithm: "HS256"
    jwt_expiration: 3600       # 1 hour
    refresh_token_expiration: 604800  # 1 week
    
    # Password policy
    password_policy:
      min_length: 8
      require_uppercase: true
      require_lowercase: true
      require_numbers: true
      require_special_chars: true
      
    # Session management
    session_timeout: 1800      # 30 minutes
    max_concurrent_sessions: 5
```

### LDAP Authentication

```yaml
daglab:
  security:
    auth_backend: "ldap"
    ldap:
      server: "ldap://ldap.company.com"
      bind_dn: "cn=admin,dc=company,dc=com"
      bind_password: "${LDAP_PASSWORD}"
      user_search_base: "ou=users,dc=company,dc=com"
      user_filter: "(uid={username})"
      group_search_base: "ou=groups,dc=company,dc=com"
      
      # Attribute mapping
      username_attr: "uid"
      email_attr: "mail"
      first_name_attr: "givenName"
      last_name_attr: "sn"
```

### OAuth 2.0 Configuration

```yaml
daglab:
  security:
    auth_backend: "oauth"
    oauth:
      provider: "google"       # google, github, azure
      client_id: "${OAUTH_CLIENT_ID}"
      client_secret: "${OAUTH_CLIENT_SECRET}"
      redirect_uri: "http://localhost:8080/auth/callback"
      scope: "openid email profile"
```

### Role-Based Access Control (RBAC)

```yaml
daglab:
  security:
    rbac:
      enabled: true
      
      # Default roles
      roles:
        admin:
          permissions: ["*"]
        dag_author:
          permissions: ["dag:create", "dag:edit", "dag:delete", "dag:run"]
        dag_viewer:
          permissions: ["dag:view", "dag:run"]
        operator:
          permissions: ["dag:run", "dag:view", "task:view"]
          
      # Resource-based permissions
      resources:
        dag:
          permissions: ["create", "edit", "delete", "view", "run"]
        task:
          permissions: ["view", "run", "kill"]
        user:
          permissions: ["create", "edit", "delete", "view"]
```

## Logging Configuration

### Basic Logging

```yaml
daglab:
  logging:
    level: "INFO"
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: "%Y-%m-%d %H:%M:%S"
    
    # Console logging
    console:
      enabled: true
      level: "INFO"
      
    # File logging
    file:
      enabled: true
      path: "./logs/daglab.log"
      level: "DEBUG"
      max_size: "100MB"
      backup_count: 5
      rotation: "time"          # time, size
      rotation_interval: "midnight"
```

### Structured Logging

```yaml
daglab:
  logging:
    format: "json"             # json, text
    
    # JSON logging configuration
    json_format:
      timestamp_field: "@timestamp"
      level_field: "level"
      message_field: "message"
      logger_field: "logger"
      
    # Additional fields
    extra_fields:
      environment: "${ENVIRONMENT}"
      service: "daglab"
      version: "1.0.0"
```

### External Logging

```yaml
daglab:
  logging:
    # Syslog
    syslog:
      enabled: true
      host: "localhost"
      port: 514
      facility: "local0"
      
    # ELK Stack
    elasticsearch:
      enabled: true
      hosts: ["elasticsearch:9200"]
      index_pattern: "daglab-logs-%Y.%m.%d"
      
    # Fluentd
    fluentd:
      enabled: true
      host: "fluentd"
      port: 24224
      tag: "daglab"
```

## Monitoring Configuration

### Prometheus Metrics

```yaml
daglab:
  monitoring:
    metrics:
      enabled: true
      backend: "prometheus"
      
      # Prometheus configuration
      prometheus:
        port: 9090
        path: "/metrics"
        registry: "default"
        
        # Custom metrics
        custom_metrics:
          - name: "dag_execution_duration"
            type: "histogram"
            description: "DAG execution duration"
            buckets: [1, 5, 10, 30, 60, 300, 600]
            
          - name: "task_failure_rate"
            type: "counter"
            description: "Task failure rate"
```

### Health Checks

```yaml
daglab:
  monitoring:
    health_checks:
      enabled: true
      endpoint: "/health"
      interval: 30              # seconds
      
      # Health check components
      checks:
        database:
          enabled: true
          timeout: 5
        storage:
          enabled: true
          timeout: 5
        executor:
          enabled: true
          timeout: 10
```

### Alerting

```yaml
daglab:
  monitoring:
    alerting:
      enabled: true
      
      # Alert channels
      channels:
        email:
          enabled: true
          smtp_server: "smtp.company.com"
          recipients: ["admin@company.com"]
          
        slack:
          enabled: true
          webhook_url: "${SLACK_WEBHOOK_URL}"
          channel: "#daglab-alerts"
          
        pagerduty:
          enabled: true
          integration_key: "${PAGERDUTY_KEY}"
          
      # Alert rules
      rules:
        - name: "dag_failure"
          condition: "dag_status == 'failed'"
          severity: "critical"
          cooldown: 300
          
        - name: "high_memory_usage"
          condition: "memory_usage > 0.9"
          severity: "warning"
          cooldown: 600
```

## Scheduler Configuration

### Cron Scheduler

```yaml
daglab:
  scheduler:
    type: "cron"
    timezone: "UTC"
    
    # Scheduling behavior
    catchup: false             # Run missed schedules
    max_active_runs: 1         # Concurrent DAG runs
    start_date: "2024-01-01"   # Default start date
    
    # Performance settings
    schedule_interval: 10      # Scheduler check interval
    max_threads: 4             # Scheduler threads
    
    # Retry configuration
    retry_policy:
      max_retries: 3
      retry_delay: 300
```

### Advanced Scheduling

```yaml
daglab:
  scheduler:
    # Custom scheduling
    custom_schedules:
      business_hours:
        cron: "0 9-17 * * 1-5"  # Weekdays 9 AM - 5 PM
        timezone: "America/New_York"
        
      end_of_month:
        cron: "0 0 L * *"       # Last day of month
        
    # Schedule dependencies
    schedule_dependencies:
      enabled: true
      wait_for_completion: true
      timeout: 3600
```

## Integration Configuration

### Webhook Integration

```yaml
daglab:
  integrations:
    webhooks:
      enabled: true
      base_url: "http://localhost:8080"
      
      # Webhook security
      secret_token: "${WEBHOOK_SECRET}"
      verify_ssl: true
      timeout: 30
      
      # Event subscriptions
      events:
        - "dag.started"
        - "dag.completed"
        - "dag.failed"
        - "task.failed"
        
      # Webhook endpoints
      endpoints:
        slack_notifications:
          url: "${SLACK_WEBHOOK_URL}"
          events: ["dag.failed", "task.failed"]
          
        custom_api:
          url: "https://api.mycompany.com/daglab-webhook"
          events: ["dag.completed"]
          headers:
            Authorization: "Bearer ${API_TOKEN}"
```

### Email Integration

```yaml
daglab:
  integrations:
    email:
      enabled: true
      
      # SMTP configuration
      smtp_server: "smtp.gmail.com"
      smtp_port: 587
      use_tls: true
      username: "${EMAIL_USERNAME}"
      password: "${EMAIL_PASSWORD}"
      
      # Email settings
      from_address: "daglab@company.com"
      from_name: "DagLab System"
      
      # Templates
      templates:
        dag_failure:
          subject: "DAG Failed: {dag_id}"
          body_template: "templates/dag_failure_email.html"
          
        dag_success:
          subject: "DAG Completed: {dag_id}"
          body_template: "templates/dag_success_email.html"
```

## Performance Tuning

### Memory Management

```yaml
daglab:
  performance:
    memory:
      max_memory_per_task: "1GB"
      gc_threshold: 0.8         # Trigger GC at 80% memory
      memory_profiling: false
      
    # Connection pooling
    connection_pools:
      database:
        pool_size: 20
        max_overflow: 30
        pool_recycle: 3600
        
      redis:
        max_connections: 50
        
    # Caching
    cache:
      enabled: true
      backend: "redis"          # redis, memory, file
      ttl: 3600                 # Default TTL in seconds
      max_size: "100MB"
```

### Optimization Settings

```yaml
daglab:
  optimization:
    # Task execution optimization
    task_optimization:
      parallel_execution: true
      dependency_optimization: true
      resource_allocation: "dynamic"
      
    # I/O optimization
    io_optimization:
      async_io: true
      buffer_size: "64KB"
      compression: true
      
    # Database optimization
    database_optimization:
      query_optimization: true
      index_hints: true
      batch_size: 1000
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
    echo: true                 # Enable SQL logging
    
  logging:
    level: "DEBUG"
    console:
      enabled: true
      
  executor:
    type: "local"
    max_parallel_tasks: 2
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
    
  logging:
    level: "INFO"
    file:
      enabled: true
      path: "/var/log/daglab/daglab.log"
      
  security:
    enable_auth: true
    secret_key: "${PRODUCTION_SECRET_KEY}"
    
  monitoring:
    enabled: true
    metrics:
      enabled: true
```

## Configuration Validation

### Validate Configuration

```bash
# Validate main configuration
daglab validate-config

# Validate specific configuration file
daglab validate-config --config config/production.yaml

# Check configuration syntax
daglab config-check --syntax-only

# Show resolved configuration (with env vars)
daglab config-show --resolved
```

### Configuration Schema

DagLab validates configuration against a JSON schema. You can export the schema for IDE integration:

```bash
# Export configuration schema
daglab export-schema --output daglab-config-schema.json

# Validate against schema (using external tools)
jsonschema -i config/daglab.yaml daglab-config-schema.json
```

## Best Practices

### Security Best Practices

1. **Never store secrets in configuration files**
   - Use environment variables for sensitive data
   - Consider using secret management tools (Vault, AWS Secrets Manager)

2. **Enable authentication in production**
   - Use strong secret keys
   - Implement proper RBAC
   - Regular security audits

3. **Secure database connections**
   - Use SSL/TLS for database connections
   - Implement connection encryption
   - Regular password rotation

### Performance Best Practices

1. **Right-size your executor**
   - Start with local executor for development
   - Use Celery for distributed workloads
   - Consider Kubernetes for cloud-native deployments

2. **Optimize database configuration**
   - Use connection pooling
   - Monitor and tune pool sizes
   - Regular database maintenance

3. **Configure appropriate logging levels**
   - Use DEBUG only in development
   - Implement log rotation
   - Monitor log storage usage

### Operational Best Practices

1. **Environment separation**
   - Use different configurations for each environment
   - Implement proper CI/CD for configuration changes
   - Version control all configuration files

2. **Monitoring and alerting**
   - Enable comprehensive monitoring
   - Set up alerting for critical failures
   - Regular health checks

3. **Backup and recovery**
   - Regular database backups
   - Configuration backup procedures
   - Disaster recovery planning

## Troubleshooting Configuration

### Common Configuration Issues

1. **Database connection failures**
   ```bash
   # Test database connection
   daglab test-db-connection
   ```

2. **Permission errors**
   ```bash
   # Check file permissions
   daglab check-permissions
   ```

3. **Environment variable issues**
   ```bash
   # Show resolved configuration
   daglab config-show --resolved
   ```

4. **Syntax errors**
   ```bash
   # Validate YAML syntax
   daglab config-check --syntax-only
   ```

## Next Steps

After configuring DagLab:

1. Review [CLI Commands](./cli-commands.md) for operational commands
2. Explore [Workflow Management](./workflow-management.md) for advanced workflows
3. Check [Deployment Guide](../deployment/README.md) for production deployment
4. See [Troubleshooting](../troubleshooting/common-issues.md) for common issues

For more advanced configurations and use cases, refer to the specific integration guides in the documentation.
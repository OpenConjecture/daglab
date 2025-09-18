# Best Practices

This guide outlines best practices for designing, implementing, and maintaining workflows in DagLab. Following these practices will help you build robust, scalable, and maintainable data pipelines.

## Workflow Design Best Practices

### 1. Design Principles

#### Idempotency
Ensure tasks produce the same result when executed multiple times:

```yaml
# ✅ Good - Idempotent task
- id: process_daily_data
  type: python_script
  config:
    script: |
      import pandas as pd
      from datetime import datetime
      
      # Use execution date for consistent results
      date = "{{ ds }}"
      
      # Clear existing output first
      output_file = f"data/processed/daily_data_{date}.csv"
      if os.path.exists(output_file):
          os.remove(output_file)
      
      # Process and save
      df = process_data_for_date(date)
      df.to_csv(output_file, index=False)

# ❌ Bad - Non-idempotent task
- id: append_data
  type: python_script
  config:
    script: |
      # This appends data each time, causing duplicates
      df = process_data()
      df.to_csv("data/output.csv", mode="a", header=False)
```

#### Atomicity
Each task should be a single, indivisible unit of work:

```yaml
# ✅ Good - Atomic tasks
- id: extract_customer_data
  type: database_query
  config:
    query: "SELECT * FROM customers WHERE updated_at >= '{{ ds }}'"
    
- id: validate_customer_data
  type: data_validator
  depends_on: [extract_customer_data]
  
- id: transform_customer_data
  type: python_script
  depends_on: [validate_customer_data]

# ❌ Bad - Non-atomic task doing multiple things
- id: extract_validate_transform
  type: python_script
  config:
    script: |
      # This task does too many things
      data = extract_data()
      validated_data = validate_data(data)
      transformed_data = transform_data(validated_data)
      save_data(transformed_data)
```

#### Single Responsibility
Each task should have one clear purpose:

```yaml
# ✅ Good - Clear, single responsibilities
- id: download_external_data
  type: http_request
  config:
    url: "https://api.external.com/data"
    
- id: validate_schema
  type: schema_validator
  depends_on: [download_external_data]
  
- id: enrich_with_lookup_data
  type: data_enricher
  depends_on: [validate_schema]

# ❌ Bad - Mixed responsibilities
- id: download_and_process
  type: python_script
  config:
    script: |
      # Downloads, validates, transforms, and saves
      data = download_data()
      validated = validate(data)
      enriched = enrich(validated)
      transformed = transform(enriched)
      save(transformed)
```

### 2. Dependency Management

#### Minimize Dependencies
Keep dependencies simple and necessary:

```yaml
# ✅ Good - Minimal, necessary dependencies
tasks:
  - id: extract_orders
    type: database_query
    
  - id: extract_customers
    type: database_query
    
  - id: join_orders_customers
    type: data_joiner
    depends_on: [extract_orders, extract_customers]  # Only necessary deps
    
  - id: generate_report
    type: report_generator
    depends_on: [join_orders_customers]

# ❌ Bad - Unnecessary dependencies
tasks:
  - id: extract_orders
    type: database_query
    
  - id: extract_customers
    type: database_query
    
  - id: join_orders_customers
    type: data_joiner
    depends_on: [extract_orders, extract_customers]
    
  - id: generate_report
    type: report_generator
    depends_on: [extract_orders, extract_customers, join_orders_customers]  # Unnecessary deps
```

#### Use Parallel Execution
Leverage parallelism for independent tasks:

```yaml
# ✅ Good - Parallel extraction
dag:
  id: parallel_data_pipeline
  max_active_tasks: 10

tasks:
  # These can run in parallel
  - id: extract_sales_data
    type: api_request
    
  - id: extract_inventory_data
    type: database_query
    
  - id: extract_customer_data
    type: file_reader
    
  # This waits for all extractions to complete
  - id: merge_all_data
    type: data_merger
    depends_on: [extract_sales_data, extract_inventory_data, extract_customer_data]
```

### 3. Error Handling and Resilience

#### Implement Comprehensive Retry Logic
Configure retries for transient failures:

```yaml
# ✅ Good - Comprehensive retry configuration
- id: external_api_call
  type: http_request
  config:
    url: "https://api.external.com/data"
    timeout: 30
  
  retry_policy:
    max_retries: 5
    retry_delay: 300              # 5 minutes initial delay
    exponential_backoff: true
    max_retry_delay: 3600         # Max 1 hour between retries
    retry_on_status: [500, 502, 503, 504, 429]
    
  # Notification on final failure
  on_failure:
    - type: email_notification
      config:
        to: ["team@company.com"]
        subject: "API call failed after {{ task.retry_number }} retries"
```

#### Use Circuit Breaker Pattern
Protect against cascading failures:

```yaml
# ✅ Good - Circuit breaker implementation
- id: check_external_service_health
  type: health_check
  config:
    url: "https://external-service.com/health"
    timeout: 10
    
- id: call_external_service
  type: http_request
  depends_on: [check_external_service_health]
  condition: "{{ task_instance.xcom_pull('check_external_service_health')['healthy'] }}"
  config:
    url: "https://external-service.com/api/data"
    
- id: use_cached_data
  type: file_reader
  depends_on: [check_external_service_health]
  condition: "{{ not task_instance.xcom_pull('check_external_service_health')['healthy'] }}"
  config:
    path: "data/cache/fallback_data.csv"
```

#### Implement Graceful Degradation
Provide fallback mechanisms:

```yaml
# ✅ Good - Multiple fallback options
- id: primary_data_source
  type: api_request
  config:
    url: "https://primary-api.com/data"
  retry_policy:
    max_retries: 2
    
- id: secondary_data_source
  type: api_request
  depends_on: [primary_data_source]
  condition: "{{ task_instance.xcom_pull('primary_data_source') is none }}"
  config:
    url: "https://backup-api.com/data"
    
- id: use_cached_data
  type: file_reader
  depends_on: [primary_data_source, secondary_data_source]
  condition: |
    {{
      task_instance.xcom_pull('primary_data_source') is none and
      task_instance.xcom_pull('secondary_data_source') is none
    }}
  config:
    path: "data/cache/latest_data.csv"
```

## Data Management Best Practices

### 1. Data Quality and Validation

#### Implement Data Quality Checks
Validate data at multiple stages:

```yaml
# ✅ Good - Comprehensive data validation
- id: extract_customer_data
  type: database_query
  config:
    query: "SELECT * FROM customers"
    
- id: validate_schema
  type: schema_validator
  depends_on: [extract_customer_data]
  config:
    schema_file: "schemas/customer_schema.json"
    
- id: validate_business_rules
  type: business_rule_validator
  depends_on: [validate_schema]
  config:
    rules:
      - field: "email"
        rule: "email_format"
      - field: "age"
        rule: "range"
        min: 0
        max: 150
      - field: "customer_id"
        rule: "unique"
        
- id: data_quality_report
  type: data_quality_reporter
  depends_on: [validate_business_rules]
  config:
    output_file: "reports/data_quality_{{ ds }}.html"
    fail_on_quality_threshold: 0.95
```

#### Use Data Contracts
Define clear data contracts between tasks:

```yaml
# data_contracts/customer_data.yaml
contract:
  name: "customer_data_v1"
  version: "1.0.0"
  description: "Customer data contract"
  
  schema:
    type: "object"
    required: ["customer_id", "email", "created_at"]
    properties:
      customer_id:
        type: "string"
        pattern: "^CUST[0-9]{8}$"
      email:
        type: "string"
        format: "email"
      created_at:
        type: "string"
        format: "date-time"
  
  quality_rules:
    completeness:
      customer_id: 1.0
      email: 0.95
    uniqueness:
      customer_id: 1.0
    validity:
      email: 0.98
```

### 2. Data Lineage and Versioning

#### Track Data Lineage
Maintain clear data lineage tracking:

```yaml
# ✅ Good - Clear lineage tracking
- id: extract_raw_data
  type: database_query
  config:
    query: "SELECT * FROM raw_customers"
  metadata:
    data_lineage:
      source: "production.raw_customers"
      extraction_method: "full_load"
      
- id: clean_customer_data
  type: data_cleaner
  depends_on: [extract_raw_data]
  metadata:
    data_lineage:
      source_task: "extract_raw_data"
      transformations: ["remove_duplicates", "standardize_phone", "validate_email"]
      
- id: enrich_customer_data
  type: data_enricher
  depends_on: [clean_customer_data]
  metadata:
    data_lineage:
      source_task: "clean_customer_data"
      enrichment_sources: ["external_demographic_api", "internal_preferences_db"]
```

#### Version Data Assets
Version important data assets:

```python
# ✅ Good - Data versioning
def save_processed_data(df, execution_date):
    # Version data with timestamp and hash
    data_hash = hashlib.md5(df.to_csv().encode()).hexdigest()[:8]
    version = f"{execution_date}_{data_hash}"
    
    # Save with version
    output_path = f"data/processed/customers_v{version}.parquet"
    df.to_parquet(output_path)
    
    # Update latest pointer
    latest_path = "data/processed/customers_latest.parquet"
    if os.path.exists(latest_path):
        os.remove(latest_path)
    os.symlink(output_path, latest_path)
    
    # Store metadata
    metadata = {
        "version": version,
        "execution_date": execution_date,
        "record_count": len(df),
        "data_hash": data_hash,
        "created_at": datetime.now().isoformat()
    }
    
    with open(f"data/processed/customers_v{version}.metadata.json", "w") as f:
        json.dump(metadata, f)
```

### 3. Performance Optimization

#### Optimize Data Processing
Use efficient data processing techniques:

```python
# ✅ Good - Efficient data processing
def process_large_dataset(input_file, output_file):
    # Use chunking for large files
    chunk_size = 10000
    
    # Process in chunks to manage memory
    for chunk in pd.read_csv(input_file, chunksize=chunk_size):
        processed_chunk = process_chunk(chunk)
        
        # Append to output file
        mode = 'w' if not os.path.exists(output_file) else 'a'
        header = not os.path.exists(output_file)
        processed_chunk.to_csv(output_file, mode=mode, header=header, index=False)

# ❌ Bad - Loading entire dataset into memory
def process_large_dataset_bad(input_file, output_file):
    # This will consume too much memory for large files
    df = pd.read_csv(input_file)  # Loads entire file into memory
    processed_df = process_data(df)
    processed_df.to_csv(output_file, index=False)
```

#### Use Appropriate Data Formats
Choose optimal data formats for your use case:

```yaml
# ✅ Good - Format selection based on use case
- id: save_transactional_data
  type: data_writer
  config:
    # Use Parquet for analytical workloads
    format: "parquet"
    compression: "snappy"
    output_path: "data/analytics/transactions.parquet"
    
- id: save_lookup_data
  type: data_writer
  config:
    # Use CSV for small reference data
    format: "csv"
    output_path: "data/reference/country_codes.csv"
    
- id: save_streaming_data
  type: data_writer
  config:
    # Use JSON Lines for streaming/append scenarios
    format: "jsonl"
    output_path: "data/streaming/events.jsonl"
```

## Security Best Practices

### 1. Credential Management

#### Use Environment Variables and Secret Stores
Never hardcode credentials:

```yaml
# ✅ Good - Using environment variables
- id: connect_to_database
  type: database_query
  config:
    connection_string: "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    query: "SELECT * FROM customers"

# Using secret management
- id: call_external_api
  type: http_request
  config:
    url: "https://api.external.com/data"
    headers:
      Authorization: "Bearer {{ secret('api_token') }}"

# ❌ Bad - Hardcoded credentials
- id: bad_database_connection
  type: database_query
  config:
    connection_string: "postgresql://user:password123@prod-db:5432/mydb"  # Never do this!
```

#### Implement Principle of Least Privilege
Grant minimal necessary permissions:

```yaml
# ✅ Good - Task-specific permissions
dag:
  id: customer_data_pipeline
  
  # DAG-level security context
  security_context:
    run_as_user: "daglab_worker"
    run_as_group: "data_processors"
    
tasks:
  - id: read_customer_data
    type: database_query
    security_context:
      # Read-only database user
      database_user: "readonly_user"
    config:
      connection: "customer_db_readonly"
      
  - id: write_processed_data
    type: database_insert
    security_context:
      # Write-only user for specific table
      database_user: "analytics_writer"
    config:
      connection: "analytics_db_write"
```

### 2. Data Protection

#### Encrypt Sensitive Data
Protect sensitive data in transit and at rest:

```yaml
# ✅ Good - Data encryption
- id: process_pii_data
  type: python_script
  config:
    script: |
      # Encrypt PII fields before processing
      df['ssn'] = encrypt_field(df['ssn'], encryption_key)
      df['credit_card'] = encrypt_field(df['credit_card'], encryption_key)
      
      # Process encrypted data
      processed_df = process_data(df)
      
      # Save with encryption
      processed_df.to_parquet(output_path, encryption='AES256')
      
  security_context:
    encryption_key_source: "vault"
```

#### Implement Data Masking
Mask sensitive data in non-production environments:

```python
# ✅ Good - Data masking for non-prod
def mask_sensitive_data(df, environment):
    if environment != 'production':
        # Mask email addresses
        df['email'] = df['email'].apply(lambda x: mask_email(x))
        
        # Mask phone numbers
        df['phone'] = df['phone'].apply(lambda x: 'XXX-XXX-' + x[-4:])
        
        # Replace SSN with fake data
        df['ssn'] = df['ssn'].apply(lambda x: generate_fake_ssn())
        
    return df
```

### 3. Audit and Compliance

#### Implement Comprehensive Logging
Log all security-relevant events:

```yaml
# ✅ Good - Comprehensive audit logging
- id: process_financial_data
  type: python_script
  config:
    script: |
      # Log data access
      audit_logger.info(f"Accessing financial data", extra={
          "user": context['user'],
          "dag_id": context['dag'].dag_id,
          "task_id": context['task'].task_id,
          "execution_date": context['ds'],
          "data_source": "financial_db"
      })
      
      # Process data
      df = load_financial_data()
      
      # Log data processing
      audit_logger.info(f"Processed {len(df)} financial records", extra={
          "record_count": len(df),
          "processing_time": processing_time
      })
```

## Performance Best Practices

### 1. Resource Management

#### Right-size Resource Allocations
Allocate appropriate resources for each task:

```yaml
# ✅ Good - Appropriate resource allocation
dag:
  id: ml_training_pipeline
  
tasks:
  - id: data_preprocessing
    type: python_script
    resources:
      memory: "4GB"     # Moderate memory for data prep
      cpu: 2
    config:
      script: "preprocess_data.py"
      
  - id: model_training
    type: ml_trainer
    resources:
      memory: "16GB"    # High memory for training
      cpu: 8
      gpu: 1           # GPU for deep learning
    config:
      model_type: "neural_network"
      
  - id: model_validation
    type: ml_validator
    resources:
      memory: "2GB"     # Low memory for validation
      cpu: 1
    config:
      validation_script: "validate_model.py"
```

#### Use Resource Pools
Organize resources into pools for better management:

```yaml
# Resource pool configuration
resource_pools:
  - name: "cpu_intensive"
    resources:
      cpu: 8
      memory: "8GB"
    max_concurrent_tasks: 4
    
  - name: "memory_intensive"
    resources:
      cpu: 2
      memory: "32GB"
    max_concurrent_tasks: 2
    
  - name: "gpu_pool"
    resources:
      cpu: 4
      memory: "16GB"
      gpu: 1
    max_concurrent_tasks: 1

# Use pools in tasks
tasks:
  - id: train_deep_learning_model
    type: ml_trainer
    resource_pool: "gpu_pool"
    
  - id: process_large_dataset
    type: data_processor
    resource_pool: "memory_intensive"
```

### 2. Caching and Optimization

#### Implement Smart Caching
Cache expensive computations intelligently:

```yaml
# ✅ Good - Strategic caching
- id: expensive_feature_engineering
  type: python_script
  config:
    script: "feature_engineering.py"
  
  # Cache based on input data hash
  cache:
    enabled: true
    key: "features_{{ input_data_hash }}"
    ttl: 86400  # 24 hours
    invalidate_on:
      - "input_data_changed"
      - "feature_config_changed"
      
- id: model_inference
  type: ml_inference
  depends_on: [expensive_feature_engineering]
  config:
    model_path: "models/production_model.pkl"
  
  # Cache predictions for batch inference
  cache:
    enabled: true
    key: "predictions_{{ model_version }}_{{ input_batch_id }}"
    ttl: 3600  # 1 hour
```

#### Optimize Database Operations
Use efficient database patterns:

```sql
-- ✅ Good - Optimized queries
-- Use indexes and proper WHERE clauses
SELECT customer_id, order_date, total_amount
FROM orders 
WHERE order_date >= '{{ ds }}' 
  AND order_date < '{{ next_ds }}'
  AND status = 'completed'
ORDER BY customer_id, order_date;

-- Use LIMIT for large result sets
SELECT *
FROM large_table
WHERE created_at >= '{{ ds }}'
ORDER BY created_at
LIMIT 100000;

-- ❌ Bad - Inefficient queries
-- Avoid SELECT * on large tables
SELECT * FROM large_table;

-- Avoid operations that prevent index usage
SELECT * FROM orders 
WHERE YEAR(order_date) = 2024;  -- This prevents index usage
```

## Monitoring and Observability

### 1. Comprehensive Monitoring

#### Implement Multi-level Monitoring
Monitor at DAG, task, and system levels:

```yaml
# ✅ Good - Multi-level monitoring
dag:
  id: production_data_pipeline
  
  # DAG-level monitoring
  monitoring:
    enabled: true
    metrics:
      - "dag_duration"
      - "dag_success_rate"
      - "dag_failure_rate"
    alerts:
      - name: "dag_duration_alert"
        condition: "dag_duration > 7200"  # 2 hours
        severity: "warning"
      - name: "dag_failure_alert"
        condition: "dag_failure_rate > 0.05"
        severity: "critical"

tasks:
  - id: critical_data_processing
    type: python_script
    
    # Task-level monitoring
    monitoring:
      enabled: true
      metrics:
        - "task_duration"
        - "memory_usage"
        - "records_processed"
      alerts:
        - name: "task_timeout"
          condition: "task_duration > 3600"
          action: "kill_and_notify"
        - name: "memory_limit"
          condition: "memory_usage > 0.9"
          action: "scale_up"
```

#### Use Custom Metrics
Implement business-specific metrics:

```python
# ✅ Good - Custom business metrics
from daglab.metrics import Metrics

def process_orders(execution_date):
    metrics = Metrics()
    
    # Business metrics
    orders = load_orders(execution_date)
    
    metrics.gauge('daily_order_count', len(orders))
    metrics.gauge('daily_revenue', orders['amount'].sum())
    metrics.gauge('average_order_value', orders['amount'].mean())
    
    # Data quality metrics
    valid_orders = orders[orders['email'].str.contains('@')]
    metrics.gauge('email_validation_rate', len(valid_orders) / len(orders))
    
    # Processing metrics
    start_time = time.time()
    processed_orders = process_order_data(orders)
    processing_time = time.time() - start_time
    
    metrics.timer('order_processing_duration', processing_time)
    metrics.gauge('processing_throughput', len(orders) / processing_time)
    
    return processed_orders
```

### 2. Alerting Strategy

#### Implement Tiered Alerting
Use different alert levels for different scenarios:

```yaml
# ✅ Good - Tiered alerting system
alerting:
  channels:
    - name: "critical_alerts"
      type: "pagerduty"
      config:
        integration_key: "${PAGERDUTY_KEY}"
        
    - name: "warning_alerts"
      type: "slack"
      config:
        webhook_url: "${SLACK_WEBHOOK}"
        channel: "#data-alerts"
        
    - name: "info_alerts"
      type: "email"
      config:
        recipients: ["data-team@company.com"]

  rules:
    # Critical - Immediate attention required
    - name: "pipeline_failure"
      condition: "dag_state == 'failed'"
      severity: "critical"
      channels: ["critical_alerts", "warning_alerts"]
      
    # Warning - Attention needed soon
    - name: "data_quality_degradation"
      condition: "data_quality_score < 0.95"
      severity: "warning"
      channels: ["warning_alerts"]
      
    # Info - For awareness
    - name: "unusual_data_volume"
      condition: "record_count > avg_record_count * 1.5"
      severity: "info"
      channels: ["info_alerts"]
```

## Testing Best Practices

### 1. Test Strategy

#### Implement Comprehensive Testing
Test at multiple levels:

```python
# Unit tests for individual tasks
class TestDataProcessingTask(unittest.TestCase):
    def test_data_transformation(self):
        # Test data transformation logic
        input_data = create_test_data()
        result = transform_data(input_data)
        self.assertEqual(len(result), expected_count)
        
    def test_error_handling(self):
        # Test error scenarios
        with self.assertRaises(ValidationError):
            transform_data(invalid_data)

# Integration tests for DAG workflows
class TestDataPipelineIntegration(DAGTestCase):
    def test_complete_pipeline(self):
        # Test end-to-end pipeline
        result = self.run_dag("data_pipeline", test_data)
        self.assertEqual(result.state, "success")
        self.verify_output_quality()
        
    def test_failure_scenarios(self):
        # Test failure handling
        with self.mock_database_failure():
            result = self.run_dag("data_pipeline")
            self.assertEqual(result.state, "failed")
            self.verify_alerts_sent()
```

### 2. Data Testing

#### Test Data Quality
Implement automated data quality tests:

```python
# ✅ Good - Automated data quality tests
def test_data_quality(df):
    # Schema validation
    assert all(col in df.columns for col in required_columns)
    
    # Completeness tests
    assert df['customer_id'].isnull().sum() == 0
    assert df['email'].isnull().sum() / len(df) < 0.05
    
    # Validity tests
    assert df['email'].str.contains('@').all()
    assert (df['age'] >= 0).all() and (df['age'] <= 150).all()
    
    # Consistency tests
    assert df['order_date'] <= datetime.now().date()
    assert df['total_amount'] >= 0
    
    # Uniqueness tests
    assert df['customer_id'].duplicated().sum() == 0
    
    return True
```

## Deployment and Operations

### 1. Environment Management

#### Use Environment-specific Configurations
Maintain separate configurations for different environments:

```yaml
# config/development.yaml
daglab:
  database:
    url: "sqlite:///dev_daglab.db"
  executor:
    type: "local"
    max_parallel_tasks: 2
  logging:
    level: "DEBUG"

# config/staging.yaml
daglab:
  database:
    url: "postgresql://user:pass@staging-db:5432/daglab"
  executor:
    type: "celery"
    max_parallel_tasks: 4
  logging:
    level: "INFO"

# config/production.yaml
daglab:
  database:
    url: "postgresql://user:pass@prod-db:5432/daglab"
  executor:
    type: "kubernetes"
    max_parallel_tasks: 20
  logging:
    level: "WARNING"
  monitoring:
    enabled: true
```

### 2. CI/CD Integration

#### Implement Automated Deployment Pipeline
Use CI/CD for DAG deployment:

```yaml
# .github/workflows/daglab-deployment.yml
name: DagLab Deployment

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate DAGs
        run: |
          daglab validate --all
          daglab test --coverage
          
  deploy-staging:
    needs: validate
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Staging
        run: |
          daglab deploy --environment staging
          daglab test --environment staging --smoke-test
          
  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy to Production
        run: |
          daglab deploy --environment production
          daglab test --environment production --smoke-test
```

## Documentation Best Practices

### 1. Code Documentation

#### Document DAGs and Tasks Thoroughly
Provide comprehensive documentation:

```yaml
# ✅ Good - Well-documented DAG
dag:
  id: customer_analytics_pipeline
  description: |
    Customer analytics pipeline that processes daily customer data,
    performs segmentation analysis, and generates business intelligence reports.
    
    This pipeline runs daily at 2 AM UTC and processes the previous day's data.
    It includes data validation, quality checks, and automated alerting.
    
    Dependencies:
    - Customer database (PostgreSQL)
    - External demographic API
    - S3 storage for reports
    
    Outputs:
    - Customer segments in data warehouse
    - Daily analytics dashboard
    - Email reports to stakeholders
    
  schedule: "0 2 * * *"
  tags: [analytics, customer, daily]
  
  # Ownership and contacts
  owner: "data-team@company.com"
  contacts:
    primary: "john.doe@company.com"
    secondary: "jane.smith@company.com"
    
  # SLA and expectations
  sla_duration: "4h"  # Must complete within 4 hours
  expected_duration: "2h"  # Typically takes 2 hours

tasks:
  - id: extract_customer_data
    description: |
      Extracts customer data from the production database for the previous day.
      
      Includes:
      - Customer profile information
      - Transaction history
      - Interaction logs
      
      Quality checks:
      - Validates data completeness
      - Checks for duplicate records
      - Verifies data freshness
    type: database_query
    
    # Task metadata
    owner: "data-engineering@company.com"
    estimated_duration: "15m"
    dependencies: ["production database availability"]
```

### 2. Operational Documentation

#### Maintain Runbooks and Troubleshooting Guides
Document operational procedures:

```markdown
# Customer Analytics Pipeline Runbook

## Overview
The customer analytics pipeline processes daily customer data and generates business intelligence reports.

## Monitoring
- **Dashboard**: https://monitoring.company.com/daglab/customer-analytics
- **Alerts**: Sent to #data-alerts Slack channel
- **SLA**: Must complete within 4 hours of start time

## Common Issues and Solutions

### Issue: Database Connection Timeout
**Symptoms**: Task fails with "connection timeout" error
**Solution**: 
1. Check database health dashboard
2. Verify network connectivity
3. Restart task if issue is transient

### Issue: Data Quality Failure
**Symptoms**: Data validation task fails
**Solution**:
1. Check data quality report
2. Investigate upstream data sources
3. Contact data source owners if needed

## Emergency Procedures

### Pipeline Failure
1. Check monitoring dashboard for root cause
2. Review task logs for error details
3. If critical, run manual data export
4. Notify stakeholders via email template

### Data Corruption
1. Stop pipeline immediately
2. Restore from last known good backup
3. Investigate corruption source
4. Implement additional validation

## Contacts
- **Primary**: Data Engineering Team (data-eng@company.com)
- **Secondary**: Data Science Team (data-science@company.com)
- **Emergency**: On-call engineer (oncall@company.com)
```

This comprehensive best practices guide covers the essential aspects of building robust, maintainable workflows in DagLab. Following these practices will help ensure your data pipelines are reliable, performant, and easy to operate.
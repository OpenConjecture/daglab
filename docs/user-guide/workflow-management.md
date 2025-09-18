# Workflow Management

This guide covers advanced workflow management techniques in DagLab, including complex DAG patterns, dependency management, and optimization strategies.

## Workflow Fundamentals

### Understanding DAGs

A Directed Acyclic Graph (DAG) in DagLab represents a workflow where:
- **Nodes** are tasks that perform specific operations
- **Edges** represent dependencies between tasks
- **Acyclic** means no circular dependencies
- **Directed** means dependencies flow in one direction

### Basic DAG Structure

```yaml
dag:
  id: data_processing_pipeline
  description: "Process customer data and generate reports"
  schedule: "0 2 * * *"  # Daily at 2 AM
  tags: [data, etl, reports]
  
  # DAG-level configuration
  max_active_runs: 1
  catchup: false
  start_date: "2024-01-01"
  
tasks:
  - id: extract_customer_data
    type: database_query
    config:
      connection: "customer_db"
      query: "SELECT * FROM customers WHERE updated_at > '{{ yesterday }}'"
      
  - id: validate_data
    type: data_validator
    depends_on: [extract_customer_data]
    config:
      schema_file: "schemas/customer_schema.json"
      
  - id: transform_data
    type: python_script
    depends_on: [validate_data]
    config:
      script_file: "scripts/transform_customers.py"
      
  - id: load_data
    type: database_insert
    depends_on: [transform_data]
    config:
      connection: "warehouse_db"
      table: "customers_processed"
      
  - id: generate_report
    type: report_generator
    depends_on: [load_data]
    config:
      template: "customer_report_template.html"
      output: "reports/customer_report_{{ ds }}.pdf"
```

## Advanced Workflow Patterns

### Parallel Processing

Execute multiple tasks concurrently to improve performance:

```yaml
dag:
  id: parallel_data_processing
  
tasks:
  # Extract from multiple sources in parallel
  - id: extract_sales_data
    type: api_request
    config:
      url: "https://api.sales.com/data"
      
  - id: extract_inventory_data
    type: database_query
    config:
      query: "SELECT * FROM inventory"
      
  - id: extract_customer_data
    type: file_reader
    config:
      path: "data/customers.csv"
  
  # Process each dataset independently
  - id: process_sales
    type: python_script
    depends_on: [extract_sales_data]
    config:
      script: "process_sales.py"
      
  - id: process_inventory
    type: python_script
    depends_on: [extract_inventory_data]
    config:
      script: "process_inventory.py"
      
  - id: process_customers
    type: python_script
    depends_on: [extract_customer_data]
    config:
      script: "process_customers.py"
  
  # Combine results after all processing is complete
  - id: merge_datasets
    type: data_merger
    depends_on: [process_sales, process_inventory, process_customers]
    config:
      output_file: "data/merged_data.parquet"
```

### Conditional Execution

Execute tasks based on conditions or previous task outcomes:

```yaml
dag:
  id: conditional_workflow
  
tasks:
  - id: check_data_availability
    type: python_script
    config:
      script: |
        import os
        from datetime import datetime
        
        data_file = f"data/input_{datetime.now().strftime('%Y%m%d')}.csv"
        if os.path.exists(data_file):
            return {"data_available": True, "file_path": data_file}
        else:
            return {"data_available": False}
            
  - id: process_data
    type: python_script
    depends_on: [check_data_availability]
    condition: "{{ task_instance.xcom_pull('check_data_availability')['data_available'] }}"
    config:
      script: "process_daily_data.py"
      
  - id: send_no_data_alert
    type: email_notification
    depends_on: [check_data_availability]
    condition: "{{ not task_instance.xcom_pull('check_data_availability')['data_available'] }}"
    config:
      to: ["admin@company.com"]
      subject: "No data available for processing"
      
  - id: generate_report
    type: report_generator
    depends_on: [process_data]
    config:
      template: "daily_report.html"
```

### Dynamic Task Generation

Generate tasks dynamically based on runtime data:

```yaml
dag:
  id: dynamic_processing
  
tasks:
  - id: discover_files
    type: python_script
    config:
      script: |
        import os
        import glob
        
        files = glob.glob("data/input/*.csv")
        return {"files_to_process": files}
        
  - id: process_file
    type: python_script
    dynamic: true
    depends_on: [discover_files]
    config:
      script: |
        # This task will be created for each file
        file_path = "{{ task_instance.xcom_pull('discover_files')['files_to_process'][task_index] }}"
        # Process the file
        process_csv_file(file_path)
        
  - id: combine_results
    type: data_merger
    depends_on: [process_file]
    config:
      input_pattern: "output/processed_*.csv"
      output_file: "output/combined_results.csv"
```

### Branching Workflows

Create different execution paths based on conditions:

```yaml
dag:
  id: branching_workflow
  
tasks:
  - id: analyze_data_quality
    type: data_quality_checker
    config:
      input_file: "data/daily_input.csv"
      quality_threshold: 0.95
      
  - id: high_quality_processing
    type: python_script
    depends_on: [analyze_data_quality]
    condition: "{{ task_instance.xcom_pull('analyze_data_quality')['quality_score'] >= 0.95 }}"
    config:
      script: "standard_processing.py"
      
  - id: low_quality_processing
    type: python_script
    depends_on: [analyze_data_quality]
    condition: "{{ task_instance.xcom_pull('analyze_data_quality')['quality_score'] < 0.95 }}"
    config:
      script: "enhanced_cleaning_processing.py"
      
  - id: quality_report
    type: report_generator
    depends_on: [analyze_data_quality]
    config:
      template: "quality_report.html"
      
  - id: final_validation
    type: data_validator
    depends_on: [high_quality_processing, low_quality_processing]
    config:
      validation_rules: "final_validation_rules.json"
```

## Task Types and Configuration

### Built-in Task Types

#### Python Script Tasks
```yaml
- id: data_transformation
  type: python_script
  config:
    script_file: "scripts/transform.py"        # External file
    script: |                                  # Inline script
      import pandas as pd
      
      def transform_data(input_data):
          # Transformation logic
          return processed_data
    
    # Python environment
    python_path: "/opt/python/bin/python"
    virtual_env: "/opt/venvs/daglab"
    requirements: ["pandas>=1.3.0", "numpy>=1.20.0"]
    
    # Resource limits
    memory_limit: "2GB"
    cpu_limit: 2
    timeout: 3600
```

#### Database Tasks
```yaml
- id: database_operation
  type: database_query
  config:
    connection: "production_db"               # Connection name
    query_file: "sql/extract_customers.sql"  # External SQL file
    query: |                                 # Inline SQL
      SELECT customer_id, name, email
      FROM customers
      WHERE created_at >= '{{ ds }}'
    
    # Query parameters
    parameters:
      start_date: "{{ ds }}"
      end_date: "{{ next_ds }}"
    
    # Output configuration
    output_format: "parquet"                 # csv, json, parquet
    output_path: "data/customers_{{ ds }}.parquet"
    
    # Performance settings
    fetch_size: 10000
    timeout: 1800
```

#### HTTP/API Tasks
```yaml
- id: api_request
  type: http_request
  config:
    url: "https://api.example.com/data"
    method: "GET"                            # GET, POST, PUT, DELETE
    
    # Authentication
    auth_type: "bearer"                      # basic, bearer, oauth
    auth_token: "{{ var.api_token }}"
    
    # Headers and parameters
    headers:
      Content-Type: "application/json"
      User-Agent: "DagLab/1.0"
    params:
      date: "{{ ds }}"
      format: "json"
    
    # Request body (for POST/PUT)
    json_body:
      query: "SELECT * FROM data"
      filters: ["active", "verified"]
    
    # Response handling
    response_format: "json"
    response_path: "data/api_response_{{ ds }}.json"
    
    # Retry configuration
    retries: 3
    retry_delay: 60
    timeout: 300
```

#### File Operations
```yaml
- id: file_processing
  type: file_operation
  config:
    operation: "copy"                        # copy, move, delete, compress
    source: "data/raw/input_{{ ds }}.csv"
    destination: "data/processed/input_{{ ds }}.csv"
    
    # File processing options
    compression: "gzip"
    encoding: "utf-8"
    permissions: "0644"
    
    # Pattern matching
    pattern: "data/raw/*.csv"
    recursive: true
    
    # Transformation during copy
    transform:
      type: "csv_to_parquet"
      options:
        delimiter: ","
        quote_char: "\""
        compression: "snappy"
```

#### Email Notifications
```yaml
- id: send_notification
  type: email_notification
  config:
    to: ["team@company.com", "admin@company.com"]
    cc: ["manager@company.com"]
    subject: "DAG {{ dag.dag_id }} completed successfully"
    
    # Email content
    body_text: |
      The DAG {{ dag.dag_id }} has completed successfully.
      Execution date: {{ ds }}
      Duration: {{ dag_run.duration }}
    
    body_html_file: "templates/success_email.html"
    
    # Attachments
    attachments:
      - path: "reports/daily_report_{{ ds }}.pdf"
        name: "Daily Report"
      - path: "data/summary_{{ ds }}.csv"
        name: "Data Summary"
    
    # Conditional sending
    condition: "{{ dag_run.state == 'success' }}"
```

### Custom Task Types

Create custom task types for specialized operations:

```python
# custom_tasks/ml_model_task.py
from daglab.tasks import BaseTask
import joblib
import pandas as pd

class MLModelTask(BaseTask):
    def __init__(self, model_path, input_data, output_path, **kwargs):
        super().__init__(**kwargs)
        self.model_path = model_path
        self.input_data = input_data
        self.output_path = output_path
    
    def execute(self, context):
        # Load model
        model = joblib.load(self.model_path)
        
        # Load data
        data = pd.read_csv(self.input_data)
        
        # Make predictions
        predictions = model.predict(data)
        
        # Save results
        results = pd.DataFrame({
            'prediction': predictions,
            'confidence': model.predict_proba(data).max(axis=1)
        })
        results.to_csv(self.output_path, index=False)
        
        return {"predictions_count": len(predictions)}
```

Use custom task in DAG:
```yaml
- id: predict_customer_churn
  type: ml_model
  config:
    model_path: "models/churn_model.pkl"
    input_data: "data/customers_{{ ds }}.csv"
    output_path: "predictions/churn_predictions_{{ ds }}.csv"
```

## Dependency Management

### Simple Dependencies
```yaml
tasks:
  - id: task_a
    type: python_script
    
  - id: task_b
    type: python_script
    depends_on: [task_a]              # Single dependency
    
  - id: task_c
    type: python_script
    depends_on: [task_a, task_b]      # Multiple dependencies
```

### Complex Dependency Patterns

#### Fan-out Pattern
```yaml
tasks:
  - id: extract_data
    type: database_query
    
  # Multiple tasks depend on extract_data
  - id: process_orders
    type: python_script
    depends_on: [extract_data]
    
  - id: process_customers
    type: python_script
    depends_on: [extract_data]
    
  - id: process_products
    type: python_script
    depends_on: [extract_data]
```

#### Fan-in Pattern
```yaml
tasks:
  - id: process_sales
    type: python_script
    
  - id: process_inventory
    type: python_script
    
  - id: process_customers
    type: python_script
    
  # Single task depends on multiple upstream tasks
  - id: generate_report
    type: report_generator
    depends_on: [process_sales, process_inventory, process_customers]
```

#### Diamond Pattern
```yaml
tasks:
  - id: extract_data
    type: database_query
    
  - id: clean_data
    type: data_cleaner
    depends_on: [extract_data]
    
  - id: enrich_data
    type: data_enricher
    depends_on: [extract_data]
    
  - id: merge_and_analyze
    type: data_analyzer
    depends_on: [clean_data, enrich_data]
```

### Cross-DAG Dependencies

Create dependencies between different DAGs:

```yaml
# dag_a.yaml
dag:
  id: daily_etl
  
tasks:
  - id: process_daily_data
    type: python_script
    config:
      script: "process_daily.py"
```

```yaml
# dag_b.yaml
dag:
  id: weekly_report
  schedule: "0 8 * * 1"  # Monday at 8 AM
  
tasks:
  - id: wait_for_daily_etl
    type: external_dag_sensor
    config:
      external_dag_id: "daily_etl"
      external_task_id: "process_daily_data"
      days_back: 7  # Wait for last 7 days of daily ETL
      
  - id: generate_weekly_report
    type: report_generator
    depends_on: [wait_for_daily_etl]
    config:
      script: "weekly_report.py"
```

## Error Handling and Recovery

### Retry Configuration

Configure automatic retries for failed tasks:

```yaml
tasks:
  - id: unreliable_api_call
    type: http_request
    config:
      url: "https://unreliable-api.com/data"
    
    # Retry configuration
    retry_policy:
      max_retries: 5
      retry_delay: 300           # 5 minutes
      exponential_backoff: true
      max_retry_delay: 3600      # Max 1 hour between retries
      retry_on_status: [500, 502, 503, 504]
      
    # Email on final failure
    on_failure:
      - type: email_notification
        config:
          to: ["admin@company.com"]
          subject: "API call failed after {{ task.retry_number }} retries"
```

### Circuit Breaker Pattern

Implement circuit breaker for external dependencies:

```yaml
tasks:
  - id: check_external_service
    type: health_check
    config:
      url: "https://external-service.com/health"
      timeout: 30
      
  - id: call_external_service
    type: http_request
    depends_on: [check_external_service]
    condition: "{{ task_instance.xcom_pull('check_external_service')['status'] == 'healthy' }}"
    config:
      url: "https://external-service.com/api/data"
      
  - id: use_fallback_data
    type: file_reader
    depends_on: [check_external_service]
    condition: "{{ task_instance.xcom_pull('check_external_service')['status'] != 'healthy' }}"
    config:
      path: "data/fallback/cached_data.csv"
```

### Data Quality Validation

Implement data quality checks with recovery actions:

```yaml
tasks:
  - id: extract_data
    type: database_query
    config:
      query: "SELECT * FROM source_table"
      
  - id: validate_data_quality
    type: data_quality_validator
    depends_on: [extract_data]
    config:
      rules:
        - field: "customer_id"
          rule: "not_null"
        - field: "email"
          rule: "email_format"
        - field: "created_at"
          rule: "date_range"
          min_date: "2020-01-01"
      minimum_pass_rate: 0.95
      
  - id: process_clean_data
    type: python_script
    depends_on: [validate_data_quality]
    condition: "{{ task_instance.xcom_pull('validate_data_quality')['pass_rate'] >= 0.95 }}"
    config:
      script: "process_data.py"
      
  - id: data_cleaning_workflow
    type: sub_dag
    depends_on: [validate_data_quality]
    condition: "{{ task_instance.xcom_pull('validate_data_quality')['pass_rate'] < 0.95 }}"
    config:
      dag_file: "data_cleaning_dag.yaml"
```

## Performance Optimization

### Resource Management

Optimize resource usage for better performance:

```yaml
dag:
  id: resource_optimized_pipeline
  
  # DAG-level resource configuration
  default_resources:
    memory: "1GB"
    cpu: 1
    disk_space: "10GB"
  
tasks:
  - id: memory_intensive_task
    type: python_script
    config:
      script: "large_data_processing.py"
    
    # Task-specific resource overrides
    resources:
      memory: "8GB"
      cpu: 4
      disk_space: "50GB"
    
    # Resource monitoring
    resource_monitoring:
      enabled: true
      alert_threshold:
        memory: 0.9
        cpu: 0.8
      
  - id: io_intensive_task
    type: file_operation
    config:
      operation: "compress"
      source: "data/large_dataset.csv"
    
    resources:
      memory: "2GB"
      cpu: 1
      disk_space: "100GB"
      io_priority: "high"
```

### Parallel Execution Strategies

Optimize task execution through parallelization:

```yaml
dag:
  id: parallel_optimized_dag
  
  # Enable parallel execution
  max_active_tasks: 10
  parallel_execution: true
  
tasks:
  # Data partitioning for parallel processing
  - id: partition_data
    type: data_partitioner
    config:
      input_file: "data/large_dataset.csv"
      partition_size: 100000
      output_pattern: "data/partitions/part_{}.csv"
      
  - id: process_partition
    type: python_script
    dynamic: true
    depends_on: [partition_data]
    config:
      script: |
        partition_file = "{{ task_instance.xcom_pull('partition_data')['partitions'][task_index] }}"
        process_partition(partition_file)
    
    # Parallel execution configuration
    max_parallel_instances: 5
    
  - id: merge_results
    type: data_merger
    depends_on: [process_partition]
    config:
      input_pattern: "data/processed/part_*.csv"
      output_file: "data/final_result.csv"
```

### Caching Strategies

Implement caching to avoid redundant computations:

```yaml
tasks:
  - id: expensive_computation
    type: python_script
    config:
      script: "expensive_ml_training.py"
    
    # Caching configuration
    cache:
      enabled: true
      key: "ml_model_{{ ds }}"
      ttl: 86400  # 24 hours
      storage: "redis"  # redis, memory, file
      
  - id: use_cached_model
    type: python_script
    depends_on: [expensive_computation]
    config:
      script: |
        # Check if cached result exists
        cached_model = get_cached_result("ml_model_{{ ds }}")
        if cached_model:
            model = cached_model
        else:
            # Fallback to recomputation
            model = train_model()
```

## Monitoring and Observability

### Task-Level Monitoring

Add monitoring and alerting to tasks:

```yaml
tasks:
  - id: critical_data_processing
    type: python_script
    config:
      script: "process_critical_data.py"
    
    # Monitoring configuration
    monitoring:
      enabled: true
      metrics:
        - name: "processing_duration"
          type: "timer"
        - name: "records_processed"
          type: "counter"
        - name: "error_rate"
          type: "gauge"
      
      # Alerting rules
      alerts:
        - name: "processing_timeout"
          condition: "processing_duration > 3600"
          severity: "critical"
          action: "kill_task"
          
        - name: "high_error_rate"
          condition: "error_rate > 0.05"
          severity: "warning"
          action: "send_notification"
```

### Custom Metrics

Collect custom metrics from tasks:

```python
# In your task script
from daglab.metrics import Metrics

def process_data():
    metrics = Metrics()
    
    # Start timer
    with metrics.timer('data_processing_duration'):
        # Process data
        processed_records = 0
        for record in data:
            try:
                process_record(record)
                processed_records += 1
                metrics.increment('records_processed')
            except Exception as e:
                metrics.increment('processing_errors')
                
    # Set gauge metric
    metrics.gauge('processing_efficiency', processed_records / total_records)
    
    # Custom metric with tags
    metrics.increment('records_by_type', tags={'type': record_type})
```

### Health Checks

Implement health checks for external dependencies:

```yaml
tasks:
  - id: health_check_database
    type: health_check
    config:
      type: "database"
      connection: "production_db"
      query: "SELECT 1"
      timeout: 30
      
  - id: health_check_api
    type: health_check
    config:
      type: "http"
      url: "https://api.example.com/health"
      expected_status: 200
      timeout: 10
      
  - id: main_processing
    type: python_script
    depends_on: [health_check_database, health_check_api]
    condition: |
      {{
        task_instance.xcom_pull('health_check_database')['healthy'] and
        task_instance.xcom_pull('health_check_api')['healthy']
      }}
    config:
      script: "main_processing.py"
```

## Testing Workflows

### Unit Testing Tasks

Test individual tasks in isolation:

```python
# tests/test_data_processing.py
import unittest
from daglab.testing import TaskTestCase
from tasks.data_processing import DataProcessingTask

class TestDataProcessingTask(TaskTestCase):
    def test_data_transformation(self):
        # Setup test data
        test_input = "test_data/input.csv"
        expected_output = "test_data/expected_output.csv"
        
        # Create task instance
        task = DataProcessingTask(
            input_file=test_input,
            output_file="test_output.csv"
        )
        
        # Execute task
        result = task.execute(self.create_context())
        
        # Verify results
        self.assertTrue(result['success'])
        self.assert_files_equal("test_output.csv", expected_output)
```

### Integration Testing

Test complete DAG workflows:

```python
# tests/test_dag_integration.py
from daglab.testing import DAGTestCase

class TestDataPipelineDAG(DAGTestCase):
    def setUp(self):
        self.dag_file = "dags/data_pipeline.yaml"
        self.test_data_dir = "test_data/"
        
    def test_complete_pipeline(self):
        # Setup test environment
        self.setup_test_database()
        self.setup_test_files()
        
        # Run DAG
        result = self.run_dag(
            params={"test_mode": True},
            timeout=300
        )
        
        # Verify results
        self.assertEqual(result.state, "success")
        self.verify_output_data()
        
    def test_error_handling(self):
        # Simulate error condition
        self.inject_database_error()
        
        # Run DAG
        result = self.run_dag()
        
        # Verify error handling
        self.assertEqual(result.state, "failed")
        self.verify_error_notifications_sent()
```

### Load Testing

Test workflow performance under load:

```yaml
# Load testing configuration
load_test:
  dag_id: "data_processing_pipeline"
  
  scenarios:
    - name: "normal_load"
      concurrent_runs: 5
      duration: "1h"
      
    - name: "peak_load"
      concurrent_runs: 20
      duration: "30m"
      
    - name: "stress_test"
      concurrent_runs: 50
      duration: "15m"
  
  metrics:
    - "execution_time"
    - "memory_usage"
    - "cpu_usage"
    - "error_rate"
    
  thresholds:
    max_execution_time: "30m"
    max_memory_usage: "8GB"
    max_error_rate: "0.01"
```

## Best Practices

### Workflow Design Principles

1. **Idempotency**: Tasks should produce the same result when run multiple times
2. **Atomicity**: Each task should be a single, indivisible unit of work
3. **Determinism**: Task execution should be predictable and repeatable
4. **Isolation**: Tasks should not depend on external state changes
5. **Observability**: Include comprehensive logging and monitoring

### Performance Best Practices

1. **Optimize Dependencies**: Minimize unnecessary dependencies
2. **Use Parallel Execution**: Leverage parallelism where possible
3. **Implement Caching**: Cache expensive computations
4. **Resource Management**: Right-size resource allocations
5. **Data Partitioning**: Break large datasets into smaller chunks

### Error Handling Best Practices

1. **Graceful Degradation**: Implement fallback mechanisms
2. **Retry Logic**: Use exponential backoff for retries
3. **Circuit Breakers**: Protect against cascading failures
4. **Alerting**: Implement comprehensive alerting
5. **Recovery Procedures**: Document and automate recovery steps

### Security Best Practices

1. **Credential Management**: Use secure credential storage
2. **Access Control**: Implement proper permissions
3. **Data Encryption**: Encrypt sensitive data
4. **Audit Logging**: Log all security-relevant events
5. **Network Security**: Use secure communication protocols

## Troubleshooting Common Issues

### Dependency Resolution Problems

```bash
# Check dependency graph
daglab visualize my_dag --dependencies

# Validate dependency logic
daglab validate my_dag --check-dependencies

# Debug dependency cycles
daglab debug my_dag --check-cycles
```

### Performance Issues

```bash
# Profile DAG execution
daglab profile my_dag --detailed

# Analyze resource usage
daglab metrics my_dag --resource-usage

# Identify bottlenecks
daglab analyze my_dag --bottlenecks
```

### Data Quality Issues

```bash
# Validate data quality
daglab validate-data my_dag --rules data_quality_rules.json

# Check data lineage
daglab lineage my_dag --trace-data

# Generate data quality report
daglab report my_dag --data-quality
```

This comprehensive workflow management guide should help you design, implement, and optimize complex workflows in DagLab. For specific implementation details and advanced scenarios, refer to the [API Reference](../api-reference/README.md) and [Examples](../examples/) sections.
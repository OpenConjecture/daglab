# API Reference

This section provides comprehensive API documentation for DagLab, including REST APIs, Python APIs, and integration interfaces.

## Table of Contents

1. [REST API Overview](./rest-api.md)
2. [Python API Reference](./python-api.md)
3. [Task API](./task-api.md)
4. [Operator Reference](./operators.md)
5. [Configuration API](./configuration-api.md)
6. [Plugin Development API](./plugin-api.md)
7. [Webhook API](./webhook-api.md)
8. [Metrics and Monitoring API](./monitoring-api.md)

## API Overview

DagLab provides multiple API interfaces for different use cases:

### REST API
The REST API provides HTTP endpoints for:
- DAG management and execution
- Task monitoring and control
- System administration
- Data access and management

**Base URL**: `http://localhost:8080/api/v1`

**Authentication**: Bearer token, API key, or session-based

### Python API
The Python API offers programmatic access to DagLab functionality:
- DAG definition and creation
- Task development and testing
- Custom operator development
- System integration

### Task API
The Task API provides interfaces for:
- Custom task development
- Task execution context
- Inter-task communication
- Resource management

### Integration APIs
Various integration APIs support:
- Webhook notifications
- External system integration
- Plugin development
- Monitoring and metrics

## Quick Start Examples

### REST API Example
```bash
# Get all DAGs
curl -X GET "http://localhost:8080/api/v1/dags" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Run a DAG
curl -X POST "http://localhost:8080/api/v1/dags/my_dag/runs" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"execution_date": "2024-01-01T00:00:00Z"}'
```

### Python API Example
```python
from daglab import DAG, PythonOperator
from datetime import datetime

# Create a DAG
dag = DAG(
    'my_python_dag',
    description='Example DAG using Python API',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1)
)

# Define a task
def my_task():
    print("Hello from DagLab!")
    return "success"

# Add task to DAG
task = PythonOperator(
    task_id='hello_task',
    python_callable=my_task,
    dag=dag
)

# Register DAG
dag.register()
```

### Task Development Example
```python
from daglab.tasks import BaseTask
from daglab.exceptions import TaskException

class CustomTask(BaseTask):
    def __init__(self, input_file, output_file, **kwargs):
        super().__init__(**kwargs)
        self.input_file = input_file
        self.output_file = output_file
    
    def execute(self, context):
        """Execute the task logic"""
        try:
            # Task implementation
            data = self.load_data(self.input_file)
            processed_data = self.process_data(data)
            self.save_data(processed_data, self.output_file)
            
            return {"status": "success", "records_processed": len(processed_data)}
        except Exception as e:
            raise TaskException(f"Task failed: {str(e)}")
    
    def load_data(self, file_path):
        """Load data from file"""
        # Implementation
        pass
    
    def process_data(self, data):
        """Process data"""
        # Implementation
        pass
    
    def save_data(self, data, file_path):
        """Save processed data"""
        # Implementation
        pass
```

## Authentication and Authorization

### API Authentication Methods

#### Bearer Token Authentication
```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8080/api/v1/dags
```

#### API Key Authentication
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:8080/api/v1/dags
```

#### Session-based Authentication
```python
import requests

# Login to get session
session = requests.Session()
response = session.post('http://localhost:8080/api/v1/auth/login', {
    'username': 'your_username',
    'password': 'your_password'
})

# Use session for subsequent requests
dags = session.get('http://localhost:8080/api/v1/dags').json()
```

### Authorization Scopes

Different API endpoints require different permission levels:

- **Read**: View DAGs, tasks, and execution status
- **Write**: Create and modify DAGs and tasks
- **Execute**: Run DAGs and control task execution
- **Admin**: System administration and user management

## Error Handling

### HTTP Status Codes

DagLab APIs use standard HTTP status codes:

- `200 OK` - Successful request
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

### Error Response Format

All error responses follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid DAG configuration",
    "details": {
      "field": "schedule_interval",
      "value": "invalid_cron",
      "reason": "Invalid cron expression"
    },
    "request_id": "req_123456789"
  }
}
```

### Python API Exceptions

```python
from daglab.exceptions import (
    DagLabException,
    DAGException,
    TaskException,
    ValidationException,
    ConfigurationException
)

try:
    dag.run()
except TaskException as e:
    print(f"Task failed: {e.message}")
    print(f"Task ID: {e.task_id}")
    print(f"Details: {e.details}")
except DAGException as e:
    print(f"DAG error: {e.message}")
    print(f"DAG ID: {e.dag_id}")
```

## Rate Limiting

API endpoints are subject to rate limiting:

### Rate Limit Headers

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

### Rate Limit Handling

```python
import time
import requests

def api_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:  # Rate limited
            retry_after = int(response.headers.get('Retry-After', 60))
            time.sleep(retry_after)
            continue
            
        return response
    
    raise Exception("Max retries exceeded")
```

## Pagination

Large result sets are paginated:

### Request Parameters
- `page` - Page number (1-based)
- `page_size` - Number of items per page (max 100)
- `sort` - Sort field and direction

### Response Format
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_pages": 5,
    "total_items": 100,
    "has_next": true,
    "has_prev": false
  },
  "links": {
    "first": "/api/v1/dags?page=1",
    "last": "/api/v1/dags?page=5",
    "next": "/api/v1/dags?page=2",
    "prev": null
  }
}
```

### Python Helper
```python
def get_all_pages(url, headers):
    all_items = []
    page = 1
    
    while True:
        response = requests.get(f"{url}?page={page}", headers=headers)
        data = response.json()
        
        all_items.extend(data['data'])
        
        if not data['pagination']['has_next']:
            break
            
        page += 1
    
    return all_items
```

## Webhooks

DagLab can send webhook notifications for various events:

### Webhook Configuration
```yaml
daglab:
  webhooks:
    enabled: true
    endpoints:
      - url: "https://your-app.com/webhooks/daglab"
        secret: "your_webhook_secret"
        events: ["dag.completed", "dag.failed", "task.failed"]
```

### Webhook Payload
```json
{
  "event": "dag.completed",
  "timestamp": "2024-01-01T12:00:00Z",
  "dag_id": "my_dag",
  "run_id": "run_20240101_120000",
  "data": {
    "state": "success",
    "start_date": "2024-01-01T12:00:00Z",
    "end_date": "2024-01-01T12:30:00Z",
    "duration": 1800
  }
}
```

### Webhook Verification
```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)
```

## SDK and Client Libraries

### Official Python SDK
```bash
pip install daglab-sdk
```

```python
from daglab_sdk import DagLabClient

client = DagLabClient(
    base_url="http://localhost:8080",
    api_key="your_api_key"
)

# Get all DAGs
dags = client.dags.list()

# Run a DAG
run = client.dags.run("my_dag", execution_date="2024-01-01")

# Get run status
status = client.runs.get(run.id)
```

### Community Libraries

- **JavaScript/Node.js**: `daglab-js`
- **Go**: `daglab-go`
- **Java**: `daglab-java`
- **C#/.NET**: `daglab-dotnet`

## OpenAPI Specification

DagLab provides an OpenAPI 3.0 specification for the REST API:

### Access the Specification
- **JSON**: `http://localhost:8080/api/v1/openapi.json`
- **YAML**: `http://localhost:8080/api/v1/openapi.yaml`
- **Interactive Docs**: `http://localhost:8080/api/docs`

### Generate Client Code
```bash
# Generate Python client
openapi-generator generate \
  -i http://localhost:8080/api/v1/openapi.json \
  -g python \
  -o daglab-python-client

# Generate JavaScript client
openapi-generator generate \
  -i http://localhost:8080/api/v1/openapi.json \
  -g javascript \
  -o daglab-js-client
```

## Version Compatibility

### API Versioning
DagLab uses semantic versioning for API compatibility:

- **Major version changes**: Breaking changes to API
- **Minor version changes**: New features, backward compatible
- **Patch version changes**: Bug fixes, backward compatible

### Version Headers
```bash
curl -H "Accept: application/vnd.daglab.v1+json" \
  http://localhost:8080/api/dags
```

### Deprecation Policy
- Deprecated endpoints are marked in documentation
- Deprecated features remain available for 2 major versions
- Deprecation warnings are included in API responses

## Performance Considerations

### Best Practices
1. **Use pagination** for large result sets
2. **Cache responses** when appropriate
3. **Use batch operations** for multiple resources
4. **Implement retry logic** with exponential backoff
5. **Monitor rate limits** and adjust request frequency

### Batch Operations
```python
# Batch DAG operations
client.dags.batch_update([
    {"id": "dag1", "schedule": "@daily"},
    {"id": "dag2", "schedule": "@weekly"}
])

# Batch run operations
client.runs.batch_kill(["run1", "run2", "run3"])
```

## Getting Started

1. **Set up authentication** - Obtain API credentials
2. **Explore the API** - Use interactive documentation
3. **Try basic operations** - List DAGs, create runs
4. **Implement error handling** - Handle common error scenarios
5. **Add monitoring** - Track API usage and performance

For detailed endpoint documentation, see the specific API reference sections:
- [REST API Reference](./rest-api.md)
- [Python API Reference](./python-api.md)
- [Task API Reference](./task-api.md)
- [Operator Reference](./operators.md)
# REST API Reference

This document provides comprehensive documentation for DagLab's REST API endpoints. The REST API allows you to programmatically manage DAGs, monitor executions, and administer the DagLab system.

## Base URL and Versioning

**Base URL**: `http://localhost:8080/api/v1`

**Current Version**: v1

**Content Type**: `application/json`

## Authentication

### Bearer Token Authentication
```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8080/api/v1/dags
```

### API Key Authentication
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:8080/api/v1/dags
```

## DAG Management

### List DAGs

Get a list of all available DAGs.

**Endpoint**: `GET /api/v1/dags`

**Parameters**:
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `sort` (optional): Sort field and direction (`id`, `created_at`, `-created_at`)
- `tags` (optional): Filter by tags (comma-separated)
- `owner` (optional): Filter by owner

**Example Request**:
```bash
curl -X GET "http://localhost:8080/api/v1/dags?page=1&page_size=10&tags=etl,daily" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response**:
```json
{
  "data": [
    {
      "id": "customer_data_pipeline",
      "description": "Daily customer data processing pipeline",
      "schedule_interval": "0 2 * * *",
      "is_active": true,
      "is_paused": false,
      "tags": ["etl", "daily", "customer"],
      "owner": "data-team",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "last_run_date": "2024-01-20T02:00:00Z",
      "next_run_date": "2024-01-21T02:00:00Z",
      "task_count": 8,
      "success_rate": 0.95
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_pages": 3,
    "total_items": 25,
    "has_next": true,
    "has_prev": false
  }
}
```

### Get DAG Details

Get detailed information about a specific DAG.

**Endpoint**: `GET /api/v1/dags/{dag_id}`

**Parameters**:
- `dag_id` (required): DAG identifier

**Example Request**:
```bash
curl -X GET "http://localhost:8080/api/v1/dags/customer_data_pipeline" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response**:
```json
{
  "id": "customer_data_pipeline",
  "description": "Daily customer data processing pipeline",
  "schedule_interval": "0 2 * * *",
  "is_active": true,
  "is_paused": false,
  "tags": ["etl", "daily", "customer"],
  "owner": "data-team",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "configuration": {
    "max_active_runs": 1,
    "catchup": false,
    "start_date": "2024-01-01T00:00:00Z",
    "timeout": 7200
  },
  "tasks": [
    {
      "id": "extract_customer_data",
      "type": "database_query",
      "depends_on": [],
      "description": "Extract customer data from production database"
    },
    {
      "id": "validate_data",
      "type": "data_validator",
      "depends_on": ["extract_customer_data"],
      "description": "Validate extracted data quality"
    }
  ],
  "statistics": {
    "total_runs": 50,
    "successful_runs": 47,
    "failed_runs": 3,
    "success_rate": 0.94,
    "average_duration": 1800,
    "last_success": "2024-01-20T02:30:00Z",
    "last_failure": "2024-01-18T02:15:00Z"
  }
}
```

### Create DAG

Create a new DAG from YAML definition.

**Endpoint**: `POST /api/v1/dags`

**Request Body**:
```json
{
  "id": "new_data_pipeline",
  "description": "New data processing pipeline",
  "yaml_content": "dag:\n  id: new_data_pipeline\n  description: \"New pipeline\"\n...",
  "is_active": true
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8080/api/v1/dags" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "new_pipeline",
    "description": "My new pipeline",
    "yaml_content": "...",
    "is_active": true
  }'
```

**Example Response**:
```json
{
  "id": "new_pipeline",
  "description": "My new pipeline",
  "is_active": true,
  "created_at": "2024-01-21T10:00:00Z",
  "message": "DAG created successfully"
}
```

### Update DAG

Update an existing DAG.

**Endpoint**: `PUT /api/v1/dags/{dag_id}`

**Request Body**:
```json
{
  "description": "Updated description",
  "schedule_interval": "0 3 * * *",
  "is_active": true,
  "yaml_content": "..."
}
```

### Delete DAG

Delete a DAG and all its runs.

**Endpoint**: `DELETE /api/v1/dags/{dag_id}`

**Parameters**:
- `force` (optional): Force delete even with active runs

**Example Request**:
```bash
curl -X DELETE "http://localhost:8080/api/v1/dags/old_pipeline?force=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Pause/Unpause DAG

Control DAG execution state.

**Endpoint**: `POST /api/v1/dags/{dag_id}/pause`
**Endpoint**: `POST /api/v1/dags/{dag_id}/unpause`

**Request Body**:
```json
{
  "reason": "Maintenance window"
}
```

## DAG Runs

### List DAG Runs

Get DAG execution history.

**Endpoint**: `GET /api/v1/dags/{dag_id}/runs`

**Parameters**:
- `state` (optional): Filter by state (`running`, `success`, `failed`)
- `start_date` (optional): Filter runs after date (ISO 8601)
- `end_date` (optional): Filter runs before date (ISO 8601)
- `limit` (optional): Number of runs to return

**Example Request**:
```bash
curl -X GET "http://localhost:8080/api/v1/dags/customer_pipeline/runs?state=failed&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response**:
```json
{
  "data": [
    {
      "id": "run_20240120_020000",
      "dag_id": "customer_pipeline",
      "state": "failed",
      "execution_date": "2024-01-20T02:00:00Z",
      "start_date": "2024-01-20T02:00:15Z",
      "end_date": "2024-01-20T02:15:30Z",
      "duration": 915,
      "failed_task_count": 1,
      "success_task_count": 3,
      "total_task_count": 4,
      "error_message": "Database connection timeout"
    }
  ]
}
```

### Get DAG Run Details

Get detailed information about a specific DAG run.

**Endpoint**: `GET /api/v1/dags/{dag_id}/runs/{run_id}`

**Example Response**:
```json
{
  "id": "run_20240120_020000",
  "dag_id": "customer_pipeline",
  "state": "failed",
  "execution_date": "2024-01-20T02:00:00Z",
  "start_date": "2024-01-20T02:00:15Z",
  "end_date": "2024-01-20T02:15:30Z",
  "duration": 915,
  "configuration": {
    "environment": "production",
    "batch_size": 1000
  },
  "tasks": [
    {
      "id": "extract_data",
      "state": "success",
      "start_date": "2024-01-20T02:00:15Z",
      "end_date": "2024-01-20T02:05:00Z",
      "duration": 285,
      "try_number": 1
    },
    {
      "id": "validate_data",
      "state": "failed",
      "start_date": "2024-01-20T02:05:00Z",
      "end_date": "2024-01-20T02:15:30Z",
      "duration": 630,
      "try_number": 3,
      "error_message": "Data validation failed: null values in required fields"
    }
  ]
}
```

### Create DAG Run

Trigger a new DAG execution.

**Endpoint**: `POST /api/v1/dags/{dag_id}/runs`

**Request Body**:
```json
{
  "execution_date": "2024-01-21T00:00:00Z",
  "configuration": {
    "environment": "production",
    "batch_size": 1000,
    "debug_mode": false
  },
  "note": "Manual execution for data backfill"
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8080/api/v1/dags/customer_pipeline/runs" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "execution_date": "2024-01-21T00:00:00Z",
    "configuration": {
      "batch_size": 500
    }
  }'
```

**Example Response**:
```json
{
  "id": "run_20240121_000000",
  "dag_id": "customer_pipeline",
  "state": "running",
  "execution_date": "2024-01-21T00:00:00Z",
  "created_at": "2024-01-21T10:00:00Z",
  "message": "DAG run created successfully"
}
```

### Kill DAG Run

Stop a running DAG execution.

**Endpoint**: `DELETE /api/v1/dags/{dag_id}/runs/{run_id}`

**Request Body**:
```json
{
  "reason": "Cancelled due to resource constraints"
}
```

## Task Management

### List Tasks

Get tasks for a specific DAG.

**Endpoint**: `GET /api/v1/dags/{dag_id}/tasks`

**Example Response**:
```json
{
  "data": [
    {
      "id": "extract_customer_data",
      "type": "database_query",
      "description": "Extract customer data from production database",
      "depends_on": [],
      "owner": "data-engineering",
      "retries": 3,
      "retry_delay": 300,
      "timeout": 1800,
      "pool": "database_pool"
    }
  ]
}
```

### Get Task Details

Get detailed information about a specific task.

**Endpoint**: `GET /api/v1/dags/{dag_id}/tasks/{task_id}`

### Get Task Instances

Get execution history for a specific task.

**Endpoint**: `GET /api/v1/dags/{dag_id}/tasks/{task_id}/instances`

**Parameters**:
- `state` (optional): Filter by state
- `start_date` (optional): Filter instances after date
- `end_date` (optional): Filter instances before date

**Example Response**:
```json
{
  "data": [
    {
      "id": "extract_customer_data_20240120_020000",
      "task_id": "extract_customer_data",
      "dag_id": "customer_pipeline",
      "run_id": "run_20240120_020000",
      "state": "success",
      "start_date": "2024-01-20T02:00:15Z",
      "end_date": "2024-01-20T02:05:00Z",
      "duration": 285,
      "try_number": 1,
      "max_tries": 3,
      "hostname": "worker-node-1",
      "pid": 12345
    }
  ]
}
```

### Get Task Logs

Retrieve logs for a specific task instance.

**Endpoint**: `GET /api/v1/dags/{dag_id}/tasks/{task_id}/instances/{instance_id}/logs`

**Parameters**:
- `full_content` (optional): Return full log content
- `download` (optional): Download as file

**Example Response**:
```json
{
  "logs": [
    {
      "timestamp": "2024-01-20T02:00:15Z",
      "level": "INFO",
      "message": "Starting task execution"
    },
    {
      "timestamp": "2024-01-20T02:00:16Z",
      "level": "INFO",
      "message": "Connecting to database"
    },
    {
      "timestamp": "2024-01-20T02:05:00Z",
      "level": "INFO",
      "message": "Task completed successfully"
    }
  ],
  "metadata": {
    "log_file": "/var/log/daglab/customer_pipeline/extract_customer_data/20240120_020000.log",
    "size": 15420,
    "line_count": 156
  }
}
```

### Retry Task Instance

Retry a failed task instance.

**Endpoint**: `POST /api/v1/dags/{dag_id}/tasks/{task_id}/instances/{instance_id}/retry`

### Kill Task Instance

Kill a running task instance.

**Endpoint**: `DELETE /api/v1/dags/{dag_id}/tasks/{task_id}/instances/{instance_id}`

## System Administration

### System Status

Get overall system health and status.

**Endpoint**: `GET /api/v1/system/status`

**Example Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-21T10:00:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "response_time": 15,
      "details": "PostgreSQL 13.5 - Connection pool: 45/50"
    },
    "executor": {
      "status": "healthy",
      "active_workers": 8,
      "queued_tasks": 12,
      "details": "Celery executor with Redis broker"
    },
    "storage": {
      "status": "healthy",
      "free_space": "850GB",
      "usage": "15%",
      "details": "Local filesystem storage"
    }
  },
  "metrics": {
    "active_dags": 25,
    "running_tasks": 8,
    "queued_tasks": 12,
    "total_runs_today": 150,
    "success_rate_24h": 0.96
  }
}
```

### System Configuration

Get current system configuration.

**Endpoint**: `GET /api/v1/system/config`

**Example Response**:
```json
{
  "executor": {
    "type": "celery",
    "max_parallel_tasks": 20,
    "default_queue": "default"
  },
  "database": {
    "type": "postgresql",
    "pool_size": 50,
    "max_overflow": 30
  },
  "security": {
    "auth_enabled": true,
    "session_timeout": 3600
  },
  "logging": {
    "level": "INFO",
    "retention_days": 30
  }
}
```

### System Metrics

Get system performance metrics.

**Endpoint**: `GET /api/v1/system/metrics`

**Parameters**:
- `start_time` (optional): Start time for metrics (ISO 8601)
- `end_time` (optional): End time for metrics (ISO 8601)
- `granularity` (optional): Time granularity (`5m`, `1h`, `1d`)

**Example Response**:
```json
{
  "timeframe": {
    "start": "2024-01-21T00:00:00Z",
    "end": "2024-01-21T10:00:00Z",
    "granularity": "1h"
  },
  "metrics": [
    {
      "timestamp": "2024-01-21T09:00:00Z",
      "dag_runs_started": 12,
      "dag_runs_completed": 10,
      "dag_runs_failed": 1,
      "tasks_executed": 45,
      "average_task_duration": 180,
      "cpu_usage": 0.65,
      "memory_usage": 0.72,
      "disk_usage": 0.15
    }
  ]
}
```

## User Management

### List Users

Get list of system users.

**Endpoint**: `GET /api/v1/users`

**Example Response**:
```json
{
  "data": [
    {
      "id": "user123",
      "username": "john.doe",
      "email": "john.doe@company.com",
      "full_name": "John Doe",
      "role": "dag_author",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z",
      "last_login": "2024-01-21T09:30:00Z"
    }
  ]
}
```

### Create User

Create a new user account.

**Endpoint**: `POST /api/v1/users`

**Request Body**:
```json
{
  "username": "jane.smith",
  "email": "jane.smith@company.com",
  "full_name": "Jane Smith",
  "password": "secure_password",
  "role": "dag_viewer"
}
```

### Update User

Update user information.

**Endpoint**: `PUT /api/v1/users/{user_id}`

### Delete User

Delete a user account.

**Endpoint**: `DELETE /api/v1/users/{user_id}`

## Authentication Endpoints

### Login

Authenticate and obtain access token.

**Endpoint**: `POST /api/v1/auth/login`

**Request Body**:
```json
{
  "username": "john.doe",
  "password": "user_password"
}
```

**Example Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "def50200d8e4f...",
  "user": {
    "id": "user123",
    "username": "john.doe",
    "email": "john.doe@company.com",
    "role": "dag_author"
  }
}
```

### Refresh Token

Refresh an expired access token.

**Endpoint**: `POST /api/v1/auth/refresh`

**Request Body**:
```json
{
  "refresh_token": "def50200d8e4f..."
}
```

### Logout

Invalidate current session/token.

**Endpoint**: `POST /api/v1/auth/logout`

### Password Reset

Request password reset.

**Endpoint**: `POST /api/v1/auth/password-reset`

**Request Body**:
```json
{
  "email": "john.doe@company.com"
}
```

## Data Management

### Export Data

Export DAG definitions and execution data.

**Endpoint**: `GET /api/v1/export`

**Parameters**:
- `type` (required): Export type (`dags`, `runs`, `logs`, `all`)
- `dag_ids` (optional): Specific DAGs to export (comma-separated)
- `start_date` (optional): Start date for runs/logs export
- `end_date` (optional): End date for runs/logs export
- `format` (optional): Export format (`json`, `yaml`, `csv`)

**Example Request**:
```bash
curl -X GET "http://localhost:8080/api/v1/export?type=dags&format=yaml" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o dags_export.yaml
```

### Import Data

Import DAG definitions.

**Endpoint**: `POST /api/v1/import`

**Request Body**: Multipart form data with file upload

**Example Request**:
```bash
curl -X POST "http://localhost:8080/api/v1/import" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@dags_export.yaml" \
  -F "type=dags" \
  -F "overwrite=true"
```

### Backup System

Create system backup.

**Endpoint**: `POST /api/v1/backup`

**Request Body**:
```json
{
  "name": "backup_20240121",
  "description": "Weekly system backup",
  "include": ["dags", "runs", "users", "config"],
  "compress": true
}
```

### Restore System

Restore from backup.

**Endpoint**: `POST /api/v1/restore`

**Request Body**:
```json
{
  "backup_id": "backup_20240121",
  "restore_options": {
    "overwrite_existing": false,
    "restore_runs": true,
    "restore_users": false
  }
}
```

## Webhooks

### List Webhook Configurations

Get configured webhooks.

**Endpoint**: `GET /api/v1/webhooks`

### Create Webhook

Configure a new webhook endpoint.

**Endpoint**: `POST /api/v1/webhooks`

**Request Body**:
```json
{
  "name": "slack_notifications",
  "url": "https://hooks.slack.com/services/...",
  "events": ["dag.failed", "task.failed"],
  "secret": "webhook_secret",
  "enabled": true,
  "headers": {
    "Content-Type": "application/json"
  }
}
```

### Update Webhook

Update webhook configuration.

**Endpoint**: `PUT /api/v1/webhooks/{webhook_id}`

### Delete Webhook

Delete webhook configuration.

**Endpoint**: `DELETE /api/v1/webhooks/{webhook_id}`

### Test Webhook

Send test event to webhook.

**Endpoint**: `POST /api/v1/webhooks/{webhook_id}/test`

## Error Responses

### Standard Error Format

All API errors follow this format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "DAG 'unknown_dag' not found",
    "details": {
      "resource_type": "dag",
      "resource_id": "unknown_dag"
    },
    "request_id": "req_1234567890",
    "timestamp": "2024-01-21T10:00:00Z"
  }
}
```

### Common Error Codes

- `AUTHENTICATION_REQUIRED` - Authentication credentials missing
- `AUTHORIZATION_FAILED` - Insufficient permissions
- `VALIDATION_ERROR` - Request validation failed
- `RESOURCE_NOT_FOUND` - Requested resource not found
- `RESOURCE_CONFLICT` - Resource already exists or in conflicting state
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INTERNAL_SERVER_ERROR` - Internal server error

### Rate Limiting

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1640995200
```

When rate limit is exceeded, you'll receive a `429` status code:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again later.",
    "details": {
      "limit": 1000,
      "window": "1h",
      "retry_after": 300
    }
  }
}
```

## SDK Examples

### Python SDK Usage

```python
from daglab_sdk import DagLabClient

# Initialize client
client = DagLabClient(
    base_url="http://localhost:8080",
    api_key="your_api_key"
)

# List DAGs
dags = client.dags.list(tags=["etl", "daily"])

# Get DAG details
dag = client.dags.get("customer_pipeline")

# Create DAG run
run = client.dags.run(
    "customer_pipeline",
    execution_date="2024-01-21T00:00:00Z",
    configuration={"batch_size": 1000}
)

# Monitor run status
while run.state in ["running", "queued"]:
    time.sleep(30)
    run = client.runs.get(run.id)

print(f"Run completed with state: {run.state}")
```

### JavaScript SDK Usage

```javascript
const { DagLabClient } = require('daglab-js');

const client = new DagLabClient({
  baseUrl: 'http://localhost:8080',
  apiKey: 'your_api_key'
});

// List DAGs
const dags = await client.dags.list({ tags: ['etl', 'daily'] });

// Create and monitor run
const run = await client.dags.run('customer_pipeline', {
  execution_date: '2024-01-21T00:00:00Z',
  configuration: { batch_size: 1000 }
});

console.log(`Created run: ${run.id}`);
```

This REST API reference provides comprehensive documentation for integrating with DagLab programmatically. For more advanced usage patterns and examples, see the [Python API Reference](./python-api.md) and [SDK Documentation](../examples/sdk-examples.md).
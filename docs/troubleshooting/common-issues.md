# Common Issues and Troubleshooting

This guide helps you diagnose and resolve common issues encountered when using DagLab. Issues are organized by category with symptoms, causes, and solutions.

## Table of Contents

1. [Installation and Setup Issues](#installation-and-setup-issues)
2. [Configuration Problems](#configuration-problems)
3. [DAG Definition Issues](#dag-definition-issues)
4. [Task Execution Problems](#task-execution-problems)
5. [Database Connection Issues](#database-connection-issues)
6. [Performance Issues](#performance-issues)
7. [Authentication and Authorization](#authentication-and-authorization)
8. [Networking and Connectivity](#networking-and-connectivity)
9. [Storage and File System Issues](#storage-and-file-system-issues)
10. [Deployment and Infrastructure](#deployment-and-infrastructure)

## Installation and Setup Issues

### Issue: DagLab Installation Fails with Permission Errors

**Symptoms:**
```bash
$ pip install daglab
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**Causes:**
- Installing system-wide without proper permissions
- Conflicting Python installations
- Virtual environment not activated

**Solutions:**

1. **Use Virtual Environment (Recommended):**
```bash
python -m venv daglab-env
source daglab-env/bin/activate  # On Windows: daglab-env\Scripts\activate
pip install daglab
```

2. **User Installation:**
```bash
pip install --user daglab
```

3. **Fix Path Issues:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH=$HOME/.local/bin:$PATH
```

### Issue: Command 'daglab' Not Found After Installation

**Symptoms:**
```bash
$ daglab --version
bash: daglab: command not found
```

**Causes:**
- DagLab not in PATH
- Installation in wrong Python environment
- Incomplete installation

**Solutions:**

1. **Check Installation:**
```bash
pip show daglab
which python
which pip
```

2. **Reinstall in Correct Environment:**
```bash
pip uninstall daglab
pip install daglab
```

3. **Add to PATH:**
```bash
export PATH=$PATH:$(python -m site --user-base)/bin
```

### Issue: Python Version Compatibility Errors

**Symptoms:**
```bash
ERROR: Package 'daglab' requires a different Python: 3.7.0 not in '>=3.8'
```

**Causes:**
- Python version too old
- Using wrong Python interpreter

**Solutions:**

1. **Check Python Version:**
```bash
python --version
python3 --version
```

2. **Install Python 3.8+:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.9

# macOS with Homebrew
brew install python@3.9

# Windows
# Download from python.org
```

3. **Use Specific Python Version:**
```bash
python3.9 -m pip install daglab
```

## Configuration Problems

### Issue: Configuration File Not Found

**Symptoms:**
```bash
$ daglab run my_dag.yaml
Error: Configuration file not found: config/daglab.yaml
```

**Causes:**
- Missing configuration file
- Incorrect file path
- Wrong working directory

**Solutions:**

1. **Create Default Configuration:**
```bash
daglab init-config
```

2. **Specify Configuration Path:**
```bash
daglab --config /path/to/config.yaml run my_dag.yaml
```

3. **Set Environment Variable:**
```bash
export DAGLAB_CONFIG_PATH=/path/to/config.yaml
```

### Issue: Database Connection Configuration Errors

**Symptoms:**
```bash
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server
```

**Causes:**
- Incorrect database URL
- Database server not running
- Network connectivity issues
- Missing database credentials

**Solutions:**

1. **Verify Database URL Format:**
```yaml
# config/daglab.yaml
daglab:
  database:
    url: "postgresql://username:password@hostname:port/database"
```

2. **Test Database Connection:**
```bash
psql -h hostname -p port -U username -d database
```

3. **Check Database Status:**
```bash
# PostgreSQL
sudo systemctl status postgresql
pg_isready -h hostname -p port

# MySQL
sudo systemctl status mysql
mysqladmin -h hostname -P port -u username -p ping
```

### Issue: Invalid YAML Configuration

**Symptoms:**
```bash
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Causes:**
- YAML syntax errors
- Incorrect indentation
- Special characters not escaped

**Solutions:**

1. **Validate YAML Syntax:**
```bash
python -c "import yaml; yaml.safe_load(open('config/daglab.yaml'))"
```

2. **Use Online YAML Validator:**
   - Visit: https://yaml-online-parser.appspot.com/

3. **Common YAML Fixes:**
```yaml
# Correct indentation (use spaces, not tabs)
daglab:
  database:
    url: "postgresql://user:pass@host/db"
    
# Quote special characters
password: "my@password!with#symbols"

# Proper list syntax
tags: 
  - etl
  - daily
```

## DAG Definition Issues

### Issue: DAG Validation Fails

**Symptoms:**
```bash
$ daglab validate my_dag.yaml
ValidationError: Task 'process_data' depends on non-existent task 'extract_dat'
```

**Causes:**
- Typos in task IDs
- Missing task definitions
- Circular dependencies
- Invalid task configuration

**Solutions:**

1. **Check Task Dependencies:**
```yaml
# Ensure all referenced tasks exist
tasks:
  - id: extract_data  # Note: correct spelling
    type: database_query
    
  - id: process_data
    type: python_script
    depends_on: [extract_data]  # Must match exactly
```

2. **Use Dependency Validation:**
```bash
daglab validate my_dag.yaml --check-dependencies
```

3. **Visualize DAG Structure:**
```bash
daglab visualize my_dag.yaml --dependencies
```

### Issue: Circular Dependency Detected

**Symptoms:**
```bash
ValidationError: Circular dependency detected: task_a -> task_b -> task_a
```

**Causes:**
- Tasks depending on each other in a cycle
- Complex dependency chains forming loops

**Solutions:**

1. **Identify the Cycle:**
```bash
daglab debug my_dag.yaml --check-cycles
```

2. **Fix Dependency Chain:**
```yaml
# Before (circular)
tasks:
  - id: task_a
    depends_on: [task_b]
  - id: task_b
    depends_on: [task_a]

# After (fixed)
tasks:
  - id: task_a
    depends_on: []
  - id: task_b
    depends_on: [task_a]
```

### Issue: Task Configuration Validation Errors

**Symptoms:**
```bash
ValidationError: Required field 'query' missing for database_query task
```

**Causes:**
- Missing required configuration parameters
- Invalid parameter values
- Wrong task type for operation

**Solutions:**

1. **Check Task Type Documentation:**
```bash
daglab help task-types database_query
```

2. **Validate Task Configuration:**
```yaml
# Complete task configuration
- id: extract_customers
  type: database_query
  config:
    connection: "customer_db"
    query: "SELECT * FROM customers"
    output_format: "csv"
```

3. **Use Schema Validation:**
```bash
daglab validate my_dag.yaml --strict
```

## Task Execution Problems

### Issue: Task Fails with Import Errors

**Symptoms:**
```bash
ModuleNotFoundError: No module named 'pandas'
```

**Causes:**
- Missing Python dependencies
- Virtual environment not activated
- Package not installed in correct environment

**Solutions:**

1. **Install Missing Dependencies:**
```bash
pip install pandas numpy requests
```

2. **Use Requirements File:**
```yaml
# In DAG configuration
tasks:
  - id: data_processing
    type: python_script
    config:
      requirements:
        - pandas>=1.3.0
        - numpy>=1.20.0
      script: "process_data.py"
```

3. **Check Python Environment:**
```bash
which python
pip list | grep pandas
```

### Issue: Task Timeout Errors

**Symptoms:**
```bash
TaskTimeoutError: Task 'long_running_task' exceeded timeout of 3600 seconds
```

**Causes:**
- Task taking longer than configured timeout
- Infinite loops or hanging operations
- Resource constraints

**Solutions:**

1. **Increase Task Timeout:**
```yaml
tasks:
  - id: long_running_task
    type: python_script
    timeout: 7200  # 2 hours
    config:
      script: "long_process.py"
```

2. **Optimize Task Performance:**
```python
# Use chunking for large datasets
def process_large_dataset(file_path):
    chunk_size = 10000
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        process_chunk(chunk)
```

3. **Monitor Task Progress:**
```bash
daglab logs long_running_task --follow
```

### Issue: Memory Errors During Task Execution

**Symptoms:**
```bash
MemoryError: Unable to allocate 8.00 GiB for an array
```

**Causes:**
- Processing datasets larger than available memory
- Memory leaks in task code
- Insufficient system resources

**Solutions:**

1. **Increase Memory Limits:**
```yaml
tasks:
  - id: memory_intensive_task
    type: python_script
    resources:
      memory: "8GB"
    config:
      script: "process_large_data.py"
```

2. **Use Chunking Strategy:**
```python
# Process data in chunks
def process_data_chunks(file_path):
    chunk_size = 1000
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        result = process_chunk(chunk)
        save_chunk_result(result)
```

3. **Monitor Memory Usage:**
```bash
# During execution
htop
free -h
```

### Issue: Task Retry Failures

**Symptoms:**
```bash
TaskRetryError: Task failed after 3 retry attempts
```

**Causes:**
- Persistent errors in task logic
- External service unavailability
- Configuration issues

**Solutions:**

1. **Configure Retry Policy:**
```yaml
tasks:
  - id: unreliable_task
    type: api_request
    retry_policy:
      max_retries: 5
      retry_delay: 300
      exponential_backoff: true
      retry_on_status: [500, 502, 503, 504]
    config:
      url: "https://api.example.com/data"
```

2. **Implement Circuit Breaker:**
```python
def robust_api_call():
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if should_retry(e):
            raise RetryableException(str(e))
        else:
            raise PermanentException(str(e))
```

3. **Add Health Checks:**
```yaml
tasks:
  - id: health_check
    type: health_check
    config:
      url: "https://api.example.com/health"
      
  - id: api_call
    type: api_request
    depends_on: [health_check]
    condition: "{{ task_instance.xcom_pull('health_check')['healthy'] }}"
```

## Database Connection Issues

### Issue: Connection Pool Exhaustion

**Symptoms:**
```bash
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**Causes:**
- Too many concurrent database connections
- Connections not being released properly
- Pool size too small for workload

**Solutions:**

1. **Increase Pool Size:**
```yaml
daglab:
  database:
    url: "postgresql://user:pass@host/db"
    pool_size: 20
    max_overflow: 30
    pool_timeout: 30
```

2. **Fix Connection Leaks:**
```python
# Use context managers
def database_operation():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM table")
        return cursor.fetchall()
    # Connection automatically closed
```

3. **Monitor Connection Usage:**
```sql
-- PostgreSQL
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';

-- Check connection pool status
SELECT * FROM pg_stat_activity WHERE datname = 'daglab';
```

### Issue: Database Lock Timeouts

**Symptoms:**
```bash
psycopg2.OperationalError: canceling statement due to lock timeout
```

**Causes:**
- Long-running transactions
- Concurrent access to same resources
- Deadlocks between transactions

**Solutions:**

1. **Increase Lock Timeout:**
```sql
-- PostgreSQL
SET lock_timeout = '30s';
SET statement_timeout = '60s';
```

2. **Optimize Queries:**
```sql
-- Use proper indexes
CREATE INDEX CONCURRENTLY idx_table_column ON table_name(column_name);

-- Break large transactions into smaller ones
BEGIN;
UPDATE table SET column = value WHERE id BETWEEN 1 AND 1000;
COMMIT;
```

3. **Monitor Locks:**
```sql
-- PostgreSQL
SELECT 
  bl.pid AS blocked_pid,
  bd.query AS blocked_query,
  kl.pid AS blocking_pid,
  kd.query AS blocking_query
FROM pg_stat_activity bl
JOIN pg_locks blocked ON bl.pid = blocked.pid
JOIN pg_locks blocking ON blocked.locktype = blocking.locktype
JOIN pg_stat_activity kl ON blocking.pid = kl.pid
WHERE NOT blocked.granted;
```

## Performance Issues

### Issue: Slow DAG Execution

**Symptoms:**
- DAGs taking much longer than expected
- High CPU or memory usage
- Tasks queuing for long periods

**Causes:**
- Inefficient task execution
- Resource contention
- Poor dependency design
- Database performance issues

**Solutions:**

1. **Profile DAG Performance:**
```bash
daglab profile my_dag --detailed
daglab metrics my_dag --performance
```

2. **Optimize Task Dependencies:**
```yaml
# Enable parallel execution
dag:
  id: optimized_pipeline
  max_active_tasks: 10
  
tasks:
  # Independent tasks can run in parallel
  - id: extract_sales
    type: database_query
    
  - id: extract_customers
    type: database_query
    
  - id: extract_products
    type: database_query
    
  # Only this task needs to wait
  - id: merge_data
    type: data_merger
    depends_on: [extract_sales, extract_customers, extract_products]
```

3. **Use Resource Pools:**
```yaml
daglab:
  resource_pools:
    - name: cpu_intensive
      cpu: 4
      memory: "8GB"
      max_concurrent: 2
      
    - name: io_intensive
      cpu: 1
      memory: "2GB"
      max_concurrent: 8

tasks:
  - id: cpu_heavy_task
    resource_pool: cpu_intensive
    
  - id: file_processing
    resource_pool: io_intensive
```

### Issue: High Memory Usage

**Symptoms:**
- System running out of memory
- Tasks being killed by OOM killer
- Swap usage increasing

**Causes:**
- Memory leaks in task code
- Processing large datasets in memory
- Too many concurrent tasks

**Solutions:**

1. **Implement Memory Monitoring:**
```python
import psutil
import gc

def monitor_memory():
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"Memory usage: {memory_mb:.2f} MB")
    
    if memory_mb > 1000:  # 1GB threshold
        gc.collect()  # Force garbage collection
```

2. **Use Data Streaming:**
```python
# Instead of loading entire file
def process_large_file_bad(file_path):
    df = pd.read_csv(file_path)  # Loads entire file
    return df.groupby('category').sum()

# Use chunking
def process_large_file_good(file_path):
    chunk_size = 10000
    result = {}
    
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        chunk_result = chunk.groupby('category').sum()
        # Merge chunk results
        for key, value in chunk_result.items():
            result[key] = result.get(key, 0) + value
    
    return result
```

3. **Configure Memory Limits:**
```yaml
tasks:
  - id: memory_limited_task
    type: python_script
    resources:
      memory: "2GB"
    config:
      script: "process_data.py"
```

## Authentication and Authorization

### Issue: Authentication Failures

**Symptoms:**
```bash
HTTP 401 Unauthorized: Invalid credentials
```

**Causes:**
- Incorrect username/password
- Expired tokens
- Missing authentication configuration

**Solutions:**

1. **Verify Credentials:**
```bash
# Test login
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

2. **Check Token Expiration:**
```python
import jwt
from datetime import datetime

token = "your_jwt_token"
decoded = jwt.decode(token, options={"verify_signature": False})
exp_timestamp = decoded.get('exp')

if exp_timestamp:
    exp_date = datetime.fromtimestamp(exp_timestamp)
    print(f"Token expires: {exp_date}")
```

3. **Configure Authentication:**
```yaml
daglab:
  security:
    enable_auth: true
    auth_backend: "database"  # or ldap, oauth
    secret_key: "your-secret-key"
    jwt_expiration: 3600
```

### Issue: Permission Denied Errors

**Symptoms:**
```bash
HTTP 403 Forbidden: Insufficient permissions
```

**Causes:**
- User lacks required permissions
- RBAC configuration issues
- Resource access restrictions

**Solutions:**

1. **Check User Permissions:**
```bash
daglab user show john.doe
daglab permissions list --user john.doe
```

2. **Configure RBAC:**
```yaml
daglab:
  security:
    rbac:
      enabled: true
      roles:
        data_analyst:
          permissions: 
            - "dag:view"
            - "dag:run"
            - "task:view"
        data_engineer:
          permissions:
            - "dag:*"
            - "task:*"
            - "user:view"
```

3. **Grant Permissions:**
```bash
daglab user add-role john.doe data_engineer
daglab permissions grant john.doe "dag:create"
```

## Networking and Connectivity

### Issue: Service Unreachable

**Symptoms:**
```bash
curl: (7) Failed to connect to localhost port 8080: Connection refused
```

**Causes:**
- Service not running
- Firewall blocking connections
- Wrong port configuration
- Network routing issues

**Solutions:**

1. **Check Service Status:**
```bash
# Check if service is running
netstat -tuln | grep 8080
ss -tuln | grep 8080

# Check process
ps aux | grep daglab
```

2. **Verify Configuration:**
```yaml
daglab:
  web:
    host: "0.0.0.0"  # Listen on all interfaces
    port: 8080
```

3. **Check Firewall:**
```bash
# Ubuntu/Debian
sudo ufw status
sudo ufw allow 8080

# CentOS/RHEL
sudo firewall-cmd --list-ports
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

### Issue: DNS Resolution Problems

**Symptoms:**
```bash
getaddrinfo failed: Name or service not known
```

**Causes:**
- DNS server issues
- Incorrect hostname configuration
- Network connectivity problems

**Solutions:**

1. **Test DNS Resolution:**
```bash
nslookup daglab.example.com
dig daglab.example.com
```

2. **Use IP Addresses:**
```yaml
# Temporary workaround
daglab:
  database:
    url: "postgresql://user:pass@192.168.1.100:5432/daglab"
```

3. **Configure DNS:**
```bash
# Add to /etc/hosts
echo "192.168.1.100 daglab.example.com" | sudo tee -a /etc/hosts
```

## Storage and File System Issues

### Issue: Disk Space Errors

**Symptoms:**
```bash
OSError: [Errno 28] No space left on device
```

**Causes:**
- Disk full
- Large log files
- Temporary files not cleaned up

**Solutions:**

1. **Check Disk Usage:**
```bash
df -h
du -sh /var/log/daglab/
du -sh /tmp/daglab/
```

2. **Clean Up Files:**
```bash
# Rotate logs
daglab logs rotate --keep-days 7

# Clean temporary files
find /tmp/daglab -type f -mtime +1 -delete

# Clean old DAG runs
daglab runs clean --older-than 30d
```

3. **Configure Log Rotation:**
```yaml
daglab:
  logging:
    file:
      enabled: true
      path: "/var/log/daglab/daglab.log"
      max_size: "100MB"
      backup_count: 5
      rotation: "size"
```

### Issue: Permission Denied on File Operations

**Symptoms:**
```bash
PermissionError: [Errno 13] Permission denied: '/data/output.csv'
```

**Causes:**
- Incorrect file permissions
- Running as wrong user
- SELinux/AppArmor restrictions

**Solutions:**

1. **Check File Permissions:**
```bash
ls -la /data/
stat /data/output.csv
```

2. **Fix Permissions:**
```bash
# Change ownership
sudo chown daglab:daglab /data/output.csv

# Change permissions
chmod 644 /data/output.csv

# Recursive for directories
chmod -R 755 /data/daglab/
```

3. **Run as Correct User:**
```yaml
# Docker/Kubernetes
securityContext:
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
```

## Deployment and Infrastructure

### Issue: Container Startup Failures

**Symptoms:**
```bash
docker: Error response from daemon: Container exited with a non-zero code
```

**Causes:**
- Incorrect container configuration
- Missing environment variables
- Health check failures

**Solutions:**

1. **Check Container Logs:**
```bash
docker logs daglab-web
kubectl logs deployment/daglab-web -n daglab
```

2. **Verify Environment Variables:**
```bash
docker exec daglab-web env | grep DAGLAB
```

3. **Test Health Checks:**
```bash
# Inside container
curl http://localhost:8080/health

# From outside
docker exec daglab-web curl http://localhost:8080/health
```

### Issue: Kubernetes Pod CrashLoopBackOff

**Symptoms:**
```bash
NAME                         READY   STATUS             RESTARTS   AGE
daglab-web-7d4b8c8f9-xyz12   0/1     CrashLoopBackOff   5          5m
```

**Causes:**
- Application crashes on startup
- Failed health checks
- Resource constraints

**Solutions:**

1. **Check Pod Events:**
```bash
kubectl describe pod daglab-web-7d4b8c8f9-xyz12 -n daglab
kubectl get events -n daglab --sort-by=.metadata.creationTimestamp
```

2. **View Pod Logs:**
```bash
kubectl logs daglab-web-7d4b8c8f9-xyz12 -n daglab --previous
```

3. **Adjust Resource Limits:**
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

## Diagnostic Commands

### General Health Check

```bash
#!/bin/bash
# daglab-health-check.sh

echo "=== DagLab Health Check ==="

# Check service status
echo "1. Service Status:"
systemctl status daglab-web 2>/dev/null || echo "Service not running"

# Check network connectivity
echo "2. Network Connectivity:"
curl -s http://localhost:8080/health && echo "OK" || echo "FAILED"

# Check database connectivity
echo "3. Database Connectivity:"
daglab db status

# Check disk space
echo "4. Disk Space:"
df -h | grep -E "(Filesystem|/dev/)"

# Check memory usage
echo "5. Memory Usage:"
free -h

# Check recent logs
echo "6. Recent Errors:"
daglab logs --level ERROR --lines 5
```

### Performance Diagnostics

```bash
#!/bin/bash
# performance-check.sh

echo "=== Performance Diagnostics ==="

# System resources
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}'

echo "Memory Usage:"
free | grep Mem | awk '{printf "%.2f%%\n", $3/$2 * 100.0}'

# Database performance
echo "Database Connections:"
psql -h localhost -U daglab -d daglab -c "SELECT count(*) FROM pg_stat_activity;"

# Active DAGs and tasks
echo "Active DAGs:"
daglab list dags --state running | wc -l

echo "Running Tasks:"
daglab list tasks --state running | wc -l
```

## Getting Additional Help

### Log Analysis

```bash
# Enable debug logging
export DAGLAB_LOG_LEVEL=DEBUG

# Comprehensive log collection
daglab logs --all-components --since "1h ago" > daglab-debug.log

# Analyze patterns
grep -i error daglab-debug.log
grep -i warning daglab-debug.log
```

### Support Information Collection

```bash
#!/bin/bash
# collect-support-info.sh

echo "=== DagLab Support Information ==="
echo "Date: $(date)"
echo "Version: $(daglab --version)"
echo "Python: $(python --version)"
echo "OS: $(uname -a)"

echo -e "\n=== Configuration ==="
daglab config show --resolved

echo -e "\n=== System Status ==="
daglab health check

echo -e "\n=== Recent Logs ==="
daglab logs --level ERROR --lines 20
```

### Community Support

- **GitHub Issues**: Report bugs and get help
- **Discord/Slack**: Real-time community support
- **Documentation**: Comprehensive guides and tutorials
- **Stack Overflow**: Tag questions with `daglab`

Remember to include relevant logs, configuration files (with secrets removed), and error messages when seeking help from the community.
# Getting Started with DagLab

This guide will help you get up and running with DagLab quickly. You'll learn the basics of creating, configuring, and running your first workflow.

## Prerequisites

Before getting started, ensure you have:

- **Python 3.8+** installed on your system
- **pip** package manager
- Basic familiarity with YAML configuration files
- (Optional) Docker for containerized deployments

## Installation

### Method 1: pip Install (Recommended)

```bash
# Install DagLab from PyPI
pip install daglab

# Verify installation
daglab --version
```

### Method 2: Development Install

```bash
# Clone the repository
git clone https://github.com/openconjecture/daglab.git
cd daglab

# Install in development mode
pip install -e .
```

### Method 3: Docker

```bash
# Pull the official DagLab image
docker pull daglab/daglab:latest

# Run DagLab in a container
docker run -it daglab/daglab:latest daglab --help
```

## Your First Workflow

Let's create a simple data processing workflow to understand DagLab basics.

### Step 1: Initialize a Project

```bash
# Create a new DagLab project
daglab init my-first-workflow
cd my-first-workflow
```

This creates a project structure:
```
my-first-workflow/
├── dags/
│   └── example_dag.yaml
├── config/
│   └── daglab.yaml
├── data/
├── logs/
└── plugins/
```

### Step 2: Understanding DAG Structure

Open `dags/example_dag.yaml` to see a basic DAG structure:

```yaml
# dags/simple_data_pipeline.yaml
dag:
  id: simple_data_pipeline
  description: "A simple data processing pipeline"
  schedule: "0 8 * * *"  # Daily at 8 AM
  tags: [data, etl, example]

tasks:
  - id: extract_data
    type: http_request
    config:
      url: "https://api.example.com/data"
      method: GET
      headers:
        Authorization: "Bearer ${API_TOKEN}"
    
  - id: transform_data
    type: python_script
    depends_on: [extract_data]
    config:
      script: |
        import json
        
        def transform(data):
            # Simple data transformation
            processed = []
            for item in data:
                processed.append({
                    'id': item['id'],
                    'name': item['name'].upper(),
                    'timestamp': item['created_at']
                })
            return processed
        
        # Process the data from previous task
        result = transform(task_input['extract_data']['data'])
        return result
    
  - id: load_data
    type: database_insert
    depends_on: [transform_data]
    config:
      connection: "postgresql://user:pass@localhost/db"
      table: "processed_data"
      data_source: "transform_data"
```

### Step 3: Configure DagLab

Edit `config/daglab.yaml` for your environment:

```yaml
# config/daglab.yaml
daglab:
  # Execution settings
  executor: local  # Options: local, celery, kubernetes
  max_parallel_tasks: 4
  
  # Storage configuration
  storage:
    type: local
    path: ./data
    
  # Database settings (for metadata)
  database:
    url: "sqlite:///daglab.db"
    
  # Logging configuration
  logging:
    level: INFO
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
  # Security settings
  security:
    enable_auth: false
    secret_key: "your-secret-key-here"
```

### Step 4: Set Environment Variables

Create a `.env` file for sensitive configuration:

```bash
# .env
API_TOKEN=your_api_token_here
DATABASE_PASSWORD=your_db_password
```

### Step 5: Run Your First DAG

```bash
# Validate the DAG configuration
daglab validate dags/simple_data_pipeline.yaml

# Run the DAG
daglab run dags/simple_data_pipeline.yaml

# Check execution status
daglab status simple_data_pipeline
```

### Step 6: Monitor Execution

```bash
# View real-time logs
daglab logs simple_data_pipeline

# Get execution details
daglab show simple_data_pipeline --run-id latest

# List all DAG runs
daglab list-runs
```

## Understanding Key Concepts

### DAGs (Directed Acyclic Graphs)
A DAG represents your workflow as a collection of tasks with dependencies. Each task runs only after its dependencies complete successfully.

### Tasks
Individual units of work in your workflow. DagLab supports various task types:
- **Python Scripts**: Custom Python code execution
- **HTTP Requests**: API calls and web requests
- **Database Operations**: SQL queries and data operations
- **File Operations**: File processing and manipulation
- **Shell Commands**: System command execution

### Dependencies
Tasks can depend on other tasks using the `depends_on` field. This creates the directed graph structure of your workflow.

### Scheduling
DAGs can be scheduled to run automatically using cron expressions or triggered manually.

## Common Workflow Patterns

### 1. ETL Pipeline
```yaml
tasks:
  - id: extract
    type: database_query
    config:
      query: "SELECT * FROM source_table"
      
  - id: transform
    type: python_script
    depends_on: [extract]
    
  - id: load
    type: database_insert
    depends_on: [transform]
```

### 2. Data Validation
```yaml
tasks:
  - id: validate_schema
    type: data_validator
    config:
      schema_file: "schemas/input_schema.json"
      
  - id: process_data
    type: python_script
    depends_on: [validate_schema]
```

### 3. Parallel Processing
```yaml
tasks:
  - id: split_data
    type: data_splitter
    
  - id: process_chunk_1
    type: python_script
    depends_on: [split_data]
    
  - id: process_chunk_2
    type: python_script
    depends_on: [split_data]
    
  - id: merge_results
    type: data_merger
    depends_on: [process_chunk_1, process_chunk_2]
```

## Next Steps

Now that you have DagLab running, explore these topics:

1. **[Configuration Reference](./configuration.md)** - Learn about all configuration options
2. **[CLI Commands](./cli-commands.md)** - Master the command-line interface
3. **[Workflow Management](./workflow-management.md)** - Advanced workflow techniques
4. **[Tutorials](../tutorials/README.md)** - Hands-on examples and use cases
5. **[API Reference](../api-reference/README.md)** - Programmatic access to DagLab

## Troubleshooting

If you encounter issues:

1. Check the [Troubleshooting Guide](../troubleshooting/common-issues.md)
2. Verify your configuration with `daglab validate-config`
3. Check logs with `daglab logs --level DEBUG`
4. Ensure all dependencies are properly installed

## Getting Help

- **Documentation**: This complete documentation set
- **Examples**: Check the `/examples` directory
- **Community**: Join our Discord/Slack community
- **GitHub Issues**: Report bugs and request features

Happy workflow orchestration with DagLab!
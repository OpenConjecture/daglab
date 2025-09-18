# Developer Documentation

Welcome to the DagLab developer documentation! This section provides comprehensive guides for extending, customizing, and contributing to DagLab.

## Table of Contents

1. [Architecture Overview](./architecture.md)
2. [Development Setup](./setup.md)
3. [Plugin Development](./plugin-development.md)
4. [Custom Operators](./custom-operators.md)
5. [API Development](./api-development.md)
6. [Testing Framework](./testing.md)
7. [Contributing Guidelines](./contributing.md)
8. [Release Process](./release-process.md)

## Architecture Overview

DagLab follows a modular, plugin-based architecture designed for extensibility and scalability.

### Core Components

```
DagLab Architecture
├── Core Engine
│   ├── DAG Parser & Validator
│   ├── Task Scheduler
│   ├── Execution Engine
│   └── State Manager
├── Operators & Tasks
│   ├── Built-in Operators
│   ├── Plugin Operators
│   └── Custom Operators
├── Executors
│   ├── Local Executor
│   ├── Celery Executor
│   ├── Kubernetes Executor
│   └── Custom Executors
├── Storage Layer
│   ├── Metadata Database
│   ├── Log Storage
│   ├── Artifact Storage
│   └── State Storage
├── Integration Layer
│   ├── REST API
│   ├── WebUI
│   ├── CLI
│   └── SDKs
└── Extensions
    ├── Monitoring
    ├── Security
    ├── Webhooks
    └── Plugins
```

### Key Design Principles

#### 1. Modularity
Components are loosely coupled and can be developed independently:

```python
# Example: Plugin interface
class BasePlugin:
    def __init__(self, config):
        self.config = config
    
    def initialize(self):
        """Initialize plugin resources"""
        pass
    
    def cleanup(self):
        """Cleanup plugin resources"""
        pass
    
    def get_operators(self):
        """Return operators provided by this plugin"""
        return []
```

#### 2. Extensibility
Easy to add new functionality without modifying core code:

```python
# Example: Custom operator registration
@register_operator('custom_ml_trainer')
class MLTrainerOperator(BaseOperator):
    def execute(self, context):
        # Custom ML training logic
        pass
```

#### 3. Scalability
Designed to handle large-scale workflows:

```yaml
# Example: Scalable executor configuration
executor:
  type: kubernetes
  namespace: daglab-production
  worker_image: daglab/worker:latest
  auto_scaling:
    min_workers: 5
    max_workers: 100
    scale_up_threshold: 0.8
    scale_down_threshold: 0.2
```

## Development Environment Setup

### Prerequisites

- **Python 3.8+**
- **Git**
- **Docker** (for containerized development)
- **Node.js** (for WebUI development)
- **PostgreSQL** (for testing with production database)

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/openconjecture/daglab.git
cd daglab

# Create development environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
pytest tests/
```

### Development with Docker

```bash
# Build development image
docker build -f Dockerfile.dev -t daglab:dev .

# Run development container
docker run -it --rm \
  -v $(pwd):/app \
  -p 8080:8080 \
  daglab:dev bash

# Inside container
pip install -e .[dev]
daglab develop server --reload
```

## Plugin Development

DagLab's plugin system allows you to extend functionality without modifying core code.

### Plugin Structure

```
my_daglab_plugin/
├── setup.py
├── my_plugin/
│   ├── __init__.py
│   ├── operators/
│   │   ├── __init__.py
│   │   └── my_operator.py
│   ├── hooks/
│   │   ├── __init__.py
│   │   └── my_hook.py
│   └── sensors/
│       ├── __init__.py
│       └── my_sensor.py
└── tests/
    ├── __init__.py
    └── test_my_plugin.py
```

### Creating a Plugin

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name='daglab-my-plugin',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'daglab>=1.0.0',
        # Your plugin dependencies
    ],
    entry_points={
        'daglab.plugins': [
            'my_plugin = my_plugin.plugin:MyPlugin'
        ]
    }
)

# my_plugin/plugin.py
from daglab.plugins import BasePlugin
from .operators.my_operator import MyOperator

class MyPlugin(BasePlugin):
    name = 'my_plugin'
    version = '1.0.0'
    
    def get_operators(self):
        return {
            'my_operator': MyOperator
        }
    
    def get_hooks(self):
        return {
            'my_hook': MyHook
        }
```

### Example: Custom Database Operator

```python
# my_plugin/operators/database_operator.py
from daglab.operators import BaseOperator
from daglab.exceptions import OperatorException
import psycopg2

class CustomDatabaseOperator(BaseOperator):
    def __init__(self, 
                 sql_query,
                 connection_id,
                 parameters=None,
                 **kwargs):
        super().__init__(**kwargs)
        self.sql_query = sql_query
        self.connection_id = connection_id
        self.parameters = parameters or {}
    
    def execute(self, context):
        try:
            # Get connection from configuration
            connection_config = self.get_connection(self.connection_id)
            
            # Execute query
            with psycopg2.connect(**connection_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(self.sql_query, self.parameters)
                    
                    if cursor.description:
                        # Return results for SELECT queries
                        columns = [desc[0] for desc in cursor.description]
                        results = cursor.fetchall()
                        return {
                            'columns': columns,
                            'data': results,
                            'row_count': len(results)
                        }
                    else:
                        # Return affected rows for INSERT/UPDATE/DELETE
                        return {
                            'affected_rows': cursor.rowcount
                        }
                        
        except Exception as e:
            raise OperatorException(f"Database operation failed: {str(e)}")
```

## Custom Operator Development

### Operator Interface

All operators must implement the `BaseOperator` interface:

```python
from daglab.operators import BaseOperator
from daglab.exceptions import OperatorException

class MyCustomOperator(BaseOperator):
    def __init__(self, 
                 # Operator-specific parameters
                 input_file,
                 output_file,
                 processing_options=None,
                 # Base operator parameters
                 **kwargs):
        super().__init__(**kwargs)
        self.input_file = input_file
        self.output_file = output_file
        self.processing_options = processing_options or {}
    
    def execute(self, context):
        """
        Execute the operator logic.
        
        Args:
            context: Execution context with DAG run information
            
        Returns:
            Result data that can be used by downstream tasks
            
        Raises:
            OperatorException: If execution fails
        """
        try:
            # Pre-execution validation
            self.validate_inputs()
            
            # Main execution logic
            result = self.process_data()
            
            # Post-execution cleanup
            self.cleanup_resources()
            
            return result
            
        except Exception as e:
            self.log.error(f"Operator execution failed: {str(e)}")
            raise OperatorException(str(e))
    
    def validate_inputs(self):
        """Validate operator inputs before execution"""
        if not os.path.exists(self.input_file):
            raise OperatorException(f"Input file not found: {self.input_file}")
    
    def process_data(self):
        """Main data processing logic"""
        # Implement your processing logic here
        pass
    
    def cleanup_resources(self):
        """Cleanup any resources after execution"""
        pass
```

### Advanced Operator Features

#### Resource Management

```python
class ResourceManagedOperator(BaseOperator):
    def __init__(self, 
                 memory_limit='1GB',
                 cpu_limit=1,
                 **kwargs):
        super().__init__(**kwargs)
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
    
    def get_resource_requirements(self):
        """Return resource requirements for this operator"""
        return {
            'memory': self.memory_limit,
            'cpu': self.cpu_limit,
            'disk': '10GB'
        }
```

#### Templating Support

```python
class TemplatedOperator(BaseOperator):
    # Define which fields support Jinja templating
    template_fields = ['input_path', 'output_path', 'query']
    
    def __init__(self, 
                 input_path,
                 output_path,
                 query,
                 **kwargs):
        super().__init__(**kwargs)
        self.input_path = input_path
        self.output_path = output_path
        self.query = query
    
    def execute(self, context):
        # Template fields are automatically rendered before execution
        self.log.info(f"Processing file: {self.input_path}")
        self.log.info(f"Output will be saved to: {self.output_path}")
```

#### Retry Logic

```python
class RetryableOperator(BaseOperator):
    def __init__(self, 
                 max_retries=3,
                 retry_delay=60,
                 **kwargs):
        super().__init__(**kwargs)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def execute(self, context):
        for attempt in range(self.max_retries + 1):
            try:
                return self.do_work()
            except RetryableException as e:
                if attempt < self.max_retries:
                    self.log.warning(f"Attempt {attempt + 1} failed, retrying in {self.retry_delay}s")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise OperatorException(f"All {self.max_retries + 1} attempts failed")
```

## API Development

### Adding New REST Endpoints

```python
# daglab/api/routes/custom_routes.py
from flask import Blueprint, request, jsonify
from daglab.api.auth import require_auth
from daglab.api.validation import validate_json
from daglab.models import CustomModel

custom_bp = Blueprint('custom', __name__, url_prefix='/api/v1/custom')

@custom_bp.route('/', methods=['GET'])
@require_auth
def list_custom_resources():
    """List custom resources"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    resources = CustomModel.query.paginate(
        page=page, 
        per_page=per_page
    )
    
    return jsonify({
        'data': [r.to_dict() for r in resources.items],
        'pagination': {
            'page': page,
            'pages': resources.pages,
            'total': resources.total
        }
    })

@custom_bp.route('/', methods=['POST'])
@require_auth
@validate_json({
    'type': 'object',
    'required': ['name', 'config'],
    'properties': {
        'name': {'type': 'string'},
        'config': {'type': 'object'}
    }
})
def create_custom_resource():
    """Create a new custom resource"""
    data = request.get_json()
    
    resource = CustomModel(
        name=data['name'],
        config=data['config']
    )
    
    db.session.add(resource)
    db.session.commit()
    
    return jsonify(resource.to_dict()), 201
```

### Adding GraphQL Support

```python
# daglab/api/graphql/schema.py
import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType
from daglab.models import DAG, Task

class DAGType(SQLAlchemyObjectType):
    class Meta:
        model = DAG

class TaskType(SQLAlchemyObjectType):
    class Meta:
        model = Task

class Query(graphene.ObjectType):
    all_dags = graphene.List(DAGType)
    dag_by_id = graphene.Field(DAGType, id=graphene.String(required=True))
    
    def resolve_all_dags(self, info):
        return DAG.query.all()
    
    def resolve_dag_by_id(self, info, id):
        return DAG.query.filter(DAG.id == id).first()

schema = graphene.Schema(query=Query)
```

## Testing Framework

DagLab provides comprehensive testing utilities for plugin and operator development.

### Testing Operators

```python
# tests/test_my_operator.py
import pytest
from daglab.testing import OperatorTestCase
from my_plugin.operators.my_operator import MyOperator

class TestMyOperator(OperatorTestCase):
    def setUp(self):
        self.operator = MyOperator(
            input_file='test_input.csv',
            output_file='test_output.csv'
        )
    
    def test_successful_execution(self):
        # Setup test data
        self.create_test_file('test_input.csv', 'col1,col2\n1,2\n3,4')
        
        # Execute operator
        result = self.operator.execute(self.create_context())
        
        # Verify results
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists('test_output.csv'))
        
        # Verify output content
        with open('test_output.csv', 'r') as f:
            content = f.read()
            self.assertIn('processed_data', content)
    
    def test_missing_input_file(self):
        # Test error handling
        with self.assertRaises(OperatorException):
            self.operator.execute(self.create_context())
    
    def test_resource_cleanup(self):
        # Test resource cleanup
        self.create_test_file('test_input.csv', 'test_data')
        self.operator.execute(self.create_context())
        
        # Verify cleanup
        self.operator.cleanup_resources()
        # Add assertions for cleanup verification
```

### Testing DAGs

```python
# tests/test_my_dag.py
from daglab.testing import DAGTestCase

class TestMyDAG(DAGTestCase):
    def setUp(self):
        self.dag_file = 'dags/my_dag.yaml'
        self.test_data_dir = 'test_data/'
    
    def test_dag_validation(self):
        # Test DAG definition is valid
        dag = self.load_dag(self.dag_file)
        self.assertTrue(dag.is_valid())
        
        # Test task dependencies
        self.assert_task_dependencies(dag, {
            'extract_data': [],
            'process_data': ['extract_data'],
            'save_data': ['process_data']
        })
    
    def test_dag_execution(self):
        # Setup test environment
        self.setup_test_database()
        self.setup_test_files()
        
        # Execute DAG
        result = self.run_dag(self.dag_file, timeout=300)
        
        # Verify execution
        self.assertEqual(result.state, 'success')
        self.assertEqual(result.failed_task_count, 0)
        
        # Verify outputs
        self.verify_output_data()
    
    def test_error_handling(self):
        # Test DAG behavior with errors
        with self.mock_task_failure('process_data'):
            result = self.run_dag(self.dag_file)
            
        self.assertEqual(result.state, 'failed')
        self.verify_error_notifications()
```

### Integration Testing

```python
# tests/integration/test_full_pipeline.py
import pytest
from daglab.testing import IntegrationTestCase

class TestFullPipeline(IntegrationTestCase):
    @pytest.mark.integration
    def test_end_to_end_pipeline(self):
        # Setup complete test environment
        self.setup_test_infrastructure()
        
        # Deploy DAGs
        self.deploy_dags(['pipeline1.yaml', 'pipeline2.yaml'])
        
        # Execute pipeline
        results = self.run_pipeline_sequence([
            'pipeline1',
            'pipeline2'
        ])
        
        # Verify end-to-end results
        self.verify_pipeline_outputs(results)
        self.verify_data_quality()
        self.verify_performance_metrics()
    
    def setup_test_infrastructure(self):
        # Setup databases, storage, etc.
        pass
```

## Performance Testing

```python
# tests/performance/test_operator_performance.py
import time
import pytest
from memory_profiler import profile
from daglab.testing import PerformanceTestCase

class TestOperatorPerformance(PerformanceTestCase):
    @pytest.mark.performance
    def test_operator_memory_usage(self):
        # Test memory usage under different data sizes
        data_sizes = [1000, 10000, 100000]
        
        for size in data_sizes:
            with self.assert_memory_usage(max_mb=100):
                self.run_operator_with_data_size(size)
    
    @pytest.mark.performance
    def test_operator_execution_time(self):
        # Test execution time scaling
        start_time = time.time()
        
        self.operator.execute(self.create_context())
        
        execution_time = time.time() - start_time
        self.assertLess(execution_time, 60, "Operator took too long to execute")
    
    @profile
    def test_memory_profiling(self):
        # Detailed memory profiling
        self.operator.execute(self.create_context())
```

## Code Quality and Standards

### Code Style

DagLab follows PEP 8 with some additional conventions:

```python
# Good
class DataProcessingOperator(BaseOperator):
    """Operator for processing data files."""
    
    def __init__(self, 
                 input_path: str,
                 output_path: str,
                 chunk_size: int = 1000,
                 **kwargs):
        super().__init__(**kwargs)
        self.input_path = input_path
        self.output_path = output_path
        self.chunk_size = chunk_size
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data processing."""
        self.log.info(f"Processing {self.input_path}")
        
        try:
            result = self._process_file()
            return {'status': 'success', 'records_processed': result['count']}
        except Exception as e:
            self.log.error(f"Processing failed: {e}")
            raise
```

### Type Hints

Use type hints for better code documentation and IDE support:

```python
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

class TypedOperator(BaseOperator):
    def __init__(self, 
                 config: Dict[str, Any],
                 input_files: List[Path],
                 timeout: Optional[int] = None) -> None:
        super().__init__()
        self.config = config
        self.input_files = input_files
        self.timeout = timeout
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Union[str, int]]:
        return {'status': 'completed', 'processed_files': len(self.input_files)}
```

### Documentation Standards

```python
class WellDocumentedOperator(BaseOperator):
    """
    A well-documented operator example.
    
    This operator demonstrates proper documentation standards including
    detailed parameter descriptions and usage examples.
    
    Args:
        input_path: Path to input data file
        output_path: Path where processed data will be saved
        processing_mode: Mode for data processing ('batch' or 'streaming')
        chunk_size: Size of data chunks to process at once
        
    Raises:
        OperatorException: If input file is not found or processing fails
        ValueError: If processing_mode is not valid
        
    Example:
        ```python
        operator = WellDocumentedOperator(
            input_path='/data/input.csv',
            output_path='/data/output.csv',
            processing_mode='batch',
            chunk_size=1000
        )
        result = operator.execute(context)
        ```
    """
    
    def __init__(self, 
                 input_path: str,
                 output_path: str,
                 processing_mode: str = 'batch',
                 chunk_size: int = 1000,
                 **kwargs):
        super().__init__(**kwargs)
        # Parameter validation
        if processing_mode not in ['batch', 'streaming']:
            raise ValueError("processing_mode must be 'batch' or 'streaming'")
            
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.processing_mode = processing_mode
        self.chunk_size = chunk_size
```

## Debugging and Development Tools

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('daglab').setLevel(logging.DEBUG)

# Debug operator execution
class DebugOperator(BaseOperator):
    def execute(self, context):
        import pdb; pdb.set_trace()  # Debugger breakpoint
        
        # Or use logging for debugging
        self.log.debug(f"Context: {context}")
        self.log.debug(f"Operator config: {self.__dict__}")
```

### Development Server

```bash
# Start development server with auto-reload
daglab develop server --reload --debug --port 8080

# Start with specific configuration
daglab develop server --config config/development.yaml --reload
```

### Interactive Testing

```python
# Interactive operator testing
from daglab.testing import create_test_context
from my_plugin.operators import MyOperator

# Create test context
context = create_test_context(
    dag_id='test_dag',
    task_id='test_task',
    execution_date='2024-01-21'
)

# Create and test operator
operator = MyOperator(input_file='test.csv')
result = operator.execute(context)
print(result)
```

## Contributing Guidelines

### Development Workflow

1. **Fork and Clone**
```bash
git clone https://github.com/yourusername/daglab.git
cd daglab
git remote add upstream https://github.com/openconjecture/daglab.git
```

2. **Create Feature Branch**
```bash
git checkout -b feature/my-new-feature
```

3. **Make Changes and Test**
```bash
# Make your changes
vim src/daglab/operators/my_operator.py

# Run tests
pytest tests/test_my_operator.py
pytest tests/  # Full test suite

# Check code quality
flake8 src/
mypy src/
```

4. **Commit and Push**
```bash
git add .
git commit -m "Add new operator for data processing"
git push origin feature/my-new-feature
```

5. **Create Pull Request**
- Open PR against main branch
- Include comprehensive description
- Add tests for new functionality
- Update documentation as needed

### Code Review Process

All contributions go through code review:

1. **Automated Checks**
   - CI/CD pipeline runs tests
   - Code quality checks (flake8, mypy)
   - Security scanning
   - Performance regression tests

2. **Manual Review**
   - Code design and architecture
   - Test coverage and quality
   - Documentation completeness
   - Performance implications

3. **Approval and Merge**
   - At least one maintainer approval required
   - All checks must pass
   - Squash merge for clean history

## Release Process

### Version Management

DagLab uses semantic versioning (SemVer):

- **Major (X.0.0)**: Breaking changes
- **Minor (X.Y.0)**: New features, backward compatible
- **Patch (X.Y.Z)**: Bug fixes, backward compatible

### Release Checklist

1. **Pre-release**
   - Update version numbers
   - Update CHANGELOG.md
   - Run full test suite
   - Update documentation

2. **Release**
   - Create release branch
   - Tag release
   - Build and test packages
   - Deploy to staging

3. **Post-release**
   - Deploy to production
   - Update documentation site
   - Announce release
   - Monitor for issues

## Getting Help

### Development Support

- **Documentation**: Comprehensive guides and API references
- **Discord/Slack**: #development channel for technical discussions
- **GitHub Discussions**: Long-form technical discussions
- **Office Hours**: Weekly developer office hours

### Mentorship Program

New contributors can join our mentorship program:
- Paired with experienced contributor
- Guided through first contributions
- Regular check-ins and feedback
- Recognition upon completion

Ready to start developing? Begin with [Development Setup](./setup.md) or dive into [Plugin Development](./plugin-development.md)!
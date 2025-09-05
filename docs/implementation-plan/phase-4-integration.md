# Phase 4: Dagster Integration & GraphQL

**Duration**: 2-3 weeks  
**Dependencies**: Phase 3 (Notebook Generation & Templates)  
**Prerequisites**: Working template system, generated notebooks, and CLI framework

## Overview

Phase 4 implements the core Dagster integration functionality that enables generated notebooks to interact with Dagster instances. This phase focuses on GraphQL connectivity, entity discovery, run management, and the helper functions that make notebooks functional.

## Goals

1. **GraphQL Client**: Build robust GraphQL client with authentication support
2. **Entity Discovery**: Implement `daglab discover` command for finding assets and jobs
3. **Run Management**: Create `daglab run` command for executing jobs and asset selections
4. **Helper Functions**: Build the helper library that notebooks use for Dagster operations
5. **Authentication**: Implement comprehensive authentication handling

## Detailed Implementation Plan

### 4.1 GraphQL Client Foundation

**File**: `daglab/helpers/graphql.py`

**GraphQL Client Architecture**:

1. **Client Class**:
   ```python
   class DagsterClient:
       def __init__(
           self,
           host: str,
           port: int,
           auth: Optional[AuthConfig] = None,
           timeout: int = 30,
           max_retries: int = 3
       ):
           self.host = host
           self.port = port
           self.auth = auth
           self.session = self._create_session()
           self.endpoint = f"http://{host}:{port}/graphql"
       
       async def execute_query(
           self,
           query: str,
           variables: Optional[Dict[str, Any]] = None
       ) -> GraphQLResponse:
           """Execute GraphQL query with error handling and retries."""
   ```

2. **Query Management**:
   ```python
   class GraphQLQueries:
       GET_REPOSITORIES = """
       query GetRepositories {
           repositoriesOrError {
               ... on RepositoryConnection {
                   nodes {
                       name
                       location {
                           name
                       }
                   }
               }
           }
       }
       """
       
       LAUNCH_RUN = """
       mutation LaunchRun($executionParams: ExecutionParams!) {
           launchRun(executionParams: $executionParams) {
               ... on LaunchRunSuccess {
                   run {
                       id
                       status
                   }
               }
               ... on LaunchRunFailure {
                   message
               }
           }
       }
       """
   ```

**Implementation Tasks**:

1. **HTTP Client Setup**:
   - Configure httpx client with proper settings
   - Implement connection pooling and timeouts
   - Add retry logic with exponential backoff

2. **Authentication Integration**:
   - Support for bearer tokens, basic auth, and custom headers
   - Token refresh mechanisms
   - Secure credential handling

3. **Query Execution**:
   - Implement query execution with error handling
   - Add query validation and sanitization
   - Support for variables and fragments

4. **Response Handling**:
   - Parse GraphQL responses
   - Handle errors and exceptions
   - Provide meaningful error messages

### 4.2 Entity Discovery System

**File**: `daglab/commands/discover.py`

**Discovery Features**:

1. **Repository Discovery**:
   ```python
   async def discover_repositories(client: DagsterClient) -> List[RepositoryInfo]:
       """Discover all repositories and code locations."""
   
   async def discover_jobs(
       client: DagsterClient,
       repository: str,
       location: str
   ) -> List[JobInfo]:
       """Discover jobs in a specific repository."""
   
   async def discover_assets(
       client: DagsterClient,
       repository: str,
       location: str
   ) -> List[AssetInfo]:
       """Discover assets in a specific repository."""
   ```

2. **Filtering and Search**:
   ```python
   class EntityFilters:
       def __init__(
           self,
           pattern: Optional[str] = None,
           tags: Optional[Dict[str, str]] = None,
           groups: Optional[List[str]] = None
       ):
           self.pattern = pattern
           self.tags = tags
           self.groups = groups
   
   def filter_entities(
       entities: List[EntityInfo],
       filters: EntityFilters
   ) -> List[EntityInfo]:
       """Filter entities based on criteria."""
   ```

**Command Interface**:
```python
@app.command()
def discover(
    filter_type: str = typer.Option("all", "--filter", help="Filter type (jobs|assets|repos|locations)"),
    pattern: Optional[str] = typer.Option(None, "--pattern", help="Filter with wildcards"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Filter by tags (key=value,key2=value2)"),
    json: bool = typer.Option(False, "--json", help="Output in JSON format"),
    dagster_port: Optional[int] = typer.Option(None, "--dagster-port", help="Dagster UI port"),
    auth_token: Optional[str] = typer.Option(None, "--auth-token", help="Authentication token"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """List repositories, code locations, jobs, and assets via GraphQL."""
```

**Implementation Tasks**:

1. **GraphQL Queries**:
   - Implement queries for repositories, jobs, and assets
   - Add support for filtering and pagination
   - Handle different Dagster versions

2. **Entity Parsing**:
   - Parse GraphQL responses into structured data
   - Handle different entity types and properties
   - Add metadata extraction

3. **Filtering System**:
   - Implement pattern matching for entity names
   - Add tag-based filtering
   - Support for group-based filtering

4. **Output Formatting**:
   - Generate human-readable tables
   - Support JSON output for automation
   - Add export capabilities

### 4.3 Run Management System

**File**: `daglab/commands/run.py`

**Run Management Features**:

1. **Run Submission**:
   ```python
   async def submit_job_run(
       client: DagsterClient,
       job_name: str,
       repository: str,
       location: str,
       run_config: Optional[Dict] = None,
       asset_selection: Optional[List[str]] = None
   ) -> RunSubmitResult:
       """Submit a job run with configuration validation."""
   
   async def submit_asset_run(
       client: DagsterClient,
       asset_selection: List[str],
       repository: str,
       location: str,
       run_config: Optional[Dict] = None
   ) -> RunSubmitResult:
       """Submit an asset materialization run."""
   ```

2. **Run Monitoring**:
   ```python
   async def monitor_run(
       client: DagsterClient,
       run_id: str,
       timeout: int = 300,
       poll_interval: int = 2
   ) -> RunStatus:
       """Monitor run status with polling."""
   
   async def get_run_url(
       client: DagsterClient,
       run_id: str
   ) -> str:
       """Get URL for run in Dagster UI."""
   ```

**Command Interface**:
```python
@app.command()
def run(
    # Target selection (mutually exclusive)
    job: Optional[str] = typer.Option(None, "--job", help="Job name to run"),
    asset_selection: Optional[str] = typer.Option(None, "--asset-selection", help="Asset selection (a/b,c/d)"),
    asset_pattern: Optional[str] = typer.Option(None, "--asset-pattern", help="Asset pattern (orders/*)"),
    
    # Repository and location
    repo: str = typer.Option(..., "--repo", help="Repository name"),
    location: str = typer.Option(..., "--location", help="Location name"),
    
    # Configuration
    run_config: Optional[Path] = typer.Option(None, "--run-config", help="Run configuration file"),
    config_yaml: Optional[str] = typer.Option(None, "--config-yaml", help="Run configuration YAML"),
    
    # Execution options
    validate_only: bool = typer.Option(False, "--validate-only", help="Validate config without running"),
    wait: bool = typer.Option(True, "--wait", help="Wait for run completion"),
    timeout: int = typer.Option(300, "--timeout", help="Maximum wait time in seconds"),
    cancel_on_timeout: bool = typer.Option(False, "--cancel-on-timeout", help="Cancel run on timeout"),
    
    # Output options
    json: bool = typer.Option(False, "--json", help="Output in JSON format"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Trigger a job or asset selection run."""
```

**Implementation Tasks**:

1. **Run Submission**:
   - Implement job and asset run submission
   - Add configuration validation
   - Handle different run types

2. **Run Monitoring**:
   - Implement status polling
   - Add timeout handling
   - Provide progress updates

3. **Configuration Management**:
   - Parse and validate run configurations
   - Support for YAML and JSON formats
   - Handle configuration errors

4. **Error Handling**:
   - Handle run failures gracefully
   - Provide meaningful error messages
   - Support for run cancellation

### 4.4 Helper Functions Library

**File**: `daglab/helpers/__init__.py`

**Helper Functions**:

1. **Run Management Helpers**:
   ```python
   async def run_job(
       job_name: str,
       repository: str,
       location: str,
       run_config: Optional[Dict] = None,
       wait: bool = True
   ) -> RunResult:
       """Run a job and return results."""
   
   async def run_assets(
       asset_selection: List[str],
       repository: str,
       location: str,
       run_config: Optional[Dict] = None,
       wait: bool = True
   ) -> RunResult:
       """Run asset selection and return results."""
   ```

2. **Discovery Helpers**:
   ```python
   async def discover_jobs(
       repository: Optional[str] = None,
       location: Optional[str] = None
   ) -> List[JobInfo]:
       """Discover available jobs."""
   
   async def discover_assets(
       repository: Optional[str] = None,
       location: Optional[str] = None,
       pattern: Optional[str] = None
   ) -> List[AssetInfo]:
       """Discover available assets."""
   ```

3. **Configuration Helpers**:
   ```python
   def validate_config(
       job_name: str,
       run_config: Dict
   ) -> ValidationResult:
       """Validate run configuration against job schema."""
   
   def load_config_from_file(
       config_path: Path
   ) -> Dict:
       """Load and parse configuration file."""
   ```

4. **Performance Helpers**:
   ```python
   def track_performance(
       operation: str,
       func: Callable,
       *args,
       **kwargs
   ) -> Tuple[Any, PerformanceMetrics]:
       """Track performance of an operation."""
   
   def get_memory_usage() -> MemoryInfo:
       """Get current memory usage information."""
   ```

**Implementation Tasks**:

1. **Helper Function Implementation**:
   - Implement all helper functions
   - Add proper error handling
   - Include performance tracking

2. **Integration with GraphQL Client**:
   - Use GraphQL client for all operations
   - Handle authentication automatically
   - Provide consistent error handling

3. **State Management**:
   - Implement persistent state across notebook cells
   - Add state validation and recovery
   - Support for state reset

4. **Performance Monitoring**:
   - Track execution times and memory usage
   - Provide performance comparisons
   - Add resource utilization monitoring

### 4.5 Authentication System

**File**: `daglab/helpers/auth.py`

**Authentication Features**:

1. **Auth Configuration**:
   ```python
   class AuthConfig(BaseModel):
       type: AuthType  # bearer, basic, custom
       token: Optional[str] = None
       username: Optional[str] = None
       password: Optional[str] = None
       header_name: str = "Authorization"
       custom_headers: Dict[str, str] = {}
   
       @classmethod
       def from_env(cls) -> Optional['AuthConfig']:
           """Load authentication from environment variables."""
   
       @classmethod
       def from_config(cls, config: Dict) -> 'AuthConfig':
           """Load authentication from configuration."""
   ```

2. **Token Management**:
   ```python
   class TokenManager:
       def __init__(self, config: AuthConfig):
           self.config = config
           self._token_cache = {}
       
       async def get_valid_token(self) -> str:
           """Get a valid authentication token."""
       
       async def refresh_token(self) -> str:
           """Refresh authentication token."""
   ```

**Implementation Tasks**:

1. **Authentication Types**:
   - Implement bearer token authentication
   - Add basic authentication support
   - Support for custom headers

2. **Token Management**:
   - Implement token caching and refresh
   - Handle token expiration
   - Add secure token storage

3. **Environment Integration**:
   - Load tokens from environment variables
   - Support for credential files
   - Handle missing credentials gracefully

4. **Security Features**:
   - Never log or display tokens
   - Secure credential handling
   - Input sanitization

### 4.6 Configuration Validation

**File**: `daglab/helpers/validation.py`

**Validation Features**:

1. **Run Configuration Validation**:
   ```python
   async def validate_run_config(
       client: DagsterClient,
       job_name: str,
       run_config: Dict
   ) -> ValidationResult:
       """Validate run configuration against job schema."""
   
   def validate_yaml_config(
       config: str,
       schema: Optional[Dict] = None
   ) -> ValidationResult:
       """Validate YAML configuration."""
   ```

2. **Input Sanitization**:
   ```python
   def sanitize_input(
       text: str,
       context: InputContext
   ) -> str:
       """Sanitize user input for security."""
   
   def validate_asset_selection(
       selection: str
   ) -> ValidationResult:
       """Validate asset selection syntax."""
   ```

**Implementation Tasks**:

1. **Schema Validation**:
   - Implement run configuration validation
   - Add schema parsing and validation
   - Handle validation errors

2. **Input Sanitization**:
   - Sanitize user inputs for security
   - Prevent injection attacks
   - Validate file paths and URLs

3. **Configuration Parsing**:
   - Parse YAML and JSON configurations
   - Handle parsing errors
   - Provide helpful error messages

## Acceptance Criteria

### Functional Requirements

- [ ] GraphQL client connects to Dagster instances successfully
- [ ] `daglab discover` finds and lists entities correctly
- [ ] `daglab run` submits and monitors runs properly
- [ ] Helper functions work in generated notebooks
- [ ] Authentication works with different auth types
- [ ] Configuration validation catches errors

### Integration Requirements

- [ ] Generated notebooks can connect to Dagster
- [ ] Notebooks can discover and run jobs/assets
- [ ] Run monitoring provides real-time updates
- [ ] Error handling is consistent across all operations
- [ ] Performance tracking works correctly

### Security Requirements

- [ ] Authentication tokens are handled securely
- [ ] User inputs are sanitized properly
- [ ] No sensitive data is logged or displayed
- [ ] Configuration validation prevents injection

### Code Quality Requirements

- [ ] All GraphQL operations are well-tested
- [ ] Error handling is comprehensive
- [ ] Helper functions are well-documented
- [ ] Code follows security best practices

## Testing Strategy

### Unit Tests

1. **GraphQL Client Tests**:
   - Test connection establishment
   - Test query execution
   - Test error handling
   - Test authentication

2. **Helper Function Tests**:
   - Test all helper functions
   - Test error scenarios
   - Test performance tracking
   - Test state management

3. **Validation Tests**:
   - Test configuration validation
   - Test input sanitization
   - Test error handling
   - Test edge cases

### Integration Tests

1. **Dagster Integration**:
   - Test with real Dagster instances
   - Test entity discovery
   - Test run submission and monitoring
   - Test authentication scenarios

2. **Notebook Integration**:
   - Test helper functions in notebooks
   - Test state management
   - Test error handling
   - Test performance tracking

### End-to-End Tests

1. **Complete Workflows**:
   - Test discover → run → monitor workflow
   - Test notebook generation → execution workflow
   - Test error recovery scenarios
   - Test authentication workflows

## Deliverables

1. **Complete GraphQL client** with authentication support
2. **Working `daglab discover` command** with filtering
3. **Functional `daglab run` command** with monitoring
4. **Comprehensive helper functions library** for notebooks
5. **Robust authentication system** with multiple auth types
6. **Configuration validation system** with security features
7. **Comprehensive test suite** for all components
8. **Updated documentation** with integration examples

## Risk Mitigation

1. **GraphQL Compatibility**: Test with different Dagster versions
2. **Authentication Complexity**: Start with simple auth and add complexity
3. **Error Handling**: Implement comprehensive error handling early
4. **Performance**: Monitor and optimize GraphQL operations

## Success Metrics

- Generated notebooks can successfully connect to Dagster
- Run submission and monitoring works reliably
- Authentication handles various scenarios
- Helper functions are easy to use and well-documented
- Error messages help users resolve issues

## Next Phase Preparation

Phase 4 sets up the Dagster integration for Phase 5 by providing:
- Working GraphQL client for advanced operations
- Run management system for development workflows
- Helper functions for notebook functionality
- Authentication system for secure operations

The Dagster integration established in Phase 4 will be enhanced in Phase 5 with advanced features like the development environment and export capabilities.

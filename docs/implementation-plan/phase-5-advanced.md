# Phase 5: Advanced Features & Polish

**Duration**: 2-3 weeks  
**Dependencies**: Phase 4 (Dagster Integration & GraphQL)  
**Prerequisites**: Working GraphQL client, run management, and helper functions

## Overview

Phase 5 implements the advanced features that complete the `daglab` user experience. This phase focuses on the development environment, export capabilities, performance monitoring, and the remaining CLI commands that provide a complete workflow for data engineers.

## Goals

1. **Development Environment**: Implement `daglab dev` command for sidecar development
2. **Export System**: Build `daglab export` command with metadata attachment
3. **Performance Monitoring**: Add comprehensive performance tracking and metrics
4. **Advanced CLI Commands**: Complete remaining commands (`stats`, `migrate`)
5. **User Experience Polish**: Enhance error handling, feedback, and usability

## Detailed Implementation Plan

### 5.1 Development Environment (`daglab dev`)

**File**: `daglab/commands/dev.py`

**Development Environment Features**:

1. **Sidecar Process Management**:
   ```python
   class DevEnvironment:
       def __init__(self, config: daglabConfig):
           self.config = config
           self.dagster_process: Optional[subprocess.Popen] = None
           self.marimo_process: Optional[subprocess.Popen] = None
           self.ports = self._find_available_ports()
       
       async def start(self, notebook_path: Optional[Path] = None):
           """Start both Dagster UI and marimo editor."""
       
       async def stop(self):
           """Stop all processes gracefully."""
       
       def get_status(self) -> DevStatus:
           """Get current status of development environment."""
   ```

2. **Port Management**:
   ```python
   class PortManager:
       def __init__(self, start_port: int = 3000, end_port: int = 3100):
           self.start_port = start_port
           self.end_port = end_port
           self.used_ports = set()
       
       def find_available_port(self, preferred: int) -> int:
           """Find an available port, starting from preferred."""
       
       def reserve_port(self, port: int) -> bool:
           """Reserve a port for use."""
       
       def release_port(self, port: int):
           """Release a reserved port."""
   ```

3. **Process Monitoring**:
   ```python
   class ProcessMonitor:
       def __init__(self):
           self.processes: Dict[str, subprocess.Popen] = {}
           self.monitoring = False
       
       async def start_monitoring(self):
           """Start monitoring all processes."""
       
       async def stop_monitoring(self):
           """Stop monitoring processes."""
       
       def get_process_status(self, name: str) -> ProcessStatus:
           """Get status of a specific process."""
   ```

**Command Interface**:
```python
@app.command()
def dev(
    notebook: Optional[Path] = typer.Option(None, "--notebook", help="Notebook to open"),
    dagster_port: Optional[int] = typer.Option(None, "--dagster-port", help="Dagster UI port"),
    marimo_port: Optional[int] = typer.Option(None, "--marimo-port", help="Marimo editor port"),
    port_range: Optional[str] = typer.Option(None, "--port-range", help="Port range (start-end)"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser automatically"),
    env_file: Optional[Path] = typer.Option(None, "--env-file", help="Environment file to load"),
    ci: bool = typer.Option(False, "--ci", help="Non-interactive mode for CI/CD"),
    sandbox: bool = typer.Option(False, "--sandbox", help="Restricted GraphQL operations"),
    log_level: str = typer.Option("INFO", "--log-level", help="Log level (DEBUG|INFO|WARNING|ERROR)"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Start Dagster UI and marimo editor side-by-side."""
```

**Implementation Tasks**:

1. **Process Management**:
   - Implement subprocess management for Dagster and marimo
   - Add process monitoring and health checks
   - Handle process failures and restarts

2. **Port Management**:
   - Implement port discovery and reservation
   - Handle port conflicts gracefully
   - Support for custom port ranges

3. **Browser Integration**:
   - Open both UIs in browser automatically
   - Handle browser launch failures
   - Support for different browsers

4. **Environment Management**:
   - Load environment variables from files
   - Handle environment-specific configurations
   - Support for CI/CD environments

### 5.2 Export System (`daglab export`)

**File**: `daglab/commands/export.py`

**Export Features**:

1. **HTML Export**:
   ```python
   async def export_html(
       notebook_path: Path,
       output_path: Path,
       compress: bool = False
   ) -> ExportResult:
       """Export marimo notebook to HTML."""
   
   async def export_with_compression(
       notebook_path: Path,
       output_path: Path
   ) -> ExportResult:
       """Export notebook with gzip compression."""
   ```

2. **Cloud Storage Integration**:
   ```python
   class CloudStorage:
       def __init__(self, provider: str, config: Dict[str, Any]):
           self.provider = provider
           self.config = config
       
       async def upload(
           self,
           file_path: Path,
           key: str
       ) -> CloudUploadResult:
           """Upload file to cloud storage."""
       
       def generate_signed_url(
           self,
           key: str,
           expiration: int = 3600
       ) -> str:
           """Generate signed URL for file access."""
   ```

3. **Metadata Attachment**:
   ```python
   async def attach_metadata(
       client: DagsterClient,
       target: Union[AssetKey, str],
       metadata: Dict[str, Any],
       metadata_key: str = "exploration"
   ) -> AttachResult:
       """Attach metadata to Dagster asset or job."""
   
   def generate_metadata(
       notebook_path: Path,
       export_path: Path,
       cloud_url: Optional[str] = None
   ) -> Dict[str, Any]:
       """Generate metadata for notebook export."""
   ```

**Command Interface**:
```python
@app.command()
def export(
    notebook: Path = typer.Argument(..., help="Notebook file to export"),
    output: Optional[Path] = typer.Option(None, "--output", help="Output HTML file"),
    attach: Optional[str] = typer.Option(None, "--attach", help="Attach to asset or job"),
    metadata_key: str = typer.Option("exploration", "--metadata-key", help="Metadata key"),
    upload: Optional[str] = typer.Option(None, "--upload", help="Upload to cloud storage"),
    retention_days: int = typer.Option(30, "--retention-days", help="Retention period in days"),
    compress: bool = typer.Option(False, "--compress", help="Compress HTML output"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Export marimo notebook to HTML and attach as Dagster metadata."""
```

**Implementation Tasks**:

1. **HTML Export**:
   - Implement marimo HTML export
   - Add compression support
   - Handle export errors

2. **Cloud Storage**:
   - Implement S3, GCS, and Azure support
   - Add signed URL generation
   - Handle upload failures

3. **Metadata Attachment**:
   - Implement GraphQL metadata mutations
   - Add fallback to compute-time helpers
   - Handle attachment failures

4. **Retention Management**:
   - Implement retention policy enforcement
   - Add cleanup of old exports
   - Handle storage quota management

### 5.3 Performance Monitoring System

**File**: `daglab/helpers/performance.py`

**Performance Monitoring Features**:

1. **Performance Tracker**:
   ```python
   class PerformanceTracker:
       def __init__(self):
           self.metrics: Dict[str, List[PerformanceMetric]] = {}
           self.active_operations: Dict[str, float] = {}
       
       def start_timing(self, operation: str) -> None:
           """Start timing an operation."""
       
       def end_timing(self, operation: str) -> float:
           """End timing and record metric."""
       
       def get_memory_usage(self) -> MemoryInfo:
           """Get current memory usage."""
       
       def compare_runs(self, run_a: str, run_b: str) -> ComparisonResult:
           """Compare performance between runs."""
   ```

2. **Metrics Collection**:
   ```python
   class MetricsCollector:
       def __init__(self):
           self.collectors: Dict[str, Callable] = {}
       
       def register_collector(self, name: str, collector: Callable):
           """Register a metrics collector."""
       
       def collect_metrics(self) -> Dict[str, Any]:
           """Collect all registered metrics."""
       
       def export_metrics(self, format: str = "json") -> str:
           """Export metrics in specified format."""
   ```

3. **Performance Visualization**:
   ```python
   def create_performance_chart(
       metrics: List[PerformanceMetric],
       chart_type: str = "line"
   ) -> str:
       """Create performance visualization."""
   
   def generate_performance_report(
       metrics: Dict[str, Any]
   ) -> str:
       """Generate human-readable performance report."""
   ```

**Implementation Tasks**:

1. **Metrics Collection**:
   - Implement timing and memory tracking
   - Add system resource monitoring
   - Collect operation-specific metrics

2. **Performance Analysis**:
   - Implement run comparison
   - Add trend analysis
   - Generate performance reports

3. **Visualization**:
   - Create performance charts
   - Add interactive visualizations
   - Export performance data

### 5.4 Advanced CLI Commands

**File**: `daglab/commands/stats.py`

**Statistics Command**:
```python
@app.command()
def stats(
    since: Optional[str] = typer.Option(None, "--since", help="Stats since date"),
    json: bool = typer.Option(False, "--json", help="Output in JSON format"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Show usage statistics and performance metrics."""
```

**File**: `daglab/commands/migrate.py`

**Migration Command**:
```python
@app.command()
def migrate(
    from_jupyter: Path = typer.Argument(..., help="Source Jupyter notebook"),
    to: Optional[Path] = typer.Option(None, "--to", help="Destination file"),
    preserve_outputs: bool = typer.Option(False, "--preserve-outputs", help="Keep cell outputs"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Migrate from Jupyter notebooks to marimo format."""
```

**Implementation Tasks**:

1. **Statistics Collection**:
   - Implement usage statistics tracking
   - Add performance metrics collection
   - Create statistics reporting

2. **Jupyter Migration**:
   - Implement Jupyter to marimo conversion
   - Handle different notebook formats
   - Preserve notebook structure and content

3. **Data Persistence**:
   - Store statistics and metrics
   - Implement data export
   - Handle data cleanup

### 5.5 Enhanced Error Handling and User Experience

**File**: `daglab/runtime/errors.py`

**Enhanced Error Handling**:

1. **Error Recovery**:
   ```python
   class ErrorRecovery:
       def __init__(self):
           self.recovery_strategies: Dict[str, Callable] = {}
       
       def register_strategy(self, error_type: str, strategy: Callable):
           """Register error recovery strategy."""
       
       async def attempt_recovery(self, error: Exception) -> bool:
           """Attempt to recover from error."""
       
       def get_recovery_suggestions(self, error: Exception) -> List[str]:
           """Get recovery suggestions for error."""
   ```

2. **User Feedback**:
   ```python
   class UserFeedback:
       def __init__(self, console: Console):
           self.console = console
       
       def show_progress(self, message: str, progress: float):
           """Show progress indicator."""
       
       def show_success(self, message: str):
           """Show success message."""
       
       def show_warning(self, message: str):
           """Show warning message."""
       
       def show_error(self, message: str, suggestions: List[str] = None):
           """Show error message with suggestions."""
   ```

**Implementation Tasks**:

1. **Error Recovery**:
   - Implement automatic error recovery
   - Add recovery strategies for common errors
   - Provide user guidance for recovery

2. **User Feedback**:
   - Enhance progress indicators
   - Improve error messages
   - Add success confirmations

3. **Help System**:
   - Add contextual help
   - Implement command suggestions
   - Provide troubleshooting guides

### 5.6 State Management Enhancement

**File**: `daglab/helpers/state.py`

**Enhanced State Management**:

1. **Persistent State**:
   ```python
   class PersistentState:
       def __init__(self, state_file: Path):
           self.state_file = state_file
           self.state: Dict[str, Any] = {}
           self.history: List[StateChange] = []
       
       def load_state(self) -> Dict[str, Any]:
           """Load state from file."""
       
       def save_state(self, state: Dict[str, Any]):
           """Save state to file."""
       
       def get_history(self) -> List[StateChange]:
           """Get state change history."""
   ```

2. **State Validation**:
   ```python
   def validate_state(state: Dict[str, Any]) -> ValidationResult:
       """Validate state structure and values."""
   
   def migrate_state(old_state: Dict[str, Any], version: str) -> Dict[str, Any]:
       """Migrate state to new version."""
   ```

**Implementation Tasks**:

1. **State Persistence**:
   - Implement file-based state storage
   - Add state versioning and migration
   - Handle state corruption recovery

2. **State Validation**:
   - Validate state structure
   - Check state consistency
   - Handle invalid states

3. **State History**:
   - Track state changes
   - Implement state rollback
   - Add state debugging

## Acceptance Criteria

### Functional Requirements

- [ ] `daglab dev` starts both Dagster UI and marimo editor
- [ ] `daglab export` exports notebooks to HTML with metadata attachment
- [ ] Performance monitoring tracks execution times and memory usage
- [ ] `daglab stats` shows usage statistics and metrics
- [ ] `daglab migrate` converts Jupyter notebooks to marimo
- [ ] Error handling provides recovery suggestions

### User Experience Requirements

- [ ] Development environment is easy to start and stop
- [ ] Export process provides clear feedback
- [ ] Performance metrics are easy to understand
- [ ] Error messages include actionable suggestions
- [ ] All commands provide consistent user experience

### Performance Requirements

- [ ] Development environment starts quickly
- [ ] Export process is efficient
- [ ] Performance monitoring has minimal overhead
- [ ] State management is fast and reliable

### Code Quality Requirements

- [ ] All advanced features are well-tested
- [ ] Error handling is comprehensive
- [ ] Performance monitoring is accurate
- [ ] Code is well-documented and maintainable

## Testing Strategy

### Unit Tests

1. **Process Management Tests**:
   - Test process startup and shutdown
   - Test port management
   - Test process monitoring

2. **Export System Tests**:
   - Test HTML export
   - Test cloud storage integration
   - Test metadata attachment

3. **Performance Monitoring Tests**:
   - Test metrics collection
   - Test performance analysis
   - Test visualization generation

### Integration Tests

1. **Development Environment**:
   - Test complete dev workflow
   - Test process failure handling
   - Test port conflict resolution

2. **Export Workflow**:
   - Test complete export workflow
   - Test cloud storage integration
   - Test metadata attachment

3. **Performance Monitoring**:
   - Test metrics collection in real scenarios
   - Test performance analysis
   - Test report generation

### End-to-End Tests

1. **Complete Workflows**:
   - Test dev → scaffold → run → export workflow
   - Test error recovery scenarios
   - Test performance monitoring integration

2. **User Experience**:
   - Test all commands with real users
   - Test error handling and recovery
   - Test help and documentation

## Deliverables

1. **Complete development environment** with process management
2. **Working export system** with cloud storage and metadata attachment
3. **Comprehensive performance monitoring** with visualization
4. **Advanced CLI commands** (stats, migrate)
5. **Enhanced error handling** with recovery suggestions
6. **Improved state management** with persistence and validation
7. **Comprehensive test suite** for all advanced features
8. **Updated documentation** with advanced usage examples

## Risk Mitigation

1. **Process Management Complexity**: Start with simple process management and add complexity
2. **Cloud Storage Integration**: Test with multiple providers and handle failures
3. **Performance Overhead**: Monitor and optimize performance monitoring
4. **User Experience**: Test with real users and iterate based on feedback

## Success Metrics

- Development environment starts in <30 seconds
- Export process completes successfully
- Performance monitoring provides useful insights
- Error recovery helps users resolve issues
- All advanced features work reliably

## Next Phase Preparation

Phase 5 completes the core functionality for Phase 6 by providing:
- Complete user workflow from development to export
- Performance monitoring for optimization
- Advanced features for power users
- Robust error handling and recovery

The advanced features established in Phase 5 will be polished and packaged in Phase 6 for production release.

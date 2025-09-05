# Phase 2: CLI Framework & Basic Commands

**Duration**: 1-2 weeks  
**Dependencies**: Phase 1 (Foundation & Core Infrastructure)  
**Prerequisites**: Working configuration system, CLI framework, and core utilities

## Overview

Phase 2 builds upon the foundation established in Phase 1 to implement the core CLI commands that provide the essential user experience for `daglab`. This phase focuses on the `init`, `doctor`, and `clean` commands, which form the backbone of the user workflow.

## Goals

1. **Complete CLI Structure**: Implement all command stubs with proper help text and argument parsing
2. **Project Initialization**: Build robust `daglab init` command for both existing and new projects
3. **Diagnostics System**: Create comprehensive `daglab doctor` command for troubleshooting
4. **Cleanup Utilities**: Implement `daglab clean` command for maintenance
5. **User Experience**: Ensure all commands provide clear feedback and error handling

## Detailed Implementation Plan

### 2.1 Enhanced CLI Framework

**File**: `daglab/cli.py`

**Enhanced Command Structure**:
```python
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(
    name="daglab",
    help="Scaffold and run paired marimo notebooks for Dagster assets & jobs.",
    rich_markup_mode="rich",
    no_args_is_help=True
)

# Global options
def version_callback(value: bool):
    if value:
        console.print(f"daglab version {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", callback=version_callback),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-error output")
):
    """Dagster ↔ marimo Paired Notebook CLI"""
    # Global configuration and logging setup
    pass
```

**Implementation Tasks**:

1. **Enhance CLI structure** with global options and callbacks
2. **Add Rich integration** for beautiful output and progress indicators
3. **Implement global configuration loading** and context management
4. **Add comprehensive help text** for all commands and options
5. **Set up proper error handling** with user-friendly messages

### 2.2 Project Initialization (`daglab init`)

**File**: `daglab/commands/init.py`

**Command Features**:

1. **Project Detection**:
   - Detect existing Dagster projects by looking for markers
   - Support for `dagster.yaml`, `workspace.yaml`, `pyproject.toml` with dagster deps
   - Intelligent project structure analysis

2. **Existing Project Initialization**:
   - Create `.daglab/` directory structure
   - Generate `daglab.yaml` with project-aware defaults
   - Set up `dagster/notebooks/` directory
   - Update `.gitignore` with appropriate entries
   - Create optional `justfile` or `Makefile` targets

3. **New Project Bootstrap** (`--bootstrap`):
   - Create complete Dagster project structure
   - Generate starter assets and jobs
   - Create example notebooks
   - Set up both Dagster and daglab configurations

**Command Interface**:
```python
@app.command()
def init(
    bootstrap: bool = typer.Option(False, "--bootstrap", help="Create new Dagster project"),
    notebooks_dir: Optional[Path] = typer.Option(None, "--notebooks-dir", help="Notebooks directory path"),
    ports: Optional[str] = typer.Option(None, "--ports", help="Port configuration (dagster=3000,marimo=3010)"),
    no_examples: bool = typer.Option(False, "--no-examples", help="Skip example generation"),
    template: str = typer.Option("standard", "--template", help="Project template (minimal|standard|ml)"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Initialize daglab in current or new Dagster project."""
```

**Implementation Tasks**:

1. **Project Detection Logic**:
   - Implement detection of existing Dagster projects
   - Handle various project structures and configurations
   - Provide clear feedback about detected project type

2. **Configuration Generation**:
   - Create `daglab.yaml` with appropriate defaults
   - Handle port configuration parsing
   - Support for different project templates

3. **Directory Structure Creation**:
   - Create necessary directories with proper permissions
   - Handle existing directories gracefully
   - Update `.gitignore` appropriately

4. **Bootstrap Functionality**:
   - Generate complete Dagster project structure
   - Create starter assets and jobs
   - Generate example notebooks
   - Set up proper configurations

5. **User Feedback**:
   - Provide clear progress indicators
   - Show next steps after initialization
   - Handle errors gracefully with remediation

### 2.3 Diagnostics System (`daglab doctor`)

**File**: `daglab/commands/doctor.py`

**Diagnostic Checks**:

1. **Environment Checks**:
   - Python version compatibility
   - Required dependencies availability
   - Optional dependencies status
   - Environment variables

2. **Dagster Integration**:
   - Dagster installation and version
   - Dagster instance configuration
   - Repository discovery
   - GraphQL endpoint accessibility

3. **Marimo Integration**:
   - Marimo installation and version
   - Marimo CLI availability
   - Port availability for marimo

4. **Project Configuration**:
   - `daglab.yaml` validation
   - Directory structure validation
   - File permissions
   - Git repository status

5. **Network and Connectivity**:
   - Port availability
   - Network connectivity
   - Authentication configuration

**Command Interface**:
```python
@app.command()
def doctor(
    fix: bool = typer.Option(False, "--fix", help="Attempt automatic fixes"),
    check_deps: bool = typer.Option(False, "--check-deps", help="Deep dependency check"),
    json: bool = typer.Option(False, "--json", help="Output in JSON format"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Run comprehensive diagnostics and dependency checks."""
```

**Implementation Tasks**:

1. **Diagnostic Framework**:
   - Create modular diagnostic check system
   - Implement check result reporting
   - Add automatic fix capabilities where possible

2. **Environment Validation**:
   - Check Python version and dependencies
   - Validate environment variables
   - Test network connectivity

3. **Integration Testing**:
   - Test Dagster connectivity
   - Validate marimo installation
   - Check port availability

4. **Configuration Validation**:
   - Validate `daglab.yaml` configuration
   - Check project structure
   - Verify file permissions

5. **Reporting System**:
   - Generate human-readable reports
   - Support JSON output for automation
   - Provide actionable remediation steps

### 2.4 Cleanup Utilities (`daglab clean`)

**File**: `daglab/commands/clean.py`

**Cleanup Operations**:

1. **Artifact Cleanup**:
   - Remove old HTML exports
   - Clean up temporary files
   - Clear cache directories

2. **Notebook Cleanup**:
   - Remove generated notebooks (optional)
   - Clean up checkpoint files
   - Remove orphaned files

3. **Configuration Cleanup**:
   - Reset configuration to defaults
   - Remove old configuration backups
   - Clean up log files

**Command Interface**:
```python
@app.command()
def clean(
    older_than: int = typer.Option(30, "--older-than", help="Clean files older than N days"),
    notebooks: bool = typer.Option(False, "--notebooks", help="Also clean generated notebooks"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview what would be deleted"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Clean up artifacts, temp files, and old exports."""
```

**Implementation Tasks**:

1. **File Discovery**:
   - Find files matching cleanup criteria
   - Handle different file types and patterns
   - Respect retention policies

2. **Safe Deletion**:
   - Implement dry-run mode
   - Add confirmation prompts
   - Handle permission errors gracefully

3. **Cleanup Policies**:
   - Implement age-based cleanup
   - Handle different file types
   - Preserve important files

4. **User Interface**:
   - Show cleanup preview
   - Provide progress indicators
   - Handle user confirmation

### 2.5 Additional Commands (Stubs)

**File**: `daglab/commands/`

**Command Stubs** (implementations in later phases):

1. **`daglab scaffold`** - Notebook generation (Phase 3)
2. **`daglab dev`** - Development environment (Phase 5)
3. **`daglab discover`** - Entity discovery (Phase 4)
4. **`daglab run`** - Run execution (Phase 4)
5. **`daglab export`** - Export functionality (Phase 5)
6. **`daglab stats`** - Usage statistics (Phase 5)
7. **`daglab migrate`** - Jupyter migration (Phase 5)

**Implementation Tasks**:

1. **Create command stubs** with proper help text
2. **Set up command structure** for future implementation
3. **Add placeholder implementations** that show "coming soon" messages
4. **Ensure consistent CLI experience** across all commands

## Acceptance Criteria

### Functional Requirements

- [ ] `daglab init` works for both existing and new projects
- [ ] `daglab init --bootstrap` creates complete project structure
- [ ] `daglab doctor` provides comprehensive diagnostics
- [ ] `daglab clean` safely removes old artifacts
- [ ] All commands provide clear help text and error messages
- [ ] Commands handle edge cases gracefully

### User Experience Requirements

- [ ] Commands provide clear progress indicators
- [ ] Error messages include remediation steps
- [ ] Output is well-formatted and readable
- [ ] Commands work in both interactive and non-interactive modes
- [ ] Help text is comprehensive and accurate

### Code Quality Requirements

- [ ] All commands have comprehensive test coverage
- [ ] Code passes type checking and linting
- [ ] Error handling is consistent across commands
- [ ] Commands are well-documented

## Testing Strategy

### Unit Tests

1. **Command Tests**:
   - Test command argument parsing
   - Test command logic with various inputs
   - Test error handling and edge cases
   - Test help text generation

2. **Integration Tests**:
   - Test full command workflows
   - Test command interactions
   - Test configuration handling
   - Test file system operations

### End-to-End Tests

1. **Project Initialization**:
   - Test initialization in clean directory
   - Test initialization in existing Dagster project
   - Test bootstrap functionality
   - Test error scenarios

2. **Diagnostics**:
   - Test diagnostics in various environments
   - Test automatic fixes
   - Test reporting formats

3. **Cleanup**:
   - Test cleanup operations
   - Test dry-run mode
   - Test confirmation handling

## Deliverables

1. **Complete CLI command structure** with all commands implemented or stubbed
2. **Working `daglab init` command** for both existing and new projects
3. **Comprehensive `daglab doctor` command** with diagnostics and fixes
4. **Functional `daglab clean` command** with safe cleanup operations
5. **Enhanced CLI framework** with Rich integration and error handling
6. **Comprehensive test suite** for all implemented commands
7. **Updated documentation** reflecting new functionality

## Risk Mitigation

1. **Project Detection Complexity**: Start with simple detection and add complexity incrementally
2. **File System Operations**: Implement safe file operations with proper error handling
3. **User Experience**: Test commands with real users early and often
4. **Configuration Complexity**: Keep configuration simple and well-documented

## Success Metrics

- Users can initialize daglab in <2 minutes
- Diagnostics provide actionable feedback
- Cleanup operations are safe and predictable
- All commands provide consistent user experience
- Error messages help users resolve issues quickly

## Next Phase Preparation

Phase 2 sets up the CLI framework for Phase 3 by providing:
- Stable command structure for notebook generation
- Configuration system for template management
- Error handling framework for user operations
- File system utilities for notebook creation
- User experience patterns for interactive operations

The CLI framework established in Phase 2 will be extended in Phase 3 with notebook generation capabilities.

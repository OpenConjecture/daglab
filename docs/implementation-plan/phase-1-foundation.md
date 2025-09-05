# Phase 1: Foundation & Core Infrastructure

**Duration**: 1-2 weeks  
**Dependencies**: None (starting phase)  
**Prerequisites**: Python 3.10+ development environment

## Overview

Phase 1 establishes the foundational infrastructure for the `daglab` project. This phase focuses on creating a solid, well-structured codebase with proper Python packaging, configuration management, and core utilities that will support all subsequent development.

## Goals

1. **Project Structure**: Create a clean, maintainable Python package structure
2. **Configuration System**: Implement robust configuration management with override hierarchy
3. **Core Utilities**: Build essential utilities for logging, error handling, and validation
4. **CLI Framework**: Set up the basic CLI infrastructure using Typer
5. **Development Environment**: Establish tooling for development, testing, and quality assurance

## Detailed Implementation Plan

### 1.1 Project Structure Setup

**Files to Create**:
```
daglab/
├── __init__.py
├── cli.py                    # Main CLI entry point
├── config.py                 # Configuration management
├── runtime/
│   ├── __init__.py
│   ├── logging.py           # Structured logging
│   ├── errors.py            # Custom exceptions
│   └── telemetry.py         # Telemetry client (basic)
├── helpers/
│   ├── __init__.py
│   ├── validation.py        # Input validation utilities
│   └── security.py          # Security utilities
└── templates/
    └── __init__.py

tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_logging.py
│   └── test_validation.py
└── fixtures/
    └── sample_configs/

pyproject.toml
README.md
.gitignore
.pre-commit-config.yaml
```

**Implementation Tasks**:

1. **Create `pyproject.toml`**:
   - Define project metadata and dependencies
   - Set up build system configuration
   - Configure development tools (mypy, ruff, pytest)
   - Define console script entry point

2. **Set up package structure**:
   - Create all necessary `__init__.py` files
   - Define package-level exports
   - Set up proper import structure

3. **Configure development tools**:
   - Set up pre-commit hooks
   - Configure mypy for strict type checking
   - Set up ruff for linting and formatting
   - Configure pytest for testing

### 1.2 Configuration Management System

**File**: `daglab/config.py`

**Key Components**:

1. **Configuration Schema** (using Pydantic):
   ```python
   class daglabConfig(BaseModel):
       version: str = "1.0"
       notebooks_dir: Path = Path("dagster/notebooks")
       dagster: DagsterConfig
       marimo: MarimoConfig
       defaults: DefaultsConfig
       performance: PerformanceConfig
       export: ExportConfig
       logging: LoggingConfig
       telemetry: TelemetryConfig
       security: SecurityConfig
   ```

2. **Configuration Loading**:
   - Implement override hierarchy (CLI → ENV → config file → defaults)
   - Support for multiple config file locations
   - Environment variable mapping (`daglab_*` prefix)
   - Validation and error reporting

3. **Default Configuration**:
   - Sensible defaults for all settings
   - Environment-specific defaults
   - Validation rules and constraints

**Implementation Tasks**:

1. **Create Pydantic models** for all configuration sections
2. **Implement configuration loader** with override hierarchy
3. **Add validation** for configuration values
4. **Create default configuration** templates
5. **Add configuration testing** with various scenarios

### 1.3 Core Utilities

**File**: `daglab/runtime/logging.py`

**Logging System**:
- Structured logging with JSON format option
- Log rotation and file management
- Configurable log levels and destinations
- Performance logging utilities
- Security-conscious logging (no secrets)

**File**: `daglab/runtime/errors.py`

**Error Handling**:
- Custom exception hierarchy
- Error codes and exit status mapping
- Human-readable error messages with remediation
- Error context and debugging information
- Graceful degradation patterns

**File**: `daglab/helpers/validation.py`

**Validation Utilities**:
- Input sanitization for security
- YAML configuration validation
- File path validation
- Network endpoint validation
- Schema validation helpers

**File**: `daglab/helpers/security.py`

**Security Utilities**:
- Input sanitization functions
- Path traversal prevention
- Command injection prevention
- Safe file operations
- Environment variable handling

### 1.4 Basic CLI Framework

**File**: `daglab/cli.py`

**CLI Structure**:
```python
import typer
from rich.console import Console

app = typer.Typer(
    name="daglab",
    help="Scaffold and run paired marimo notebooks for Dagster assets & jobs.",
    rich_markup_mode="rich"
)

# Basic command structure (implementations in later phases)
@app.command()
def init():
    """Initialize daglab in current or new Dagster project."""
    pass

@app.command()
def doctor():
    """Run diagnostics and dependency checks."""
    pass

@app.command()
def clean():
    """Clean up artifacts and temporary files."""
    pass
```

**Implementation Tasks**:

1. **Set up Typer application** with proper configuration
2. **Implement basic command structure** (stubs for now)
3. **Add help text and documentation** for all commands
4. **Set up Rich console** for beautiful output
5. **Add error handling** and exit code management
6. **Implement configuration loading** in CLI context

### 1.5 Development Environment

**Tooling Setup**:

1. **Pre-commit hooks**:
   - Code formatting (ruff)
   - Import sorting (ruff)
   - Type checking (mypy)
   - Security scanning (bandit)
   - Commit message linting

2. **Testing framework**:
   - pytest configuration
   - Test discovery and execution
   - Coverage reporting
   - Fixture management

3. **Development dependencies**:
   - All necessary dev tools
   - Version pinning for stability
   - Optional dependencies for cloud features

## Acceptance Criteria

### Functional Requirements

- [ ] `pip install -e .` installs the package in development mode
- [ ] `daglab --help` shows proper help text
- [ ] Configuration system loads and validates properly
- [ ] Logging system works with different levels and formats
- [ ] Error handling provides clear, actionable messages
- [ ] All development tools (mypy, ruff, pytest) run successfully

### Code Quality Requirements

- [ ] All code passes mypy strict type checking
- [ ] All code passes ruff linting and formatting
- [ ] Test coverage is >80% for core utilities
- [ ] All functions and classes have proper docstrings
- [ ] Error messages include remediation steps

### Documentation Requirements

- [ ] README.md explains project setup and development workflow
- [ ] All public APIs are documented
- [ ] Configuration options are documented with examples
- [ ] Development setup instructions are clear and complete

## Testing Strategy

### Unit Tests

1. **Configuration Tests**:
   - Test configuration loading with various scenarios
   - Test override hierarchy behavior
   - Test validation and error handling
   - Test environment variable mapping

2. **Utility Tests**:
   - Test logging functionality
   - Test error handling and exception behavior
   - Test validation functions
   - Test security utilities

3. **CLI Tests**:
   - Test basic CLI structure
   - Test help text generation
   - Test error handling and exit codes

### Integration Tests

1. **End-to-end CLI tests**:
   - Test package installation
   - Test basic command execution
   - Test configuration file handling

## Deliverables

1. **Complete project structure** with all necessary files
2. **Working configuration system** with validation
3. **Core utilities** for logging, errors, and validation
4. **Basic CLI framework** with command structure
5. **Development environment** with all tooling configured
6. **Test suite** with good coverage
7. **Documentation** for setup and development

## Risk Mitigation

1. **Configuration Complexity**: Start with simple configuration and add complexity incrementally
2. **Tool Integration**: Test all development tools early and often
3. **Type Safety**: Use mypy strict mode from the beginning to catch issues early
4. **Documentation**: Keep documentation in sync with implementation

## Success Metrics

- Development environment can be set up in <10 minutes
- All tests pass consistently
- Code quality tools run without warnings
- Configuration system handles edge cases gracefully
- CLI provides helpful error messages and guidance

## Next Phase Preparation

Phase 1 sets up the foundation for Phase 2 by providing:
- Stable configuration system for CLI commands
- Error handling framework for user-facing commands
- Logging system for debugging and monitoring
- Security utilities for safe operations
- Testing framework for validation

The CLI framework established in Phase 1 will be extended in Phase 2 with actual command implementations.

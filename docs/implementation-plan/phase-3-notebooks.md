# Phase 3: Notebook Generation & Templates

**Duration**: 2-3 weeks  
**Dependencies**: Phase 2 (CLI Framework & Basic Commands)  
**Prerequisites**: Working CLI framework, configuration system, and project initialization

## Overview

Phase 3 implements the core notebook generation system that creates marimo notebooks from Jinja2 templates. This phase focuses on the `daglab scaffold` command and the template engine that generates functional marimo notebooks for Dagster assets and jobs.

## Goals

1. **Template System**: Build robust Jinja2-based template engine for marimo notebooks
2. **Notebook Generation**: Implement `daglab scaffold` command with comprehensive options
3. **Template Library**: Create multiple notebook templates (default, minimal, ML)
4. **Validation System**: Add notebook validation and testing capabilities
5. **User Experience**: Ensure generated notebooks are functional and well-documented

## Detailed Implementation Plan

### 3.1 Template Engine Foundation

**File**: `daglab/templates/engine.py`

**Template Engine Components**:

1. **Template Loader**:
   ```python
   class TemplateEngine:
       def __init__(self, template_dir: Path):
           self.template_dir = template_dir
           self.jinja_env = self._setup_jinja_environment()
       
       def render_notebook(
           self,
           template_name: str,
           context: Dict[str, Any],
           output_path: Path
       ) -> Path:
           """Render notebook from template with context."""
   ```

2. **Template Context Builder**:
   ```python
   class TemplateContext:
       def __init__(self, config: daglabConfig):
           self.config = config
           self.metadata = self._build_metadata()
       
       def build_context(
           self,
           target_type: str,
           target_name: str,
           options: Dict[str, Any]
       ) -> Dict[str, Any]:
           """Build template context from target and options."""
   ```

**Implementation Tasks**:

1. **Set up Jinja2 environment** with custom filters and functions
2. **Create template loading system** with fallback mechanisms
3. **Implement context building** with validation
4. **Add template caching** for performance
5. **Create template validation** system

### 3.2 Notebook Templates

**Directory**: `daglab/templates/notebooks/`

**Template Structure**:

1. **Default Template** (`notebook_default.py.j2`):
   - Complete marimo notebook with all features
   - State management across cells
   - GraphQL connection and authentication
   - Run controls and validation
   - Performance monitoring
   - Export and attachment capabilities

2. **Minimal Template** (`notebook_minimal.py.j2`):
   - Simplified notebook for quick exploration
   - Basic GraphQL connection
   - Simple run controls
   - Minimal state management

3. **ML Template** (`notebook_ml.py.j2`):
   - Specialized for machine learning workflows
   - Data visualization components
   - Model training and evaluation
   - Experiment tracking integration

**Template Components**:

1. **Metadata Cell**:
   ```python
   # Notebook Metadata
   NOTEBOOK_VERSION = "{{ notebook_version }}"
   NOTEBOOK_AUTHOR = "{{ author }}"
   NOTEBOOK_CREATED = "{{ created_date }}"
   NOTEBOOK_TARGET = "{{ target_type }}:{{ target_name }}"
   NOTEBOOK_TEMPLATE = "{{ template_name }}"
   ```

2. **Imports and Setup**:
   ```python
   import marimo as mo
   from daglab.helpers import (
       run_job, discover, attach_metadata, run_inprocess,
       validate_config, track_performance, manage_state
   )
   
   app = mo.App()
   ```

3. **State Management**:
   ```python
   # Persistent state across cells
   state = manage_state({
       'run_ids': [],
       'last_config': None,
       'performance_metrics': {},
       'error_log': []
   })
   ```

4. **Connection and Authentication**:
   ```python
   # Dagster connection configuration
   connection_config = {
       'host': '{{ dagster_host }}',
       'port': {{ dagster_port }},
       'repository': '{{ repository_name }}',
       'location': '{{ location_name }}',
       'auth': {{ auth_config | tojson }}
   }
   ```

**Implementation Tasks**:

1. **Create base template structure** with all required cells
2. **Implement template inheritance** for different variants
3. **Add template variables** and conditional sections
4. **Create template validation** and testing
5. **Add template documentation** and examples

### 3.3 Scaffold Command Implementation

**File**: `daglab/commands/scaffold.py`

**Command Features**:

1. **Target Discovery**:
   - Support for jobs, assets, and asset groups
   - Integration with Dagster discovery (when available)
   - Validation of target existence

2. **Template Selection**:
   - Automatic template selection based on target type
   - Custom template support
   - Template validation

3. **Context Generation**:
   - Build template context from target and options
   - Handle configuration overrides
   - Validate template variables

4. **File Generation**:
   - Generate notebook file with proper naming
   - Handle file conflicts and overwrites
   - Create necessary directories

**Command Interface**:
```python
@app.command()
def scaffold(
    # Target selection (mutually exclusive)
    job: Optional[str] = typer.Option(None, "--job", help="Target job name"),
    asset: Optional[str] = typer.Option(None, "--asset", help="Target asset name"),
    from_selection: Optional[str] = typer.Option(None, "--from-selection", help="Asset selection pattern"),
    
    # Template options
    template: str = typer.Option("default", "--template", help="Template to use"),
    filename: Optional[str] = typer.Option(None, "--filename", help="Output filename"),
    title: Optional[str] = typer.Option(None, "--title", help="Notebook title"),
    
    # Feature flags
    no_inprocess: bool = typer.Option(False, "--no-inprocess", help="Omit in-process execution cells"),
    no_attach: bool = typer.Option(False, "--no-attach", help="Omit metadata attachment cells"),
    
    # Validation and options
    validate_config: bool = typer.Option(True, "--validate-config", help="Pre-validate configuration"),
    seed_data: bool = typer.Option(False, "--seed-data", help="Include sample data"),
    git_commit: bool = typer.Option(False, "--git-commit", help="Auto-commit generated notebook"),
    
    # Template variables
    template_vars: Optional[str] = typer.Option(None, "--template-vars", help="Custom template variables (key=value,key2=value2)"),
    
    # Output options
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Generate a paired marimo notebook for a job or asset."""
```

**Implementation Tasks**:

1. **Target Validation**:
   - Validate target selection arguments
   - Check target existence (when possible)
   - Handle target discovery errors

2. **Template Processing**:
   - Load and validate template
   - Build template context
   - Render notebook content

3. **File Generation**:
   - Generate appropriate filename
   - Create output directory if needed
   - Handle file conflicts

4. **Post-generation**:
   - Validate generated notebook
   - Optionally commit to git
   - Provide user feedback

### 3.4 Template Context System

**File**: `daglab/templates/context.py`

**Context Building**:

1. **Metadata Context**:
   ```python
   def build_metadata_context(
       target_type: str,
       target_name: str,
       options: Dict[str, Any]
   ) -> Dict[str, Any]:
       return {
           'notebook_version': '1.0.0',
           'author': getpass.getuser(),
           'created_date': datetime.now().isoformat(),
           'target_type': target_type,
           'target_name': target_name,
           'template_name': options.get('template', 'default')
       }
   ```

2. **Configuration Context**:
   ```python
   def build_config_context(config: daglabConfig) -> Dict[str, Any]:
       return {
           'dagster_host': config.dagster.host,
           'dagster_port': config.dagster.port,
           'repository_name': config.dagster.repository_name,
           'location_name': config.dagster.repository_location_name,
           'auth_config': config.dagster.auth.dict(),
           'marimo_port': config.marimo.port
       }
   ```

3. **Target Context**:
   ```python
   def build_target_context(
       target_type: str,
       target_name: str,
       config: daglabConfig
   ) -> Dict[str, Any]:
       # Build context specific to target type
       # Include target-specific configuration
       # Add target metadata and options
   ```

**Implementation Tasks**:

1. **Context Building Logic**:
   - Implement context builders for different target types
   - Handle configuration overrides
   - Validate context completeness

2. **Template Variable Processing**:
   - Parse custom template variables
   - Validate variable types and values
   - Merge with default context

3. **Context Validation**:
   - Validate required context variables
   - Check for missing or invalid values
   - Provide helpful error messages

### 3.5 Notebook Validation System

**File**: `daglab/validation/notebook.py`

**Validation Components**:

1. **Syntax Validation**:
   ```python
   def validate_python_syntax(notebook_content: str) -> ValidationResult:
       """Validate Python syntax of generated notebook."""
   
   def validate_marimo_structure(notebook_content: str) -> ValidationResult:
       """Validate marimo-specific structure and imports."""
   ```

2. **Template Validation**:
   ```python
   def validate_template_variables(
       template_content: str,
       context: Dict[str, Any]
   ) -> ValidationResult:
       """Validate that all template variables are provided."""
   ```

3. **Import Validation**:
   ```python
   def validate_imports(notebook_content: str) -> ValidationResult:
       """Validate that all imports are available."""
   ```

**Implementation Tasks**:

1. **Syntax Validation**:
   - Validate Python syntax
   - Check marimo-specific requirements
   - Validate import statements

2. **Template Validation**:
   - Check template variable completeness
   - Validate template structure
   - Test template rendering

3. **Integration Validation**:
   - Validate Dagster integration
   - Check configuration compatibility
   - Test helper function availability

### 3.6 Template Customization System

**File**: `daglab/templates/custom.py`

**Customization Features**:

1. **Custom Template Support**:
   - Load templates from user directories
   - Template inheritance and composition
   - Custom filter and function support

2. **Template Variables**:
   - Support for custom template variables
   - Variable validation and type checking
   - Default value handling

3. **Template Extensions**:
   - Plugin system for template extensions
   - Custom cell types and components
   - Integration with external tools

**Implementation Tasks**:

1. **Custom Template Loading**:
   - Support for user-defined templates
   - Template discovery and loading
   - Template validation

2. **Variable System**:
   - Custom variable parsing
   - Variable validation
   - Default value handling

3. **Extension System**:
   - Plugin architecture for templates
   - Custom filters and functions
   - Integration points

## Acceptance Criteria

### Functional Requirements

- [ ] `daglab scaffold` generates functional marimo notebooks
- [ ] Templates render correctly with all context variables
- [ ] Generated notebooks pass syntax and structure validation
- [ ] Multiple template types work correctly
- [ ] Custom template variables are supported
- [ ] File generation handles conflicts gracefully

### Template Requirements

- [ ] Default template includes all required cells
- [ ] Minimal template provides basic functionality
- [ ] ML template includes ML-specific features
- [ ] Templates are well-documented and maintainable
- [ ] Template inheritance works correctly

### User Experience Requirements

- [ ] Generated notebooks are immediately runnable
- [ ] Clear error messages for validation failures
- [ ] Helpful feedback during generation
- [ ] Generated notebooks include proper documentation

### Code Quality Requirements

- [ ] Template engine is well-tested
- [ ] Generated notebooks are consistent
- [ ] Validation system catches common issues
- [ ] Code is well-documented and maintainable

## Testing Strategy

### Unit Tests

1. **Template Engine Tests**:
   - Test template loading and rendering
   - Test context building
   - Test template validation
   - Test error handling

2. **Template Tests**:
   - Test each template type
   - Test template inheritance
   - Test variable substitution
   - Test conditional sections

3. **Validation Tests**:
   - Test syntax validation
   - Test template validation
   - Test import validation
   - Test error scenarios

### Integration Tests

1. **End-to-End Generation**:
   - Test complete scaffold workflow
   - Test with different target types
   - Test with various options
   - Test error scenarios

2. **Generated Notebook Tests**:
   - Test that generated notebooks are valid
   - Test that notebooks can be imported
   - Test that notebooks have correct structure
   - Test that notebooks include expected content

### Template Tests

1. **Template Validation**:
   - Test template syntax
   - Test template structure
   - Test variable completeness
   - Test rendering with sample data

2. **Generated Content Tests**:
   - Test generated notebook content
   - Test cell structure and organization
   - Test import statements
   - Test functionality

## Deliverables

1. **Complete template engine** with Jinja2 integration
2. **Three notebook templates** (default, minimal, ML)
3. **Working `daglab scaffold` command** with all options
4. **Template context system** with validation
5. **Notebook validation system** with comprehensive checks
6. **Template customization system** for user extensions
7. **Comprehensive test suite** for all components
8. **Template documentation** and examples

## Risk Mitigation

1. **Template Complexity**: Start with simple templates and add complexity incrementally
2. **Validation Coverage**: Implement comprehensive validation to catch issues early
3. **User Experience**: Test generated notebooks with real users
4. **Maintenance**: Keep templates simple and well-documented

## Success Metrics

- Generated notebooks are immediately functional
- Templates are easy to understand and modify
- Validation catches common issues
- Users can customize templates easily
- Generated notebooks follow best practices

## Next Phase Preparation

Phase 3 sets up the notebook generation system for Phase 4 by providing:
- Template system for Dagster integration
- Generated notebooks with GraphQL client setup
- Validation system for notebook quality
- User experience patterns for interactive operations

The notebook generation system established in Phase 3 will be enhanced in Phase 4 with actual Dagster integration capabilities.

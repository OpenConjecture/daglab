# daglab Configuration Guide

This guide explains how to configure daglab for your specific needs.

## Configuration Overview

daglab uses a hierarchical configuration system with the following override priority (highest to lowest):

1. **CLI arguments** - Command-line flags and options
2. **Environment variables** - Variables with `daglab_` prefix
3. **Configuration files** - YAML configuration files
4. **Default values** - Built-in defaults

## Configuration File Locations

daglab searches for configuration files in the following locations (in order):

1. `./daglab.yaml` or `./daglab.yml` (current directory)
2. `./.daglab.yaml` or `./.daglab.yml` (hidden file in current directory)
3. `~/.config/daglab/config.yaml` (user config directory)
4. `~/.daglab/config.yaml` (user home directory)

The first file found is used. You can also specify a custom configuration file using the `--config` flag.

## Configuration Structure

### Basic Configuration

```yaml
version: "1.0"
notebooks_dir: "dagster/notebooks"
```

### Complete Configuration

See [config/daglab.template.yaml](../config/daglab.template.yaml) for a complete example with all available options.

## Environment Variables

Any configuration option can be overridden using environment variables with the `daglab_` prefix:

- Simple values: `daglab_version=2.0`
- Nested values: `daglab_dagster__assets_module=my_assets` (use double underscore for nesting)
- Lists: Not supported via environment variables (use config file or CLI)

### Examples

```bash
# Set notebooks directory
export daglab_notebooks_dir=/custom/notebooks

# Set Dagster project directory
export daglab_dagster__project_dir=/my/dagster/project

# Set log level
export daglab_logging__level=DEBUG

# Set marimo port range
export daglab_marimo__port_range_start=3000
```

## Configuration Sections

### Core Settings

- `version`: Configuration version (currently "1.0")
- `notebooks_dir`: Directory where marimo notebooks are created

### Dagster Configuration

```yaml
dagster:
  project_dir: "."              # Dagster project directory
  module_name: null             # Auto-detected if not specified
  repository_name: null         # Auto-detected if not specified
  assets_module: "assets"       # Module containing assets
  jobs_module: "jobs"           # Module containing jobs
```

### Marimo Configuration

```yaml
marimo:
  port_range_start: 2718        # Starting port for servers
  port_range_end: 2818          # Ending port for servers
  auto_reload: true             # Auto-reload on changes
  theme: "light"                # UI theme (light/dark)
  layout_file: null             # Custom layout config
```

### Default Values

```yaml
defaults:
  author: "Your Name"           # Default author
  email: "email@example.com"    # Default email
  license: "MIT"                # Default license
  python_version: "3.10"        # Python version
  tags:                         # Default tags
    - "data-pipeline"
    - "analytics"
```

### Performance Settings

```yaml
performance:
  max_workers: 4                # Parallel workers
  timeout: 300                  # Operation timeout (seconds)
  cache_enabled: true           # Enable caching
  cache_dir: "~/.cache/daglab"  # Cache directory
```

### Export Configuration

```yaml
export:
  formats:                      # Export formats
    - "python"
    - "html"
    - "markdown"
  output_dir: "./exports"       # Output directory
  include_metadata: true        # Include metadata
  minify: false                 # Minify code
```

### Logging Configuration

```yaml
logging:
  level: "INFO"                 # Log level
  file: null                    # Log file (null for stdout)
  format: "%(asctime)s..."      # Log format
  json_format: false            # Use JSON logging
  rotation: "10MB"              # Log rotation
  retention: 7                  # Logs to keep
```

### Security Configuration

```yaml
security:
  sandbox_enabled: true         # Enable sandboxing
  allowed_imports:              # Allowed imports
    - "dagster"
    - "marimo"
    - "pandas"
    - "numpy"
  restricted_paths: []          # Restricted paths
  validate_inputs: true         # Input validation
  max_file_size: 104857600      # Max file size (bytes)
```

## Usage Examples

### Loading Configuration in Code

```python
from daglab.config import get_config, load_config

# Get current configuration
config = get_config()

# Load with CLI overrides
config = load_config(cli_overrides={
    "logging": {"level": "DEBUG"}
})

# Load from specific file
config = load_config(config_path=Path("custom.yaml"))
```

### Accessing Configuration Values

```python
config = get_config()

# Access nested values
notebooks_dir = config.notebooks_dir
dagster_module = config.dagster.assets_module
log_level = config.logging.level

# Check features
if config.performance.cache_enabled:
    cache_dir = config.performance.cache_dir
    
if config.security.sandbox_enabled:
    allowed = config.security.allowed_imports
```

## Best Practices

1. **Development vs Production**: Use different configuration files for different environments
2. **Security**: Never commit sensitive values to configuration files; use environment variables
3. **Validation**: The configuration system validates all values on load
4. **Defaults**: Rely on sensible defaults; only override what you need
5. **Documentation**: Document any custom configuration in your project

## Troubleshooting

### Configuration Not Loading

1. Check file locations and permissions
2. Validate YAML syntax
3. Check environment variable names (remember the `daglab_` prefix)

### Invalid Configuration

1. Check error messages for specific validation issues
2. Ensure numeric values are within valid ranges
3. Check enum values are valid (e.g., log levels)

### Environment Variable Issues

1. Use double underscores for nested values
2. Remember the `daglab_` prefix
3. Check variable names are lowercase

## Migration Guide

If upgrading from a previous version:

1. Check the `version` field in your configuration
2. Review breaking changes in the changelog
3. Update configuration structure as needed
4. Test thoroughly in a development environment
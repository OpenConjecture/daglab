"""Example demonstrating daglab configuration usage."""

from pathlib import Path

from daglab.config import (
    DaglabConfig,
    ExportFormat,
    LogLevel,
    get_config,
    load_config,
    save_config,
)


def main():
    """Demonstrate various configuration usage patterns."""
    
    # Example 1: Load default configuration
    print("=== Example 1: Default Configuration ===")
    config = get_config()
    print(f"Version: {config.version}")
    print(f"Notebooks directory: {config.notebooks_dir}")
    print(f"Dagster assets module: {config.dagster.assets_module}")
    print(f"Marimo port range: {config.marimo.port_range_start}-{config.marimo.port_range_end}")
    print()
    
    # Example 2: Load configuration with CLI overrides
    print("=== Example 2: Configuration with CLI Overrides ===")
    cli_overrides = {
        "notebooks_dir": "/custom/notebooks",
        "logging": {
            "level": "DEBUG"
        },
        "performance": {
            "max_workers": 8
        }
    }
    config = load_config(cli_overrides=cli_overrides)
    print(f"Notebooks directory: {config.notebooks_dir}")
    print(f"Log level: {config.logging.level}")
    print(f"Max workers: {config.performance.max_workers}")
    print()
    
    # Example 3: Create custom configuration
    print("=== Example 3: Custom Configuration ===")
    custom_config = DaglabConfig(
        version="1.1",
        notebooks_dir=Path("./my_notebooks"),
        dagster={
            "project_dir": Path("./my_project"),
            "assets_module": "custom_assets"
        },
        marimo={
            "port_range_start": 3000,
            "port_range_end": 3100,
            "theme": "dark"
        },
        logging={
            "level": LogLevel.DEBUG,
            "json_format": True
        },
        export={
            "formats": [ExportFormat.PYTHON, ExportFormat.MARKDOWN],
            "minify": True
        }
    )
    print(f"Custom notebooks dir: {custom_config.notebooks_dir}")
    print(f"Custom Dagster project: {custom_config.dagster.project_dir}")
    print(f"Custom Marimo theme: {custom_config.marimo.theme}")
    print(f"Export formats: {[f.value for f in custom_config.export.formats]}")
    print()
    
    # Example 4: Save configuration to file
    print("=== Example 4: Save Configuration ===")
    output_path = Path("./example_config.yaml")
    save_config(custom_config, output_path, comments=True)
    print(f"Configuration saved to: {output_path}")
    print()
    
    # Example 5: Access nested configuration
    print("=== Example 5: Accessing Configuration Values ===")
    config = get_config()
    
    # Check if caching is enabled
    if config.performance.cache_enabled:
        print(f"Cache directory: {config.performance.cache_dir}")
    
    # Check telemetry settings
    if config.telemetry.enabled:
        print(f"Telemetry level: {config.telemetry.level}")
    else:
        print("Telemetry is disabled")
    
    # Check security settings
    print(f"Allowed imports: {', '.join(config.security.allowed_imports)}")
    print(f"Max file size: {config.security.max_file_size / (1024*1024):.1f} MB")
    print()
    
    # Example 6: Environment variable override
    print("=== Example 6: Environment Variables ===")
    print("Set environment variables to override configuration:")
    print("  export daglab_version=2.0")
    print("  export daglab_notebooks_dir=/env/notebooks")
    print("  export daglab_dagster__assets_module=env_assets")
    print("  export daglab_logging__level=DEBUG")
    print()
    
    # Clean up
    if output_path.exists():
        output_path.unlink()
        print(f"Cleaned up: {output_path}")


if __name__ == "__main__":
    main()
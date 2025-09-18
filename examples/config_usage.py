"""
Example usage of DagLab configuration system.
"""

import os
from pathlib import Path
from daglab.config import (
    DaglabConfig, 
    ConfigLoader, 
    get_config, 
    reload_config,
    LogLevel,
    SecurityMode
)


def basic_usage():
    """Basic configuration usage examples."""
    print("=== Basic Configuration Usage ===\n")
    
    # 1. Load default configuration
    config = get_config()
    print(f"Project: {config.project_name}")
    print(f"Version: {config.version}")
    print(f"Environment: {config.environment}")
    print(f"Debug mode: {config.debug}")
    print()
    
    # 2. Access sub-configurations
    print("Dagster config:")
    print(f"  Repository: {config.dagster.repository_name}")
    print(f"  Job name: {config.dagster.job_name}")
    print()
    
    print("Marimo config:")
    print(f"  Host: {config.marimo.host}")
    print(f"  Port: {config.marimo.port}")
    print(f"  Theme: {config.marimo.theme}")
    print()


def env_var_override():
    """Demonstrate environment variable overrides."""
    print("=== Environment Variable Overrides ===\n")
    
    # Set environment variables
    os.environ["DAGLAB_PROJECT_NAME"] = "my_project"
    os.environ["DAGLAB_DEBUG"] = "true"
    os.environ["DAGLAB_MARIMO__PORT"] = "8080"
    os.environ["DAGLAB_LOGGING__LEVEL"] = "debug"
    
    # Reload configuration to pick up env vars
    config = reload_config()
    
    print(f"Project name: {config.project_name}")
    print(f"Debug mode: {config.debug}")
    print(f"Marimo port: {config.marimo.port}")
    print(f"Log level: {config.logging.level}")
    print()
    
    # Clean up
    for key in ["DAGLAB_PROJECT_NAME", "DAGLAB_DEBUG", 
                "DAGLAB_MARIMO__PORT", "DAGLAB_LOGGING__LEVEL"]:
        if key in os.environ:
            del os.environ[key]


def file_operations():
    """Demonstrate loading and saving configuration files."""
    print("=== File Operations ===\n")
    
    # Create a custom configuration
    config = DaglabConfig(
        project_name="file_example",
        environment="production",
        debug=False,
        logging={"level": LogLevel.WARNING},
        security={"mode": SecurityMode.STRICT}
    )
    
    # Save to file
    config_path = Path("example_config.yaml")
    config.to_file(config_path)
    print(f"Configuration saved to: {config_path}")
    
    # Load from file
    loaded_config = DaglabConfig.from_file(config_path)
    print(f"Loaded project: {loaded_config.project_name}")
    print(f"Environment: {loaded_config.environment}")
    print(f"Security mode: {loaded_config.security.mode}")
    print()
    
    # Clean up
    config_path.unlink()


def config_loader_example():
    """Demonstrate ConfigLoader usage."""
    print("=== ConfigLoader Example ===\n")
    
    # Get configuration info
    info = ConfigLoader.get_config_info()
    print("Configuration info:")
    print(f"  Loaded from: {info['loaded_from']}")
    print(f"  Environment: {info['environment']}")
    print(f"  Debug: {info['debug']}")
    print(f"  Env vars: {len(info['env_vars'])} found")
    print()
    
    # Create development template
    dev_template_path = Path("daglab.dev.yaml")
    ConfigLoader.create_template(
        dev_template_path, 
        environment="development"
    )
    print(f"Development template created at: {dev_template_path}")
    
    # Create production template
    prod_template_path = Path("daglab.prod.yaml")
    ConfigLoader.create_template(
        prod_template_path,
        environment="production"
    )
    print(f"Production template created at: {prod_template_path}")
    print()
    
    # Clean up
    dev_template_path.unlink()
    prod_template_path.unlink()


def programmatic_config():
    """Demonstrate programmatic configuration."""
    print("=== Programmatic Configuration ===\n")
    
    # Create configuration with specific values
    config = DaglabConfig(
        project_name="my_dag_project",
        version="2.0.0",
        environment="staging",
        
        # Configure Dagster
        dagster={
            "repository_name": "my_repo",
            "storage": {
                "s3": {
                    "bucket": "my-dagster-bucket",
                    "prefix": "dagster/"
                }
            }
        },
        
        # Configure Marimo
        marimo={
            "port": 3000,
            "theme": "dark",
            "autosave_interval": 60
        },
        
        # Performance tuning
        performance={
            "cache_size": 2000,
            "memory_limit": "8G",
            "cpu_limit": 8
        }
    )
    
    print(f"Project: {config.project_name} v{config.version}")
    print(f"Environment: {config.environment}")
    print(f"Dagster S3 bucket: {config.dagster.storage['s3']['bucket']}")
    print(f"Marimo port: {config.marimo.port}")
    print(f"Memory limit: {config.performance.memory_limit}")
    print()


def merge_configurations():
    """Demonstrate configuration merging."""
    print("=== Configuration Merging ===\n")
    
    # Start with base configuration
    base_config = get_config()
    print(f"Base project name: {base_config.project_name}")
    print(f"Base log level: {base_config.logging.level}")
    
    # Define updates
    updates = {
        "project_name": "merged_project",
        "logging": {
            "level": "debug",
            "structured": True
        },
        "performance": {
            "cache_enabled": False
        }
    }
    
    # Merge configurations
    merged = base_config.merge(updates)
    print(f"Merged project name: {merged.project_name}")
    print(f"Merged log level: {merged.logging.level}")
    print(f"Merged structured logging: {merged.logging.structured}")
    print(f"Merged cache enabled: {merged.performance.cache_enabled}")
    print()


def validation_examples():
    """Demonstrate configuration validation."""
    print("=== Configuration Validation ===\n")
    
    # Valid configuration
    try:
        config = DaglabConfig(
            environment="production",
            marimo={"port": 8080}
        )
        print("✓ Valid configuration created")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Invalid port number
    try:
        config = DaglabConfig(
            marimo={"port": 99999}  # Too high
        )
    except Exception as e:
        print(f"✓ Port validation caught error: {type(e).__name__}")
    
    # Invalid environment
    try:
        config = DaglabConfig(
            environment="invalid_env"
        )
    except Exception as e:
        print(f"✓ Environment validation caught error: {type(e).__name__}")
    
    # Invalid memory limit format
    try:
        from daglab.config import PerformanceConfig
        perf = PerformanceConfig(memory_limit="invalid")
    except Exception as e:
        print(f"✓ Memory limit validation caught error: {type(e).__name__}")
    
    print()


if __name__ == "__main__":
    # Run all examples
    basic_usage()
    env_var_override()
    file_operations()
    config_loader_example()
    programmatic_config()
    merge_configurations()
    validation_examples()
    
    print("=== All examples completed! ===")
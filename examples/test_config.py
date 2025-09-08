#!/usr/bin/env python3
"""Test script to verify configuration system works correctly."""

import os
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from daglab.config import load_config, save_config, get_config, DaglabConfig


def test_basic_config():
    """Test basic configuration loading."""
    print("=== Test 1: Basic Configuration ===")
    config = get_config()
    print(f"Version: {config.version}")
    print(f"Notebooks directory: {config.notebooks_dir}")
    print(f"Log level: {config.logging.level}")
    print()


def test_env_override():
    """Test environment variable override."""
    print("=== Test 2: Environment Variable Override ===")
    
    # Set some environment variables
    os.environ["daglab_version"] = "2.0"
    os.environ["daglab_logging__level"] = "DEBUG"
    
    # Load config (should pick up env vars)
    config = DaglabConfig()
    print(f"Version from env: {config.version}")
    print(f"Log level from env: {config.logging.level}")
    
    # Clean up
    del os.environ["daglab_version"]
    del os.environ["daglab_logging__level"]
    print()


def test_config_file():
    """Test configuration file loading."""
    print("=== Test 3: Configuration File ===")
    
    # Create a temporary config file
    test_config = Path("test_daglab.yaml")
    test_config_data = """
version: "1.5"
notebooks_dir: "custom/notebooks"
dagster:
  assets_module: "my_assets"
logging:
  level: "WARNING"
"""
    test_config.write_text(test_config_data)
    
    # Load config from file
    config = load_config(config_path=test_config)
    print(f"Version from file: {config.version}")
    print(f"Notebooks dir from file: {config.notebooks_dir}")
    print(f"Assets module from file: {config.dagster.assets_module}")
    print(f"Log level from file: {config.logging.level}")
    
    # Clean up
    test_config.unlink()
    print()


def test_override_hierarchy():
    """Test complete override hierarchy."""
    print("=== Test 4: Override Hierarchy ===")
    
    # Create config file
    test_config = Path("test_daglab.yaml")
    test_config_data = """
version: "1.0"
notebooks_dir: "from_file"
logging:
  level: "INFO"
"""
    test_config.write_text(test_config_data)
    
    # Set environment variable
    os.environ["daglab_notebooks_dir"] = "from_env"
    
    # CLI override
    cli_overrides = {"version": "3.0"}
    
    # Load with hierarchy
    config = load_config(config_path=test_config, cli_overrides=cli_overrides)
    
    print(f"Version: {config.version} (should be 3.0 from CLI)")
    print(f"Notebooks dir: {config.notebooks_dir} (should be from_env)")
    print(f"Log level: {config.logging.level} (should be INFO from file)")
    
    # Clean up
    test_config.unlink()
    del os.environ["daglab_notebooks_dir"]
    print()


def test_save_config():
    """Test saving configuration."""
    print("=== Test 5: Save Configuration ===")
    
    # Create a custom config
    config = DaglabConfig(
        version="1.2",
        notebooks_dir=Path("saved/notebooks"),
        logging={"level": "DEBUG", "json_format": True}
    )
    
    # Save it
    output_path = Path("saved_config.yaml")
    save_config(config, output_path, comments=True)
    
    print(f"Configuration saved to: {output_path}")
    print("\nSaved content:")
    print(output_path.read_text())
    
    # Clean up
    output_path.unlink()
    print()


if __name__ == "__main__":
    print("Testing daglab configuration system...\n")
    
    test_basic_config()
    test_env_override()
    test_config_file()
    test_override_hierarchy()
    test_save_config()
    
    print("All configuration tests completed successfully!")
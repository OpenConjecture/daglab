"""Integration tests for template generation with real GraphQL client."""

import os
import tempfile
import json
import pytest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from daglab.notebook.generator import NotebookGenerator
from daglab.helpers.graphql import DagsterClientSync
from daglab.helpers.auth import AuthConfig


class TestTemplateIntegration:
    """Test template generation with real Dagster integration."""
    
    @pytest.fixture
    def template_dir(self):
        """Get template directory."""
        return Path(__file__).parent.parent.parent / "src" / "daglab" / "templates"
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def generator(self, template_dir):
        """Create notebook generator."""
        return NotebookGenerator(template_dir=str(template_dir))
    
    @pytest.mark.integration
    def test_generate_minimal_notebook(self, generator, temp_output_dir):
        """Test generating minimal notebook with GraphQL client."""
        output_file = temp_output_dir / "test_minimal.py"
        
        context = {
            "title": "Test Minimal Notebook",
            "description": "Integration test notebook",
            "dagster_url": os.getenv("DAGSTER_URL", "http://localhost:3000"),
            "use_daglab_client": True,
            "auth_method": "env",
            "verify_ssl": True,
            "timeout": 30.0
        }
        
        # Generate notebook
        generator.generate_notebook(
            template_name="minimal",
            output_path=str(output_file),
            context=context
        )
        
        # Verify file was created
        assert output_file.exists()
        
        # Read and verify content
        content = output_file.read_text()
        
        # Check for key components
        assert "DagsterClientSync" in content
        assert "AuthConfig" in content
        assert "health_check()" in content
        assert "validate_graphql_query" in content
        assert "HTTP client" in content  # Fallback client
        
        # Check for proper auth handling
        assert "AuthConfig.from_env()" in content
        assert "DAGSTER_TOKEN" in content
        
        # Check for query validation
        assert "query ListJobs" in content
        assert "repositoriesOrError" in content
        
        print(f"✅ Generated minimal notebook: {output_file}")
    
    @pytest.mark.integration
    def test_generate_default_notebook(self, generator, temp_output_dir):
        """Test generating default notebook with full features."""
        output_file = temp_output_dir / "test_default.py"
        
        context = {
            "title": "Test Default Notebook",
            "description": "Full-featured integration test",
            "dagster_url": os.getenv("DAGSTER_URL", "http://localhost:3000"),
            "use_daglab_client": True,
            "rich_output": True,
            "show_repository_selector": True,
            "show_run_config": True,
            "show_tags": True,
            "add_metadata_tags": True,
            "track_in_state": True,
            "show_run_link": True,
            "auto_refresh": True
        }
        
        # Generate notebook
        generator.generate_notebook(
            template_name="default",
            output_path=str(output_file),
            context=context
        )
        
        # Verify file was created
        assert output_file.exists()
        
        content = output_file.read_text()
        
        # Check for advanced features
        assert "NotebookState" in content
        assert "state_manager" in content
        assert "Rich console" in content
        assert "repository_discovery" in content
        assert "pipeline_controls" in content
        assert "run_monitor" in content
        assert "data_visualization" in content
        
        # Check for real GraphQL queries
        assert "mutation LaunchJob" in content
        assert "launchPipelineExecution" in content
        assert "ExecutionParams" in content
        
        # Check for security validation
        assert "validate_run_config" in content
        assert "validate_tags" in content
        
        print(f"✅ Generated default notebook: {output_file}")
    
    @pytest.mark.integration
    def test_template_with_authentication(self, generator, temp_output_dir):
        """Test template with different authentication methods."""
        auth_methods = ["env", "bearer", "basic", "none"]
        
        for auth_method in auth_methods:
            output_file = temp_output_dir / f"test_auth_{auth_method}.py"
            
            context = {
                "title": f"Test {auth_method.title()} Auth",
                "auth_method": auth_method,
                "use_daglab_client": True
            }
            
            generator.generate_notebook(
                template_name="minimal",
                output_path=str(output_file),
                context=context
            )
            
            assert output_file.exists()
            content = output_file.read_text()
            
            if auth_method == "env":
                assert "AuthConfig.from_env()" in content
            elif auth_method == "bearer":
                assert "AuthConfig.bearer" in content
            elif auth_method == "basic":
                assert "AuthConfig.basic" in content
            else:
                assert "AuthType.NONE" in content
            
            print(f"✅ Generated {auth_method} auth notebook")
    
    @pytest.mark.integration
    def test_template_partials(self, template_dir):
        """Test that partials include real GraphQL functionality."""
        partials_dir = template_dir / "partials"
        
        # Test connection partial
        connection_partial = partials_dir / "_connection.j2"
        assert connection_partial.exists()
        content = connection_partial.read_text()
        assert "DagsterClient" in content
        assert "health_check" in content
        assert "GraphQL endpoint" in content
        
        # Test imports partial
        imports_partial = partials_dir / "_imports.j2"
        assert imports_partial.exists()
        content = imports_partial.read_text()
        assert "daglab.helpers.graphql" in content
        assert "DagsterClientSync" in content
        
        # Test run controls partial
        controls_partial = partials_dir / "_run_controls.j2"
        assert controls_partial.exists()
        content = controls_partial.read_text()
        assert "launchPipelineExecution" in content
        assert "ExecutionParams" in content
        assert "validate_run_config" in content
        
        print("✅ All partials contain real GraphQL integration")
    
    @pytest.mark.integration
    def test_error_handling_in_templates(self, generator, temp_output_dir):
        """Test that templates handle errors properly."""
        output_file = temp_output_dir / "test_error_handling.py"
        
        context = {
            "title": "Error Handling Test",
            "dagster_url": "http://invalid-host:9999",  # Invalid URL
            "use_daglab_client": True,
            "retry_enabled": True,
            "max_retries": 3,
            "show_errors": True
        }
        
        generator.generate_notebook(
            template_name="minimal",
            output_path=str(output_file),
            context=context
        )
        
        content = output_file.read_text()
        
        # Check for error handling
        assert "try:" in content
        assert "except Exception" in content
        assert "Connection error:" in content
        assert "fallback" in content.lower() or "HTTP client" in content
        
        print("✅ Templates include proper error handling")
    
    @pytest.mark.integration
    def test_template_with_real_connection(self, generator, temp_output_dir):
        """Test template can connect to real Dagster instance."""
        # Skip if no Dagster instance
        dagster_url = os.getenv("DAGSTER_URL")
        if not dagster_url:
            pytest.skip("No DAGSTER_URL set")
        
        # Test connection first
        try:
            auth_config = AuthConfig.from_env()
            client = DagsterClientSync(
                endpoint=f"{dagster_url}/graphql",
                auth_config=auth_config,
                timeout=10.0
            )
            if not client.health_check():
                pytest.skip("Dagster instance not healthy")
        except Exception:
            pytest.skip("Cannot connect to Dagster")
        
        # Generate notebook that will connect
        output_file = temp_output_dir / "test_real_connection.py"
        
        context = {
            "title": "Real Connection Test",
            "dagster_url": dagster_url,
            "use_daglab_client": True,
            "fetch_pipelines": True,
            "show_debug": True
        }
        
        generator.generate_notebook(
            template_name="default",
            output_path=str(output_file),
            context=context
        )
        
        content = output_file.read_text()
        
        # Verify it includes real queries
        assert "DiscoverRepositories" in content
        assert "GetJobsAndRepositories" in content
        assert "LaunchJob" in content
        
        print(f"✅ Generated notebook for real Dagster at {dagster_url}")
    
    @pytest.mark.integration
    def test_template_security_features(self, generator, temp_output_dir):
        """Test that templates include security features."""
        output_file = temp_output_dir / "test_security.py"
        
        context = {
            "title": "Security Test",
            "use_daglab_client": True,
            "validate_client": True,
            "strict_mode": True
        }
        
        generator.generate_notebook(
            template_name="default",
            output_path=str(output_file),
            context=context
        )
        
        content = output_file.read_text()
        
        # Check for security features
        assert "validate_graphql_query" in content
        assert "validate_run_config" in content
        assert "validate_tags" in content
        assert "sanitize" in content.lower() or "validation" in content
        
        # Check for auth token handling
        assert "Bearer" in content or "Authorization" in content
        assert "token" in content.lower()
        
        print("✅ Templates include security validation")
    
    @pytest.mark.integration
    def test_template_backward_compatibility(self, generator, temp_output_dir):
        """Test templates work without Daglab (fallback mode)."""
        output_file = temp_output_dir / "test_fallback.py"
        
        context = {
            "title": "Fallback Test",
            "use_daglab_client": True,  # Will fallback if not available
            "dagster_imports": True
        }
        
        generator.generate_notebook(
            template_name="minimal",
            output_path=str(output_file),
            context=context
        )
        
        content = output_file.read_text()
        
        # Check for fallback handling
        assert "DAGLAB_AVAILABLE" in content
        assert "ImportError" in content
        assert "fallback" in content.lower() or "HTTP client" in content
        assert "httpx" in content
        
        print("✅ Templates support fallback mode")
"""Tests for the run command."""

import pytest
from typer.testing import CliRunner
from pathlib import Path
import json
import yaml
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from src.daglab.commands.run import app, RunSubmitter, RunMonitor, ConfigManager

runner = CliRunner()


class TestRunSubmitter:
    """Test RunSubmitter class."""
    
    def test_submit_job(self):
        """Test job submission."""
        submitter = RunSubmitter()
        
        with patch('time.time', return_value=1234567890):
            run_id = submitter.submit_job(
                "test_job",
                {"ops": {"my_op": {"config": {"value": 42}}}},
                repo="my_repo",
                location="my_location",
                tags={"env": "test"}
            )
        
        assert run_id == "run_1234567890"
    
    def test_materialize_assets(self):
        """Test asset materialization submission."""
        submitter = RunSubmitter()
        
        with patch('time.time', return_value=1234567890):
            run_id = submitter.materialize_assets(
                ["asset1", "asset2", "asset3"],
                repo="my_repo",
                location="my_location",
                tags={"env": "prod"}
            )
        
        assert run_id == "run_1234567890"
    
    def test_expand_asset_pattern(self):
        """Test asset pattern expansion."""
        submitter = RunSubmitter()
        
        # Test wildcard pattern
        assets = submitter.expand_asset_pattern("orders/*")
        assert assets == ["orders_raw", "orders_cleaned", "orders_aggregated"]
        
        # Test non-pattern
        assets = submitter.expand_asset_pattern("single_asset")
        assert assets == ["single_asset"]
        
        # Test pattern with repo
        assets = submitter.expand_asset_pattern("analytics/*", repo="my_repo")
        assert assets == ["analytics_raw", "analytics_cleaned", "analytics_aggregated"]


class TestRunMonitor:
    """Test RunMonitor class."""
    
    @pytest.mark.asyncio
    async def test_monitor_run_success(self):
        """Test successful run monitoring."""
        monitor = RunMonitor()
        
        # Mock asyncio.sleep to speed up test
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await monitor.monitor_run("run_123")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_monitor_run_timeout(self):
        """Test run monitoring with timeout."""
        monitor = RunMonitor()
        
        # Mock time.time to simulate timeout
        start_time = 1000
        with patch('time.time') as mock_time:
            mock_time.side_effect = [start_time, start_time + 2, start_time + 2]
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await monitor.monitor_run("run_123", timeout=1, cancel_on_timeout=True)
        
        assert result is False
    
    def test_get_run_url(self):
        """Test run URL generation."""
        monitor = RunMonitor()
        
        # Default URL
        url = monitor.get_run_url("run_123")
        assert url == "http://localhost:3000/runs/run_123"
        
        # With env var
        with patch.dict('os.environ', {'DAGSTER_UI_URL': 'http://dagster.example.com'}):
            url = monitor.get_run_url("run_456")
            assert url == "http://dagster.example.com/runs/run_456"


class TestConfigManager:
    """Test ConfigManager class."""
    
    def test_load_yaml_config(self):
        """Test loading YAML configuration."""
        config_manager = ConfigManager()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
ops:
  process:
    config:
      batch_size: 100
      retry_count: 3
""")
            f.flush()
            
            config = config_manager.load_config(Path(f.name))
        
        assert config == {
            "ops": {
                "process": {
                    "config": {
                        "batch_size": 100,
                        "retry_count": 3
                    }
                }
            }
        }
    
    def test_load_json_config(self):
        """Test loading JSON configuration."""
        config_manager = ConfigManager()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"ops": {"process": {"config": {"batch_size": 50}}}}, f)
            f.flush()
            
            config = config_manager.load_config(Path(f.name))
        
        assert config == {"ops": {"process": {"config": {"batch_size": 50}}}}
    
    def test_env_var_substitution(self):
        """Test environment variable substitution."""
        config_manager = ConfigManager()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
database:
  host: ${DB_HOST:-localhost}
  port: ${DB_PORT:-5432}
  user: ${DB_USER}
""")
            f.flush()
            
            with patch.dict('os.environ', {'DB_HOST': 'prod.db.com', 'DB_USER': 'admin'}):
                config = config_manager.load_config(Path(f.name))
        
        assert config == {
            "database": {
                "host": "prod.db.com",
                "port": "5432",  # Default value
                "user": "admin"
            }
        }
    
    def test_parse_yaml_string(self):
        """Test parsing inline YAML."""
        config_manager = ConfigManager()
        
        yaml_str = "ops: {process: {config: {batch_size: 100}}}"
        config = config_manager.parse_yaml_string(yaml_str)
        
        assert config == {"ops": {"process": {"config": {"batch_size": 100}}}}
    
    def test_parse_invalid_yaml(self):
        """Test parsing invalid YAML raises error."""
        config_manager = ConfigManager()
        
        with pytest.raises(ValueError, match="Invalid YAML"):
            config_manager.parse_yaml_string("{invalid: yaml: }")


class TestRunCommand:
    """Test main run command."""
    
    def test_run_job_basic(self):
        """Test basic job run."""
        with patch.object(RunSubmitter, 'submit_job', return_value='run_123'):
            with patch.object(RunMonitor, 'monitor_run', new_callable=AsyncMock) as mock_monitor:
                mock_monitor.return_value = True
                
                result = runner.invoke(app, ["--job", "daily_etl", "--no-wait"])
        
        assert result.exit_code == 0
        assert "Submitted job 'daily_etl'" in result.stdout
    
    def test_run_assets_selection(self):
        """Test asset selection."""
        with patch.object(RunSubmitter, 'materialize_assets', return_value='run_123'):
            with patch.object(RunMonitor, 'monitor_run', new_callable=AsyncMock) as mock_monitor:
                mock_monitor.return_value = True
                
                result = runner.invoke(app, [
                    "--asset-selection", "asset1",
                    "--asset-selection", "asset2",
                    "--no-wait"
                ])
        
        assert result.exit_code == 0
        assert "Materializing 2 assets" in result.stdout
    
    def test_run_asset_pattern(self):
        """Test asset pattern expansion."""
        with patch.object(RunSubmitter, 'expand_asset_pattern', return_value=['orders_raw', 'orders_cleaned']):
            with patch.object(RunSubmitter, 'materialize_assets', return_value='run_123'):
                with patch.object(RunMonitor, 'monitor_run', new_callable=AsyncMock) as mock_monitor:
                    mock_monitor.return_value = True
                    
                    result = runner.invoke(app, ["--asset-pattern", "orders/*", "--no-wait"])
        
        assert result.exit_code == 0
        assert "Materializing 2 assets" in result.stdout
    
    def test_run_with_config_file(self):
        """Test run with configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("ops: {process: {config: {batch_size: 100}}}")
            f.flush()
            
            with patch.object(RunSubmitter, 'submit_job', return_value='run_123'):
                with patch.object(RunMonitor, 'monitor_run', new_callable=AsyncMock) as mock_monitor:
                    mock_monitor.return_value = True
                    
                    result = runner.invoke(app, [
                        "--job", "batch_job",
                        "--run-config", f.name,
                        "--no-wait"
                    ])
        
        assert result.exit_code == 0
        assert "Submitted job 'batch_job'" in result.stdout
    
    def test_run_with_inline_config(self):
        """Test run with inline YAML configuration."""
        with patch.object(RunSubmitter, 'submit_job', return_value='run_123'):
            with patch.object(RunMonitor, 'monitor_run', new_callable=AsyncMock) as mock_monitor:
                mock_monitor.return_value = True
                
                result = runner.invoke(app, [
                    "--job", "batch_job",
                    "--config-yaml", "ops: {process: {config: {batch_size: 50}}}",
                    "--no-wait"
                ])
        
        assert result.exit_code == 0
        assert "Submitted job 'batch_job'" in result.stdout
    
    def test_validate_only(self):
        """Test validation without execution."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("ops: {process: {config: {batch_size: 100}}}")
            f.flush()
            
            result = runner.invoke(app, [
                "--job", "test_job",
                "--run-config", f.name,
                "--validate-only"
            ])
        
        assert result.exit_code == 0
        assert "Configuration is valid" in result.stdout
    
    def test_run_with_tags(self):
        """Test run with tags."""
        with patch.object(RunSubmitter, 'submit_job', return_value='run_123') as mock_submit:
            with patch.object(RunMonitor, 'monitor_run', new_callable=AsyncMock) as mock_monitor:
                mock_monitor.return_value = True
                
                result = runner.invoke(app, [
                    "--job", "tagged_job",
                    "--tags", "env=prod,team=data",
                    "--no-wait"
                ])
        
        assert result.exit_code == 0
        # Check tags were parsed correctly
        _, call_kwargs = mock_submit.call_args
        assert call_kwargs['tags'] == {"env": "prod", "team": "data"}
    
    def test_json_output(self):
        """Test JSON output mode."""
        with patch.object(RunSubmitter, 'submit_job', return_value='run_123'):
            with patch.object(RunMonitor, 'monitor_run', new_callable=AsyncMock) as mock_monitor:
                mock_monitor.return_value = True
                
                result = runner.invoke(app, [
                    "--job", "test_job",
                    "--no-wait",
                    "--json"
                ])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["run_id"] == "run_123"
        assert output["status"] == "submitted"
    
    def test_error_no_entity_specified(self):
        """Test error when no entity is specified."""
        result = runner.invoke(app, [])
        
        assert result.exit_code == 1
        assert "Must specify either --job, --asset-selection, or --asset-pattern" in result.stdout
    
    def test_error_both_job_and_assets(self):
        """Test error when both job and assets are specified."""
        result = runner.invoke(app, ["--job", "test_job", "--asset-selection", "asset1"])
        
        assert result.exit_code == 1
        assert "Cannot specify both job and asset options" in result.stdout
    
    def test_error_cancel_without_timeout(self):
        """Test error when cancel-on-timeout is used without timeout."""
        result = runner.invoke(app, ["--job", "test_job", "--cancel-on-timeout"])
        
        assert result.exit_code == 1
        assert "--cancel-on-timeout requires --timeout" in result.stdout


class TestValidateCommand:
    """Test validate subcommand."""
    
    def test_validate_success(self):
        """Test successful validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("ops: {process: {config: {batch_size: 100}}}")
            f.flush()
            
            result = runner.invoke(app, [
                "validate",
                "--job", "test_job",
                "--run-config", f.name
            ])
        
        assert result.exit_code == 0
        assert "Configuration file is valid YAML/JSON" in result.stdout
        assert "Configuration is valid for job 'test_job'" in result.stdout
    
    def test_validate_missing_job(self):
        """Test validation error when job is missing."""
        result = runner.invoke(app, ["validate", "--run-config", "config.yaml"])
        
        assert result.exit_code == 1
        assert "--job is required for validation" in result.stdout
    
    def test_validate_missing_config(self):
        """Test validation error when config is missing."""
        result = runner.invoke(app, ["validate", "--job", "test_job"])
        
        assert result.exit_code == 1
        assert "--run-config is required for validation" in result.stdout


class TestListCommands:
    """Test list-assets and list-jobs commands."""
    
    def test_list_assets(self):
        """Test listing available assets."""
        result = runner.invoke(app, ["list-assets"])
        
        assert result.exit_code == 0
        assert "Available Assets" in result.stdout
        assert "raw_orders" in result.stdout
        assert "ingestion" in result.stdout
    
    def test_list_assets_with_pattern(self):
        """Test listing assets with pattern filter."""
        result = runner.invoke(app, ["list-assets", "--pattern", "raw*"])
        
        assert result.exit_code == 0
        assert "raw_orders" in result.stdout
        assert "raw_customers" in result.stdout
        assert "daily_revenue" not in result.stdout
    
    def test_list_assets_json(self):
        """Test listing assets in JSON format."""
        result = runner.invoke(app, ["list-assets", "--json"])
        
        assert result.exit_code == 0
        assets = json.loads(result.stdout)
        assert isinstance(assets, list)
        assert any(a["name"] == "raw_orders" for a in assets)
    
    def test_list_jobs(self):
        """Test listing available jobs."""
        result = runner.invoke(app, ["list-jobs"])
        
        assert result.exit_code == 0
        assert "Available Jobs" in result.stdout
        assert "daily_etl" in result.stdout
        assert "Daily ETL pipeline" in result.stdout
    
    def test_list_jobs_json(self):
        """Test listing jobs in JSON format."""
        result = runner.invoke(app, ["list-jobs", "--json"])
        
        assert result.exit_code == 0
        jobs = json.loads(result.stdout)
        assert isinstance(jobs, list)
        assert any(j["name"] == "daily_etl" for j in jobs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
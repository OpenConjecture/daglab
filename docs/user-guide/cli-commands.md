# CLI Commands Reference

This comprehensive guide covers all DagLab command-line interface (CLI) commands, their options, and usage examples.

## Command Overview

DagLab CLI provides a rich set of commands for managing workflows, monitoring executions, and administering the system. All commands follow the pattern:

```bash
daglab [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGUMENTS]
```

## Global Options

Available with all commands:

```bash
-c, --config PATH          # Configuration file path
-v, --verbose             # Verbose output
-q, --quiet               # Quiet mode (minimal output)
-h, --help                # Show help message
--version                 # Show version information
--log-level LEVEL         # Set log level (DEBUG, INFO, WARNING, ERROR)
--profile PROFILE         # Use specific configuration profile
```

## Core Commands

### `daglab init`

Initialize a new DagLab project or configuration.

```bash
# Create new project
daglab init my-project

# Initialize in current directory
daglab init .

# Initialize with template
daglab init my-project --template data-pipeline

# Initialize configuration only
daglab init-config
```

**Options:**
- `--template NAME` - Use project template
- `--config-only` - Create configuration only
- `--overwrite` - Overwrite existing files
- `--minimal` - Create minimal project structure

**Examples:**
```bash
# Create data science project
daglab init ml-pipeline --template data-science

# Initialize with PostgreSQL
daglab init web-app --template web --database postgresql

# Minimal setup
daglab init simple-dag --minimal
```

### `daglab run`

Execute DAGs and workflows.

```bash
# Run specific DAG
daglab run dags/my_workflow.yaml

# Run with specific configuration
daglab run dags/my_workflow.yaml --config config/production.yaml

# Run with parameters
daglab run dags/my_workflow.yaml --params '{"env": "prod", "date": "2024-01-01"}'

# Dry run (validate without executing)
daglab run dags/my_workflow.yaml --dry-run
```

**Options:**
- `--config PATH` - Configuration file
- `--params JSON` - DAG parameters as JSON
- `--dry-run` - Validate without executing
- `--wait` - Wait for completion
- `--timeout SECONDS` - Execution timeout
- `--force` - Force execution even if already running
- `--schedule CRON` - Override DAG schedule

**Examples:**
```bash
# Run with environment variables
daglab run dags/etl.yaml --params '{"db_host": "prod-db.company.com"}'

# Run and wait for completion
daglab run dags/data_processing.yaml --wait --timeout 3600

# Force run even if instance is running
daglab run dags/cleanup.yaml --force

# Dry run to validate
daglab run dags/new_pipeline.yaml --dry-run
```

### `daglab status`

Check status of DAGs and executions.

```bash
# Show all DAG statuses
daglab status

# Show specific DAG status
daglab status my_workflow

# Show detailed status
daglab status my_workflow --detailed

# Show recent runs
daglab status --recent 10
```

**Options:**
- `--detailed` - Show detailed information
- `--recent N` - Show N recent runs
- `--format FORMAT` - Output format (table, json, yaml)
- `--watch` - Watch for status changes
- `--filter STATE` - Filter by state (running, success, failed)

**Examples:**
```bash
# Watch status in real-time
daglab status my_workflow --watch

# Show failed runs only
daglab status --filter failed

# JSON output for automation
daglab status my_workflow --format json

# Recent runs with details
daglab status --recent 5 --detailed
```

### `daglab logs`

View and manage logs.

```bash
# Show logs for specific DAG
daglab logs my_workflow

# Show logs for specific run
daglab logs my_workflow --run-id 20240101_120000

# Show logs for specific task
daglab logs my_workflow --task-id extract_data

# Follow logs in real-time
daglab logs my_workflow --follow
```

**Options:**
- `--run-id ID` - Specific run ID
- `--task-id ID` - Specific task ID
- `--follow, -f` - Follow logs in real-time
- `--lines N` - Number of lines to show
- `--since TIME` - Show logs since timestamp
- `--level LEVEL` - Filter by log level
- `--format FORMAT` - Output format

**Examples:**
```bash
# Last 100 lines
daglab logs my_workflow --lines 100

# Logs since specific time
daglab logs my_workflow --since "2024-01-01 10:00:00"

# Error logs only
daglab logs my_workflow --level ERROR

# Follow logs with timestamp
daglab logs my_workflow --follow --format "%(asctime)s - %(message)s"
```

### `daglab list`

List DAGs, runs, and other objects.

```bash
# List all DAGs
daglab list dags

# List runs for specific DAG
daglab list runs my_workflow

# List tasks in DAG
daglab list tasks my_workflow

# List active runs
daglab list runs --state running
```

**Subcommands:**
- `dags` - List available DAGs
- `runs` - List DAG runs
- `tasks` - List tasks
- `schedules` - List scheduled DAGs
- `workers` - List active workers

**Options:**
- `--state STATE` - Filter by state
- `--limit N` - Limit results
- `--sort FIELD` - Sort by field
- `--format FORMAT` - Output format

**Examples:**
```bash
# List recent runs
daglab list runs --limit 20 --sort start_date

# List failed runs
daglab list runs --state failed

# List DAGs in JSON format
daglab list dags --format json

# List tasks for specific run
daglab list tasks my_workflow --run-id 20240101_120000
```

## DAG Management

### `daglab validate`

Validate DAG definitions and configurations.

```bash
# Validate specific DAG
daglab validate dags/my_workflow.yaml

# Validate all DAGs
daglab validate --all

# Validate configuration
daglab validate-config

# Validate with specific schema
daglab validate dags/my_workflow.yaml --schema custom_schema.json
```

**Options:**
- `--all` - Validate all DAGs
- `--schema PATH` - Custom validation schema
- `--strict` - Strict validation mode
- `--fix` - Attempt to fix issues automatically

**Examples:**
```bash
# Validate all DAGs in directory
daglab validate dags/ --all

# Strict validation with detailed output
daglab validate dags/complex_dag.yaml --strict --verbose

# Validate and fix common issues
daglab validate dags/my_dag.yaml --fix
```

### `daglab schedule`

Manage DAG scheduling.

```bash
# Schedule DAG
daglab schedule my_workflow --cron "0 8 * * *"

# Unschedule DAG
daglab schedule my_workflow --disable

# List scheduled DAGs
daglab schedule --list

# Update schedule
daglab schedule my_workflow --cron "0 6 * * 1-5" --timezone "America/New_York"
```

**Options:**
- `--cron EXPRESSION` - Cron schedule expression
- `--disable` - Disable scheduling
- `--enable` - Enable scheduling
- `--timezone TZ` - Timezone for schedule
- `--start-date DATE` - Schedule start date
- `--end-date DATE` - Schedule end date

**Examples:**
```bash
# Daily at 8 AM UTC
daglab schedule etl_pipeline --cron "0 8 * * *"

# Weekdays at 6 AM EST
daglab schedule reports --cron "0 6 * * 1-5" --timezone "America/New_York"

# Temporary schedule with end date
daglab schedule temp_job --cron "0 */2 * * *" --end-date "2024-12-31"
```

### `daglab pause` / `daglab unpause`

Pause and unpause DAG execution.

```bash
# Pause DAG
daglab pause my_workflow

# Unpause DAG
daglab unpause my_workflow

# Pause all DAGs
daglab pause --all

# Pause with reason
daglab pause my_workflow --reason "Maintenance window"
```

**Options:**
- `--all` - Apply to all DAGs
- `--reason TEXT` - Reason for pause/unpause
- `--duration SECONDS` - Auto-unpause after duration

**Examples:**
```bash
# Pause for maintenance
daglab pause data_pipeline --reason "Database maintenance"

# Temporary pause (auto-unpause after 1 hour)
daglab pause api_checks --duration 3600

# Emergency pause all
daglab pause --all --reason "System maintenance"
```

### `daglab kill`

Kill running DAG instances and tasks.

```bash
# Kill specific DAG run
daglab kill my_workflow --run-id 20240101_120000

# Kill specific task
daglab kill my_workflow --task-id extract_data --run-id 20240101_120000

# Kill all running instances of DAG
daglab kill my_workflow --all
```

**Options:**
- `--run-id ID` - Specific run ID
- `--task-id ID` - Specific task ID
- `--all` - Kill all instances
- `--force` - Force kill (SIGKILL)
- `--reason TEXT` - Reason for killing

**Examples:**
```bash
# Graceful kill with reason
daglab kill stuck_pipeline --reason "Resource constraints"

# Force kill hanging task
daglab kill data_processing --task-id slow_task --force

# Kill all instances
daglab kill problematic_dag --all
```

## Data Management

### `daglab data`

Manage workflow data and artifacts.

```bash
# List data artifacts
daglab data list

# Show data for specific DAG
daglab data show my_workflow

# Clean old data
daglab data clean --older-than 30d

# Export data
daglab data export my_workflow --output data_export.tar.gz
```

**Subcommands:**
- `list` - List data artifacts
- `show` - Show data details
- `clean` - Clean old data
- `export` - Export data
- `import` - Import data

**Options:**
- `--older-than DURATION` - Filter by age
- `--size-limit SIZE` - Size limit for operations
- `--compress` - Compress exports
- `--format FORMAT` - Export format

**Examples:**
```bash
# Clean data older than 90 days
daglab data clean --older-than 90d

# Export specific run data
daglab data export ml_pipeline --run-id 20240101_120000 --compress

# Show data usage
daglab data show --usage-stats
```

### `daglab backup`

Backup and restore DagLab data.

```bash
# Create backup
daglab backup create --output backup_20240101.tar.gz

# Restore from backup
daglab backup restore backup_20240101.tar.gz

# Schedule automatic backups
daglab backup schedule --cron "0 2 * * *" --output "/backups/daglab_{date}.tar.gz"
```

**Options:**
- `--output PATH` - Backup output path
- `--compress` - Compress backup
- `--include COMPONENTS` - Components to backup
- `--exclude COMPONENTS` - Components to exclude

**Examples:**
```bash
# Full system backup
daglab backup create --output full_backup.tar.gz --include all

# Database only backup
daglab backup create --include database --output db_backup.sql

# Scheduled daily backups
daglab backup schedule --cron "0 2 * * *" --output "/backups/{date}_backup.tar.gz"
```

## System Administration

### `daglab worker`

Manage worker processes.

```bash
# Start worker
daglab worker start

# Stop worker
daglab worker stop

# List workers
daglab worker list

# Show worker status
daglab worker status worker-001
```

**Subcommands:**
- `start` - Start worker process
- `stop` - Stop worker process
- `restart` - Restart worker
- `list` - List workers
- `status` - Show worker status

**Options:**
- `--concurrency N` - Number of concurrent tasks
- `--queue NAME` - Worker queue name
- `--hostname NAME` - Worker hostname
- `--log-level LEVEL` - Worker log level

**Examples:**
```bash
# Start worker with 8 concurrent tasks
daglab worker start --concurrency 8

# Start worker for specific queue
daglab worker start --queue high_priority

# Stop all workers
daglab worker stop --all
```

### `daglab config`

Manage configuration.

```bash
# Show current configuration
daglab config show

# Show resolved configuration (with env vars)
daglab config show --resolved

# Edit configuration
daglab config edit

# Test configuration
daglab config test
```

**Subcommands:**
- `show` - Display configuration
- `edit` - Edit configuration
- `test` - Test configuration
- `validate` - Validate configuration
- `export` - Export configuration

**Options:**
- `--resolved` - Show with environment variables resolved
- `--format FORMAT` - Output format
- `--section SECTION` - Show specific section

**Examples:**
```bash
# Show database configuration
daglab config show --section database

# Export configuration for deployment
daglab config export --output production_config.yaml

# Test database connection
daglab config test --section database
```

### `daglab db`

Database management commands.

```bash
# Initialize database
daglab db init

# Upgrade database schema
daglab db upgrade

# Reset database
daglab db reset

# Show database status
daglab db status
```

**Subcommands:**
- `init` - Initialize database
- `upgrade` - Upgrade schema
- `downgrade` - Downgrade schema
- `reset` - Reset database
- `status` - Show database status
- `backup` - Create database backup

**Options:**
- `--force` - Force operation
- `--backup` - Create backup before operation
- `--target-revision` - Target schema revision

**Examples:**
```bash
# Initialize with backup
daglab db init --backup

# Upgrade to specific revision
daglab db upgrade --target-revision abc123

# Reset with confirmation
daglab db reset --force
```

### `daglab health`

System health checks and diagnostics.

```bash
# Check system health
daglab health check

# Check specific components
daglab health check --component database

# Run diagnostics
daglab health diagnose

# Health report
daglab health report --output health_report.json
```

**Options:**
- `--component NAME` - Check specific component
- `--timeout SECONDS` - Health check timeout
- `--output PATH` - Output file for reports
- `--format FORMAT` - Report format

**Examples:**
```bash
# Quick health check
daglab health check --timeout 30

# Detailed diagnostics
daglab health diagnose --verbose

# Generate health report
daglab health report --format json --output system_health.json
```

## Monitoring and Metrics

### `daglab metrics`

View system metrics and statistics.

```bash
# Show all metrics
daglab metrics

# Show DAG metrics
daglab metrics dag my_workflow

# Show system metrics
daglab metrics system

# Export metrics
daglab metrics export --output metrics.json
```

**Options:**
- `--start-date DATE` - Start date for metrics
- `--end-date DATE` - End date for metrics
- `--format FORMAT` - Output format
- `--interval DURATION` - Metrics interval

**Examples:**
```bash
# Metrics for last 24 hours
daglab metrics --start-date "2024-01-01" --end-date "2024-01-02"

# DAG performance metrics
daglab metrics dag data_pipeline --interval 1h

# Export system metrics
daglab metrics system --format json --output system_metrics.json
```

### `daglab monitor`

Real-time monitoring commands.

```bash
# Monitor DAG execution
daglab monitor my_workflow

# Monitor system resources
daglab monitor system

# Monitor specific metrics
daglab monitor --metric task_duration
```

**Options:**
- `--refresh SECONDS` - Refresh interval
- `--metric NAME` - Specific metric to monitor
- `--alert-threshold VALUE` - Alert threshold

**Examples:**
```bash
# Monitor with 5-second refresh
daglab monitor my_workflow --refresh 5

# Monitor with alerts
daglab monitor system --alert-threshold "cpu>80"
```

## Testing and Development

### `daglab test`

Test DAGs and components.

```bash
# Test specific DAG
daglab test dags/my_workflow.yaml

# Run all tests
daglab test --all

# Test with mock data
daglab test dags/my_workflow.yaml --mock-data test_data.json
```

**Options:**
- `--all` - Test all DAGs
- `--mock-data PATH` - Mock data file
- `--coverage` - Generate coverage report
- `--verbose` - Detailed output

**Examples:**
```bash
# Test with coverage
daglab test dags/data_pipeline.yaml --coverage

# Test all DAGs with mock data
daglab test --all --mock-data test_datasets/

# Verbose testing
daglab test dags/complex_dag.yaml --verbose
```

### `daglab develop`

Development utilities.

```bash
# Start development server
daglab develop server

# Generate DAG template
daglab develop template --type etl --output new_etl_dag.yaml

# Format DAG files
daglab develop format dags/
```

**Subcommands:**
- `server` - Start development server
- `template` - Generate templates
- `format` - Format DAG files
- `lint` - Lint DAG files

**Examples:**
```bash
# Development server with auto-reload
daglab develop server --auto-reload --port 8080

# Generate ML pipeline template
daglab develop template --type ml_pipeline --name "Customer Segmentation"

# Format and lint all DAGs
daglab develop format dags/ && daglab develop lint dags/
```

## Import/Export Operations

### `daglab export`

Export DAGs, data, and configurations.

```bash
# Export DAG definition
daglab export dag my_workflow --output my_workflow.yaml

# Export all DAGs
daglab export dags --output all_dags.tar.gz

# Export system configuration
daglab export config --output system_config.yaml
```

**Options:**
- `--output PATH` - Output file path
- `--format FORMAT` - Export format
- `--compress` - Compress output
- `--include-data` - Include data artifacts

**Examples:**
```bash
# Export DAG with data
daglab export dag data_pipeline --include-data --output pipeline_export.tar.gz

# Export for migration
daglab export all --format json --output migration_package.json
```

### `daglab import`

Import DAGs and configurations.

```bash
# Import DAG
daglab import dag new_workflow.yaml

# Import from archive
daglab import dags workflow_archive.tar.gz

# Import configuration
daglab import config production_config.yaml
```

**Options:**
- `--overwrite` - Overwrite existing
- `--validate` - Validate before import
- `--dry-run` - Preview import

**Examples:**
```bash
# Import with validation
daglab import dag new_pipeline.yaml --validate

# Safe import (dry run first)
daglab import dags archive.tar.gz --dry-run
```

## Plugin Management

### `daglab plugin`

Manage DagLab plugins.

```bash
# List installed plugins
daglab plugin list

# Install plugin
daglab plugin install daglab-aws

# Uninstall plugin
daglab plugin uninstall daglab-aws

# Show plugin info
daglab plugin info daglab-kubernetes
```

**Subcommands:**
- `list` - List plugins
- `install` - Install plugin
- `uninstall` - Remove plugin
- `info` - Show plugin information
- `search` - Search available plugins

**Examples:**
```bash
# Install from PyPI
daglab plugin install daglab-snowflake

# Install from Git
daglab plugin install git+https://github.com/company/daglab-custom.git

# List with versions
daglab plugin list --versions
```

## Batch Operations

### `daglab batch`

Perform batch operations on multiple DAGs.

```bash
# Run multiple DAGs
daglab batch run dags/etl_*.yaml

# Pause multiple DAGs
daglab batch pause --pattern "data_*"

# Validate multiple DAGs
daglab batch validate dags/
```

**Options:**
- `--pattern PATTERN` - File pattern or DAG name pattern
- `--parallel N` - Number of parallel operations
- `--continue-on-error` - Continue despite errors

**Examples:**
```bash
# Run all ETL DAGs in parallel
daglab batch run dags/etl_*.yaml --parallel 4

# Pause all test DAGs
daglab batch pause --pattern "test_*"

# Validate all DAGs with error tolerance
daglab batch validate dags/ --continue-on-error
```

## Shell and Interactive Mode

### `daglab shell`

Interactive shell for DagLab operations.

```bash
# Start interactive shell
daglab shell

# Execute commands from file
daglab shell --script commands.txt

# Shell with specific context
daglab shell --dag my_workflow
```

**Features:**
- Tab completion
- Command history
- Built-in help
- Context-aware commands

### `daglab exec`

Execute arbitrary commands in DagLab context.

```bash
# Execute Python script
daglab exec python scripts/data_analysis.py

# Execute SQL query
daglab exec sql "SELECT COUNT(*) FROM dag_runs"

# Execute with environment
daglab exec --env production python deploy.py
```

## Advanced Commands

### `daglab cluster`

Cluster management for distributed deployments.

```bash
# Show cluster status
daglab cluster status

# Add node to cluster
daglab cluster add-node worker-node-2

# Remove node from cluster
daglab cluster remove-node worker-node-1
```

### `daglab security`

Security and audit commands.

```bash
# Run security scan
daglab security scan

# Generate audit report
daglab security audit --output audit_report.pdf

# Rotate secrets
daglab security rotate-secrets
```

## Global Configuration

### Configuration Files

DagLab looks for configuration in these locations (in order):

1. `--config` command line option
2. `DAGLAB_CONFIG` environment variable
3. `./config/daglab.yaml`
4. `~/.daglab/config.yaml`
5. `/etc/daglab/config.yaml`

### Environment Variables

Key environment variables:

```bash
DAGLAB_CONFIG          # Configuration file path
DAGLAB_HOME           # DagLab home directory
DAGLAB_LOG_LEVEL      # Default log level
DAGLAB_DATABASE_URL   # Database connection URL
DAGLAB_EXECUTOR       # Default executor type
```

## Command Aliases

Common command aliases for efficiency:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias dl='daglab'
alias dlr='daglab run'
alias dls='daglab status'
alias dll='daglab logs'
alias dlv='daglab validate'
```

## Exit Codes

DagLab CLI uses standard exit codes:

- `0` - Success
- `1` - General error
- `2` - Invalid command or arguments
- `3` - Configuration error
- `4` - Database error
- `5` - Network error
- `126` - Permission denied
- `127` - Command not found

## Getting Help

### Built-in Help

```bash
# General help
daglab --help

# Command-specific help
daglab run --help

# Subcommand help
daglab config show --help
```

### Man Pages

```bash
# Install man pages (if available)
daglab install-man-pages

# View man page
man daglab
man daglab-run
```

### Online Documentation

For the latest documentation and examples:
- [CLI Reference](https://docs.daglab.io/cli/)
- [Command Examples](https://docs.daglab.io/examples/)
- [Troubleshooting](https://docs.daglab.io/troubleshooting/)

## Best Practices

### Command Line Best Practices

1. **Use configuration files** instead of command-line options for complex setups
2. **Implement proper error handling** in scripts using DagLab CLI
3. **Use `--dry-run`** to test commands before execution
4. **Leverage shell aliases** for frequently used commands
5. **Monitor long-running operations** with appropriate timeouts

### Automation Best Practices

1. **Script repetitive tasks** using batch commands
2. **Use JSON output** for integration with other tools
3. **Implement proper logging** in automated scripts
4. **Set appropriate timeouts** for automated operations
5. **Handle errors gracefully** in automation scripts

### Security Best Practices

1. **Use environment variables** for sensitive information
2. **Implement proper access controls** for CLI access
3. **Audit CLI usage** in production environments
4. **Use service accounts** for automated operations
5. **Regular security updates** for CLI tools

This comprehensive CLI reference should help you effectively use DagLab from the command line. For specific use cases and advanced scenarios, refer to the [Tutorials](../tutorials/README.md) and [Examples](../examples/) sections.
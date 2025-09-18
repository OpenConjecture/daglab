#!/bin/bash
# Example usage of daglab run command

echo "=== Daglab Run Command Examples ==="
echo ""

# 1. Basic job execution
echo "1. Run a simple job:"
echo "   daglab run --job daily_etl"
echo ""

# 2. Run job with configuration file
echo "2. Run job with configuration file:"
echo "   daglab run --job daily_etl --run-config examples/run_configs/job_config.yaml"
echo ""

# 3. Run job with inline configuration
echo "3. Run job with inline YAML configuration:"
echo '   daglab run --job batch_job --config-yaml "ops: {process: {config: {batch_size: 100}}}"'
echo ""

# 4. Materialize specific assets
echo "4. Materialize specific assets:"
echo "   daglab run --asset-selection raw_orders --asset-selection raw_customers"
echo ""

# 5. Use asset patterns
echo "5. Materialize assets using patterns:"
echo '   daglab run --asset-pattern "analytics/*"'
echo '   daglab run --asset-pattern "ingestion/raw_*"'
echo ""

# 6. Run with repository and location
echo "6. Specify repository and location:"
echo "   daglab run --job ml_pipeline --repo analytics_repo --location prod_location"
echo ""

# 7. Don't wait for completion
echo "7. Submit job without waiting:"
echo "   daglab run --job long_running_job --no-wait"
echo ""

# 8. Run with timeout
echo "8. Run with timeout (1 hour):"
echo "   daglab run --job data_sync --timeout 3600"
echo ""

# 9. Run with timeout and auto-cancellation
echo "9. Cancel job if it exceeds timeout:"
echo "   daglab run --job batch_process --timeout 1800 --cancel-on-timeout"
echo ""

# 10. Add run tags
echo "10. Add tags to run:"
echo '    daglab run --job daily_etl --tags "env=prod,team=data-eng,version=1.2.0"'
echo ""

# 11. Validate configuration only
echo "11. Validate configuration without running:"
echo "    daglab run --job ml_pipeline --run-config ml_config.yaml --validate-only"
echo ""

# 12. JSON output for automation
echo "12. Get JSON output for scripting:"
echo "    daglab run --job daily_etl --json"
echo ""

# 13. Verbose output
echo "13. Enable verbose output:"
echo "    daglab run --job debug_job --verbose"
echo ""

# 14. Validate command
echo "14. Validate job configuration:"
echo "    daglab run validate --job ml_pipeline --run-config examples/run_configs/ml_pipeline_config.json"
echo ""

# 15. List available assets
echo "15. List available assets:"
echo "    daglab run list-assets"
echo "    daglab run list-assets --pattern 'raw*' --json"
echo ""

# 16. List available jobs
echo "16. List available jobs:"
echo "    daglab run list-jobs"
echo "    daglab run list-jobs --repo analytics_repo --json"
echo ""

# 17. Complex example with environment variables
echo "17. Complex example with environment setup:"
echo "    export DAGSTER_UI_URL=http://dagster.mycompany.com"
echo "    export DB_HOST=prod.database.com"
echo "    export S3_BUCKET=my-prod-bucket"
echo "    daglab run --job etl_pipeline \\"
echo "      --run-config job_config.yaml \\"
echo "      --tags 'scheduled=true,priority=high' \\"
echo "      --timeout 7200 \\"
echo "      --json > run_result.json"
echo ""

# 18. Asset materialization with configuration
echo "18. Materialize assets with configuration:"
echo "    daglab run --asset-selection daily_revenue \\"
echo "      --asset-selection customer_segments \\"
echo "      --run-config asset_config.yaml \\"
echo "      --tags 'backfill=true'"
echo ""

echo "=== Tips ==="
echo "- Use --validate-only to check configurations before running"
echo "- Use --json for integration with CI/CD pipelines"
echo "- Set DAGSTER_UI_URL environment variable to customize UI links"
echo "- Use --no-wait for fire-and-forget execution"
echo "- Combine --timeout with --cancel-on-timeout for safety"
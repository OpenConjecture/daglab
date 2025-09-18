# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "marimo",
#     "dagster",
#     "daglab",
#     "pandas",
#     "numpy",
# ]
# ///

import marimo

__generated_with = "{{ daglab_version }}"

app = marimo.App(width="{{ width | default('medium') }}")


@app.cell
def __():
    import marimo as mo
    import pandas as pd
    import numpy as np
    from dagster import asset, materialize_to_memory
    from daglab.dagster_utils import get_dagster_context
    {% if template_vars %}
    # Custom imports
    {% for import in template_vars.imports %}
    {{ import }}
    {% endfor %}
    {% endif %}
    return mo, pd, np, asset, materialize_to_memory, get_dagster_context


@app.cell
def __(mo):
    mo.md(
        r"""
        # {{ title | default('DAGLab Notebook') }}
        
        {% if description %}
        {{ description }}
        {% else %}
        This notebook was generated with DAGLab scaffold command.
        {% endif %}
        
        {% if target_type == 'asset' %}
        **Target Asset:** `{{ target_name }}`
        {% elif target_type == 'job' %}
        **Target Job:** `{{ target_name }}`
        {% endif %}
        
        ---
        """
    )
    return


@app.cell
def __(mo, get_dagster_context):
    mo.md("## Connect to Dagster")
    
    # Initialize Dagster context
    context = get_dagster_context()
    mo.md(f"✅ Connected to Dagster instance at: {context.instance.storage_directory()}")
    return context,


{% if target_type == 'asset' %}
@app.cell
def __(mo, context):
    mo.md("## Load Target Asset")
    
    # Load the target asset
    asset_key = "{{ target_name }}"
    {% if not no_attach %}
    try:
        latest_materialization = context.instance.get_latest_materialization_event(
            asset_key=asset_key
        )
        if latest_materialization:
            mo.md(f"✅ Found latest materialization for `{asset_key}`")
        else:
            mo.md(f"⚠️ No materializations found for `{asset_key}`")
    except Exception as e:
        mo.md(f"❌ Error loading asset: {e}")
    {% else %}
    mo.md(f"Asset attachment disabled. Working with asset key: `{asset_key}`")
    {% endif %}
    return asset_key,


{% elif target_type == 'job' %}
@app.cell
def __(mo, context):
    mo.md("## Load Target Job")
    
    job_name = "{{ target_name }}"
    {% if not no_attach %}
    try:
        # Get recent runs for the job
        runs = context.instance.get_runs(
            filters=RunsFilter(job_name=job_name),
            limit=5
        )
        if runs:
            mo.md(f"✅ Found {len(runs)} recent runs for job `{job_name}`")
        else:
            mo.md(f"⚠️ No runs found for job `{job_name}`")
    except Exception as e:
        mo.md(f"❌ Error loading job: {e}")
    {% else %}
    mo.md(f"Job attachment disabled. Working with job: `{job_name}`")
    {% endif %}
    return job_name,


{% endif %}
@app.cell
def __(mo, pd, np):
    mo.md("## Data Processing")
    
    {% if seed_data %}
    # Generate sample data
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100),
        'value': np.random.randn(100).cumsum() + 100,
        'category': np.random.choice(['A', 'B', 'C'], 100)
    })
    
    mo.md("Generated sample data:")
    mo.ui.table(df.head())
    {% else %}
    # Load your data here
    df = pd.DataFrame()  # Replace with actual data loading
    {% endif %}
    
    return df,


@app.cell
def __(mo, df):
    mo.md("## Analysis")
    
    # Perform your analysis here
    if not df.empty:
        summary = df.describe()
        mo.md("### Data Summary")
        mo.ui.table(summary)
    else:
        mo.md("⚠️ No data loaded. Add your data loading logic above.")
    
    return summary,


{% if not no_inprocess %}
@app.cell
def __(mo, asset):
    mo.md("## Define Dagster Asset")
    
    @asset(
        name="{{ asset_name | default('notebook_output') }}",
        {% if target_type == 'asset' %}
        deps=["{{ target_name }}"],
        {% endif %}
        description="Asset generated from DAGLab notebook"
    )
    def notebook_asset():
        """
        This asset will be created when you run `daglab sync`.
        """
        # Your asset logic here
        return df
    
    mo.md("✅ Asset defined. Run `daglab sync` to register with Dagster.")
    return notebook_asset,
{% endif %}


@app.cell
def __(mo):
    mo.md(
        r"""
        ## Next Steps
        
        1. {% if not no_inprocess %}Run `daglab sync` to register this notebook as a Dagster asset{% else %}Export this notebook for use in your pipeline{% endif %}
        2. View your {% if target_type == 'asset' %}asset{% else %}job{% endif %} in the Dagster UI
        3. {% if validate_config %}Validate your configuration with `daglab validate`{% else %}Configure your pipeline as needed{% endif %}
        
        ---
        
        <small>Generated with DAGLab {{ daglab_version }} | Template: {{ template }}</small>
        """
    )
    return


if __name__ == "__main__":
    app.run()
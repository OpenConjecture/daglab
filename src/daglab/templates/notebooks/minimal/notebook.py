# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "marimo",
#     "dagster",
#     "daglab",
# ]
# ///

import marimo

__generated_with = "{{ daglab_version }}"

app = marimo.App()


@app.cell
def __():
    import marimo as mo
    from dagster import asset
    from daglab.dagster_utils import get_dagster_context
    return mo, asset, get_dagster_context


@app.cell
def __(mo):
    mo.md(
        r"""
        # {{ title | default('DAGLab Minimal Notebook') }}
        
        {% if target_type == 'asset' %}Target Asset: `{{ target_name }}`{% endif %}
        {% if target_type == 'job' %}Target Job: `{{ target_name }}`{% endif %}
        """
    )
    return


@app.cell
def __():
    # Your code here
    result = None
    return result,


{% if not no_inprocess %}
@app.cell
def __(asset):
    @asset(name="{{ asset_name | default('notebook_output') }}")
    def notebook_asset():
        return result
    
    return notebook_asset,
{% endif %}


if __name__ == "__main__":
    app.run()
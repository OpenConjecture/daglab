"""Minimal example assets."""

from dagster import asset


@asset
def hello_world() -> str:
    """A simple hello world asset."""
    return "Hello from Dagster + Daglab!"
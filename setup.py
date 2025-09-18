"""Setup configuration for DagLab."""

from setuptools import setup, find_packages

setup(
    name="daglab",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click>=8.0",
        "rich>=13.0",
    ],
    entry_points={
        "console_scripts": [
            "daglab=daglab.cli:cli",
        ],
    },
    python_requires=">=3.8",
)
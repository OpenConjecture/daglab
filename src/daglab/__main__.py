"""Allow daglab to be run as a module: python -m daglab"""

from daglab.cli import app

if __name__ == "__main__":
    app()
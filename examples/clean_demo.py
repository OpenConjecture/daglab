#!/usr/bin/env python3
"""Demonstration of the daglab clean command."""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from daglab.commands.clean import clean
from click.testing import CliRunner


def create_demo_files():
    """Create demo files to show cleaning in action."""
    # Create directories
    dirs = ["exports", "logs", ".daglab/tmp", ".daglab/cache", "build", "__pycache__"]
    for dir_name in dirs:
        Path(dir_name).mkdir(parents=True, exist_ok=True)
    
    # Create old files (45 days old)
    old_files = {
        "exports/old_report.html": "<html>Old report from last month</html>",
        "exports/old_dashboard.html": "<html>Old dashboard</html>",
        "logs/old_app.log": "2024-01-01 - Old log entries\n" * 100,
        ".daglab/tmp/tempfile_12345.tmp": "Temporary processing data",
        ".daglab/cache/query_cache.db": "Cached query results",
        "build/dist/old_build.tar.gz": "Old build artifact",
        "__pycache__/module.cpython-39.pyc": "Compiled bytecode",
    }
    
    old_timestamp = (datetime.now() - timedelta(days=45)).timestamp()
    
    for file_path, content in old_files.items():
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        os.utime(path, (old_timestamp, old_timestamp))
    
    # Create recent files (5 days old)
    recent_files = {
        "exports/recent_report.html": "<html>Recent report</html>",
        "logs/current.log": "2024-12-01 - Current log entries",
    }
    
    recent_timestamp = (datetime.now() - timedelta(days=5)).timestamp()
    
    for file_path, content in recent_files.items():
        path = Path(file_path)
        path.write_text(content)
        os.utime(path, (recent_timestamp, recent_timestamp))
    
    print("✅ Created demo files:")
    print("\nOld files (45 days old):")
    for f in old_files:
        size = Path(f).stat().st_size
        print(f"  - {f} ({size} bytes)")
    
    print("\nRecent files (5 days old):")
    for f in recent_files:
        size = Path(f).stat().st_size
        print(f"  - {f} ({size} bytes)")


def main():
    """Run the clean command demonstration."""
    print("🧹 DagLab Clean Command Demo\n")
    print("=" * 50)
    
    # Create demo files
    create_demo_files()
    
    runner = CliRunner()
    
    # Demo 1: Dry run to see what would be deleted
    print("\n" + "=" * 50)
    print("📋 Demo 1: Dry run (preview what would be deleted)")
    print("Command: daglab clean --dry-run")
    print("-" * 50)
    
    result = runner.invoke(clean, ['--dry-run'])
    print(result.output)
    
    # Demo 2: Clean with custom age threshold
    print("\n" + "=" * 50)
    print("📋 Demo 2: Clean files older than 40 days")
    print("Command: daglab clean --older-than 40 --yes")
    print("-" * 50)
    
    result = runner.invoke(clean, ['--older-than', '40', '--yes'])
    print(result.output)
    
    # Show remaining files
    print("\n📁 Remaining files:")
    for pattern in ["exports/*.html", "logs/*.log", ".daglab/tmp/*", "__pycache__/*"]:
        files = list(Path(".").glob(pattern))
        if files:
            print(f"\n  {pattern}:")
            for f in files:
                print(f"    - {f}")
        else:
            print(f"\n  {pattern}: [cleaned]")
    
    # Cleanup demo files
    print("\n🧹 Cleaning up demo...")
    for dir_name in ["exports", "logs", ".daglab", "build", "__pycache__"]:
        path = Path(dir_name)
        if path.exists():
            import shutil
            shutil.rmtree(path)
    
    print("✅ Demo complete!")


if __name__ == "__main__":
    main()
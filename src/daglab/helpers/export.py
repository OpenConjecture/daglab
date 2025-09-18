"""Export engine for notebook conversion."""

import subprocess
import tempfile
import shutil
import gzip
import zipfile
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from dataclasses import dataclass
import marimo
import jinja2
from playwright.sync_api import sync_playwright
import nbformat
from nbconvert import HTMLExporter, MarkdownExporter, PythonExporter

from daglab.runtime.logging import setup_logger

logger = setup_logger(__name__)


class ExportFormat(Enum):
    """Supported export formats."""
    HTML = "HTML"
    PDF = "PDF"
    MD = "MD"
    PY = "PY"
    IPYNB = "IPYNB"
    DAGSTER = "DAGSTER"


@dataclass
class ExportResult:
    """Result of an export operation."""
    path: str
    output_path: str
    format: str
    size: int
    compressed: bool = False
    compression_ratio: float = 0.0
    dagster_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ExportEngine:
    """Engine for exporting Marimo notebooks to various formats."""
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize the export engine.
        
        Args:
            templates_dir: Directory containing custom templates
        """
        self.templates_dir = templates_dir or Path(__file__).parent / "templates"
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_dir))
        )
    
    def get_file_extension(self, format: ExportFormat) -> str:
        """Get file extension for a format."""
        extensions = {
            ExportFormat.HTML: ".html",
            ExportFormat.PDF: ".pdf",
            ExportFormat.MD: ".md",
            ExportFormat.PY: ".py",
            ExportFormat.IPYNB: ".ipynb",
            ExportFormat.DAGSTER: "_assets.py",
        }
        return extensions.get(format, "")
    
    def export(
        self,
        notebook_path: Path,
        format: ExportFormat,
        output_path: Optional[Path] = None,
        include_metadata: bool = True,
        template: Optional[str] = None,
        compress: bool = False,
        export_as_assets: bool = False,
    ) -> Dict[str, Any]:
        """Export a notebook to the specified format.
        
        Args:
            notebook_path: Path to the notebook file
            format: Export format
            output_path: Output file path
            include_metadata: Include notebook metadata
            template: Custom template name
            compress: Compress output
            export_as_assets: Export as Dagster assets
            
        Returns:
            Export result dictionary
        """
        if not notebook_path.exists():
            raise FileNotFoundError(f"Notebook not found: {notebook_path}")
        
        # Default output path
        if output_path is None:
            output_path = notebook_path.with_suffix(self.get_file_extension(format))
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Export based on format
            if format == ExportFormat.HTML:
                result = self._export_html(
                    notebook_path, output_path, include_metadata, template
                )
            elif format == ExportFormat.PDF:
                result = self._export_pdf(
                    notebook_path, output_path, include_metadata, template
                )
            elif format == ExportFormat.MD:
                result = self._export_markdown(
                    notebook_path, output_path, include_metadata
                )
            elif format == ExportFormat.PY:
                result = self._export_python(
                    notebook_path, output_path, include_metadata
                )
            elif format == ExportFormat.IPYNB:
                result = self._export_ipynb(
                    notebook_path, output_path, include_metadata
                )
            elif format == ExportFormat.DAGSTER:
                result = self._export_dagster(
                    notebook_path, output_path, export_as_assets
                )
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            # Compress if requested
            if compress and format in [ExportFormat.HTML, ExportFormat.MD]:
                compressed_path = self._compress_file(output_path)
                result["compressed"] = True
                result["compression_ratio"] = (
                    compressed_path.stat().st_size / output_path.stat().st_size * 100
                )
                result["output_path"] = str(compressed_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {
                "path": str(notebook_path),
                "output_path": str(output_path),
                "format": format.value,
                "error": str(e),
            }
    
    def _export_html(
        self,
        notebook_path: Path,
        output_path: Path,
        include_metadata: bool,
        template: Optional[str],
    ) -> Dict[str, Any]:
        """Export notebook to HTML format."""
        # Use marimo export command
        cmd = ["marimo", "export", "html", str(notebook_path)]
        
        if not include_metadata:
            cmd.append("--no-include-metadata")
        
        # Run export
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        
        # Apply custom template if provided
        html_content = result.stdout
        if template:
            template_obj = self.jinja_env.get_template(f"{template}.html")
            html_content = template_obj.render(
                content=html_content,
                title=notebook_path.stem,
                metadata=self._extract_metadata(notebook_path) if include_metadata else {},
            )
        
        # Write output
        output_path.write_text(html_content)
        
        return {
            "path": str(notebook_path),
            "output_path": str(output_path),
            "format": "HTML",
            "size": output_path.stat().st_size,
        }
    
    def _export_pdf(
        self,
        notebook_path: Path,
        output_path: Path,
        include_metadata: bool,
        template: Optional[str],
    ) -> Dict[str, Any]:
        """Export notebook to PDF format using Playwright."""
        # First export to HTML
        html_path = output_path.with_suffix(".html")
        self._export_html(notebook_path, html_path, include_metadata, template)
        
        # Convert HTML to PDF using Playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # Load HTML
            page.goto(f"file://{html_path.absolute()}")
            
            # Generate PDF
            page.pdf(
                path=str(output_path),
                format="A4",
                print_background=True,
                margin={"top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm"},
            )
            
            browser.close()
        
        # Clean up temporary HTML
        html_path.unlink()
        
        return {
            "path": str(notebook_path),
            "output_path": str(output_path),
            "format": "PDF",
            "size": output_path.stat().st_size,
        }
    
    def _export_markdown(
        self,
        notebook_path: Path,
        output_path: Path,
        include_metadata: bool,
    ) -> Dict[str, Any]:
        """Export notebook to Markdown format."""
        # Use marimo export command
        cmd = ["marimo", "export", "md", str(notebook_path)]
        
        if not include_metadata:
            cmd.append("--no-include-metadata")
        
        # Run export
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        
        # Write output
        output_path.write_text(result.stdout)
        
        return {
            "path": str(notebook_path),
            "output_path": str(output_path),
            "format": "MD",
            "size": output_path.stat().st_size,
        }
    
    def _export_python(
        self,
        notebook_path: Path,
        output_path: Path,
        include_metadata: bool,
    ) -> Dict[str, Any]:
        """Export notebook to pure Python script."""
        # Use marimo export command
        cmd = ["marimo", "export", "script", str(notebook_path)]
        
        # Run export
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        
        content = result.stdout
        
        # Add metadata as comments if requested
        if include_metadata:
            metadata = self._extract_metadata(notebook_path)
            metadata_lines = [
                "# Metadata:",
                f"# Title: {metadata.get('title', 'Untitled')}",
                f"# Description: {metadata.get('description', '')}",
                f"# Author: {metadata.get('author', '')}",
                f"# Date: {metadata.get('date', '')}",
                "",
            ]
            content = "\n".join(metadata_lines) + content
        
        # Write output
        output_path.write_text(content)
        
        return {
            "path": str(notebook_path),
            "output_path": str(output_path),
            "format": "PY",
            "size": output_path.stat().st_size,
        }
    
    def _export_ipynb(
        self,
        notebook_path: Path,
        output_path: Path,
        include_metadata: bool,
    ) -> Dict[str, Any]:
        """Export marimo notebook to Jupyter notebook format."""
        # Use marimo export command
        cmd = ["marimo", "export", "ipynb", str(notebook_path)]
        
        # Run export
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        
        # Parse and potentially modify notebook
        notebook = nbformat.reads(result.stdout, as_version=4)
        
        if not include_metadata:
            notebook.metadata = {}
        
        # Write output
        nbformat.write(notebook, output_path)
        
        return {
            "path": str(notebook_path),
            "output_path": str(output_path),
            "format": "IPYNB",
            "size": output_path.stat().st_size,
        }
    
    def _export_dagster(
        self,
        notebook_path: Path,
        output_path: Path,
        export_as_assets: bool,
    ) -> Dict[str, Any]:
        """Export notebook as Dagster assets."""
        # Read notebook content
        content = notebook_path.read_text()
        
        # Extract metadata and dependencies
        metadata = self._extract_metadata(notebook_path)
        dependencies = self._extract_dependencies(content)
        
        # Generate Dagster assets code
        asset_name = notebook_path.stem.replace("-", "_").replace(" ", "_")
        
        if export_as_assets:
            dagster_code = self._generate_dagster_assets(
                asset_name, notebook_path, metadata, dependencies
            )
        else:
            dagster_code = self._generate_dagster_job(
                asset_name, notebook_path, metadata
            )
        
        # Write output
        output_path.write_text(dagster_code)
        
        return {
            "path": str(notebook_path),
            "output_path": str(output_path),
            "format": "DAGSTER",
            "size": output_path.stat().st_size,
            "dagster_metadata": {
                "asset_key": asset_name,
                "dependencies": dependencies,
                "metadata": metadata,
            },
        }
    
    def _compress_file(self, file_path: Path) -> Path:
        """Compress a file using gzip."""
        compressed_path = file_path.with_suffix(file_path.suffix + ".gz")
        
        with open(file_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return compressed_path
    
    def _extract_metadata(self, notebook_path: Path) -> Dict[str, Any]:
        """Extract metadata from notebook."""
        # Try to parse marimo notebook metadata
        content = notebook_path.read_text()
        metadata = {
            "title": notebook_path.stem,
            "path": str(notebook_path),
        }
        
        # Look for marimo metadata comments
        for line in content.split("\n"):
            if line.startswith("# @title:"):
                metadata["title"] = line.replace("# @title:", "").strip()
            elif line.startswith("# @description:"):
                metadata["description"] = line.replace("# @description:", "").strip()
            elif line.startswith("# @author:"):
                metadata["author"] = line.replace("# @author:", "").strip()
        
        return metadata
    
    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract dependencies from notebook content."""
        dependencies = []
        
        # Look for import statements
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("import ") or line.startswith("from "):
                # Extract module name
                parts = line.split()
                if parts[0] == "import" and len(parts) > 1:
                    dependencies.append(parts[1].split(".")[0])
                elif parts[0] == "from" and len(parts) > 1:
                    dependencies.append(parts[1].split(".")[0])
        
        # Remove duplicates and standard library modules
        stdlib = {"os", "sys", "json", "math", "random", "datetime", "time", "re"}
        dependencies = list(set(dependencies) - stdlib)
        
        return dependencies
    
    def _generate_dagster_assets(
        self,
        asset_name: str,
        notebook_path: Path,
        metadata: Dict[str, Any],
        dependencies: List[str],
    ) -> str:
        """Generate Dagster asset definition."""
        template = '''"""Dagster assets generated from {notebook_path}"""

from dagster import asset, AssetIn, MetadataValue, Output
import subprocess
import json
from pathlib import Path


@asset(
    name="{asset_name}",
    description="{description}",
    {deps}
    metadata={{
        "notebook_path": "{notebook_path}",
        "author": "{author}",
    }}
)
def {asset_name}({params}):
    """Execute {notebook_path} as a Dagster asset."""
    
    # Execute notebook
    result = subprocess.run(
        ["marimo", "run", "{notebook_path}", "--headless"],
        capture_output=True,
        text=True,
        check=True,
    )
    
    # Parse output
    output_data = {{
        "stdout": result.stdout,
        "execution_time": result.returncode,
    }}
    
    return Output(
        value=output_data,
        metadata={{
            "preview": MetadataValue.md(result.stdout[:500]),
            "num_lines": len(result.stdout.splitlines()),
        }}
    )
'''
        
        # Format dependencies
        deps = ""
        params = ""
        if dependencies:
            deps = f"ins={{{', '.join([f'"{dep}": AssetIn()' for dep in dependencies])}}},\n    "
            params = ", ".join(dependencies)
        
        return template.format(
            notebook_path=notebook_path,
            asset_name=asset_name,
            description=metadata.get("description", f"Asset from {notebook_path.name}"),
            author=metadata.get("author", ""),
            deps=deps,
            params=params,
        )
    
    def _generate_dagster_job(
        self,
        job_name: str,
        notebook_path: Path,
        metadata: Dict[str, Any],
    ) -> str:
        """Generate Dagster job definition."""
        template = '''"""Dagster job generated from {notebook_path}"""

from dagster import job, op, Out, In
import subprocess
from pathlib import Path


@op(
    name="run_{job_name}",
    description="Execute {notebook_path}",
    out=Out(dict),
)
def run_{job_name}_op():
    """Execute notebook as Dagster op."""
    
    result = subprocess.run(
        ["marimo", "run", "{notebook_path}", "--headless"],
        capture_output=True,
        text=True,
        check=True,
    )
    
    return {{
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }}


@job(
    name="{job_name}_job",
    description="{description}",
)
def {job_name}_job():
    """Job for executing {notebook_path}"""
    run_{job_name}_op()
'''
        
        return template.format(
            notebook_path=notebook_path,
            job_name=job_name,
            description=metadata.get("description", f"Job from {notebook_path.name}"),
        )


def validate_export_path(path: Path, format: ExportFormat) -> bool:
    """Validate export path for a given format."""
    if not path.parent.exists():
        return False
    
    # Check extension matches format
    expected_ext = ExportEngine().get_file_extension(format)
    if not str(path).endswith(expected_ext):
        return False
    
    return True
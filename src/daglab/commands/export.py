"""Export command for notebook conversion."""

import typer
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
import json
import sys

from daglab.helpers.export import ExportEngine, ExportFormat
from daglab.helpers.cloud import CloudStorageProvider, create_storage_provider
from daglab.helpers.metadata import MetadataAttacher
from daglab.utils.formatting import format_success, format_error, format_warning
from daglab.runtime.logging import setup_logger

logger = setup_logger(__name__)
console = Console()
app = typer.Typer(help="Export notebooks to various formats")


@app.callback(invoke_without_command=True)
def export(
    ctx: typer.Context,
    notebook: Path = typer.Argument(
        ...,
        help="Notebook file to export",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    format: str = typer.Option(
        "html",
        "--format",
        "-f",
        help="Export format (html|pdf|md|py|ipynb|dagster)"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path"
    ),
    metadata: bool = typer.Option(
        True,
        "--metadata/--no-metadata",
        help="Include notebook metadata in export"
    ),
    assets: bool = typer.Option(
        False,
        "--assets",
        help="Export as Dagster assets"
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help="Custom template for export"
    ),
    cloud_provider: Optional[str] = typer.Option(
        None,
        "--cloud",
        "-c",
        help="Cloud storage provider (s3|gcs|azure)"
    ),
    cloud_bucket: Optional[str] = typer.Option(
        None,
        "--bucket",
        "-b",
        help="Cloud storage bucket name"
    ),
    cloud_key: Optional[str] = typer.Option(
        None,
        "--key",
        "-k",
        help="Cloud storage key/path"
    ),
    compress: bool = typer.Option(
        False,
        "--compress",
        help="Compress output (HTML/MD only)"
    ),
    retention_days: Optional[int] = typer.Option(
        None,
        "--retention",
        "-r",
        help="Cloud storage retention policy (days)"
    ),
    dagster_url: Optional[str] = typer.Option(
        None,
        "--dagster-url",
        help="Dagster instance URL for metadata"
    ),
    dagster_token: Optional[str] = typer.Option(
        None,
        "--dagster-token",
        help="Dagster authentication token"
    ),
    batch: bool = typer.Option(
        False,
        "--batch",
        help="Process directory of notebooks"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output"
    ),
) -> None:
    """Export Marimo notebooks to various formats.
    
    Convert notebooks to different formats for sharing, deployment,
    or integration with other systems.
    
    Examples:
        daglab export notebook.py --format html
        daglab export analysis.py --format pdf --output report.pdf
        daglab export pipeline.py --format dagster --assets
        daglab export notebook.py --format ipynb --no-metadata
        daglab export notebook.py --format html --cloud s3 --bucket my-reports
        daglab export notebook.py --format html --compress
    """
    if ctx.invoked_subcommand is None:
        try:
            # Validate format
            try:
                export_format = ExportFormat(format.upper())
            except ValueError:
                console.print(
                    format_error(
                        f"Invalid format '{format}'. Choose from: html, pdf, md, py, ipynb, dagster"
                    )
                )
                raise typer.Exit(1)
            
            # Initialize export engine
            engine = ExportEngine()
            
            # Setup progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                
                # Handle batch processing
                notebooks = []
                if batch:
                    if notebook.is_dir():
                        notebooks = list(notebook.glob("*.py"))
                        console.print(f"Found {len(notebooks)} notebooks to export")
                    else:
                        console.print(
                            format_warning("Batch mode requires a directory")
                        )
                        notebooks = [notebook]
                else:
                    notebooks = [notebook]
                
                # Process each notebook
                results = []
                for nb_path in notebooks:
                    task = progress.add_task(
                        f"Exporting {nb_path.name}...", 
                        total=100
                    )
                    
                    try:
                        # Determine output path
                        if output:
                            output_path = output
                        else:
                            output_path = nb_path.with_suffix(
                                engine.get_file_extension(export_format)
                            )
                        
                        # Export notebook
                        progress.update(task, advance=20, description="Converting notebook...")
                        result = engine.export(
                            notebook_path=nb_path,
                            format=export_format,
                            output_path=output_path,
                            include_metadata=metadata,
                            template=template,
                            compress=compress,
                            export_as_assets=assets,
                        )
                        
                        # Handle cloud upload
                        if cloud_provider and cloud_bucket:
                            progress.update(task, advance=20, description="Uploading to cloud...")
                            storage = create_storage_provider(
                                cloud_provider,
                                bucket=cloud_bucket,
                            )
                            
                            # Determine cloud key
                            if cloud_key:
                                key = cloud_key
                            else:
                                key = f"exports/{nb_path.stem}/{output_path.name}"
                            
                            # Upload file
                            upload_result = storage.upload(
                                file_path=output_path,
                                key=key,
                                retention_days=retention_days,
                            )
                            
                            result["cloud_url"] = upload_result["url"]
                            result["cloud_key"] = key
                            
                            # Generate signed URL if supported
                            if hasattr(storage, "generate_signed_url"):
                                result["signed_url"] = storage.generate_signed_url(
                                    key, expiration_hours=24
                                )
                        
                        # Attach Dagster metadata
                        if dagster_url and result.get("dagster_metadata"):
                            progress.update(task, advance=20, description="Attaching metadata...")
                            attacher = MetadataAttacher(
                                dagster_url=dagster_url,
                                auth_token=dagster_token,
                            )
                            
                            metadata_result = attacher.attach_export_metadata(
                                asset_key=result["dagster_metadata"]["asset_key"],
                                export_url=result.get("cloud_url", str(output_path)),
                                format=format,
                                metadata=result["dagster_metadata"],
                            )
                            
                            if metadata_result:
                                result["metadata_attached"] = True
                        
                        progress.update(task, advance=40, description="Complete")
                        results.append(result)
                        
                    except Exception as e:
                        logger.error(f"Failed to export {nb_path}: {e}")
                        console.print(
                            format_error(f"Failed to export {nb_path.name}: {str(e)}")
                        )
                        progress.update(task, advance=100, description="Failed")
                        results.append({"path": str(nb_path), "error": str(e)})
                
                # Display results
                if results:
                    display_export_results(results, verbose)
                    
                    # Save batch results if multiple files
                    if len(results) > 1:
                        results_path = Path("export_results.json")
                        with open(results_path, "w") as f:
                            json.dump(results, f, indent=2, default=str)
                        console.print(
                            format_success(f"Batch results saved to {results_path}")
                        )
                        
        except Exception as e:
            logger.error(f"Export failed: {e}")
            console.print(format_error(f"Export failed: {str(e)}"))
            raise typer.Exit(1)


def display_export_results(results: List[Dict[str, Any]], verbose: bool = False) -> None:
    """Display export results in a formatted table."""
    table = Table(title="Export Results", show_lines=True)
    table.add_column("Notebook", style="cyan")
    table.add_column("Format", style="green")
    table.add_column("Output", style="yellow")
    table.add_column("Status", style="white")
    
    if verbose:
        table.add_column("Details", style="dim")
    
    for result in results:
        if "error" in result:
            status = "[red]✗ Failed[/red]"
            details = result.get("error", "Unknown error")
        else:
            status = "[green]✓ Success[/green]"
            details = []
            
            if result.get("cloud_url"):
                details.append(f"Cloud: {result['cloud_url']}")
            if result.get("signed_url"):
                details.append(f"Signed URL: {result['signed_url'][:50]}...")
            if result.get("metadata_attached"):
                details.append("Metadata: Attached")
            if result.get("compressed"):
                details.append(f"Compressed: {result['compression_ratio']:.1f}%")
            
            details = "\n".join(details) if details else "Exported successfully"
        
        row = [
            Path(result.get("path", "")).name,
            result.get("format", ""),
            Path(result.get("output_path", "")).name,
            status,
        ]
        
        if verbose:
            row.append(details)
            
        table.add_row(*row)
    
    console.print(table)
    
    # Summary statistics
    successful = len([r for r in results if "error" not in r])
    failed = len(results) - successful
    
    console.print(f"\n[bold]Summary:[/bold] {successful} successful, {failed} failed")


@app.command()
def batch(
    directory: Path = typer.Argument(
        ...,
        help="Directory containing notebooks to export",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
    ),
    pattern: str = typer.Option(
        "*.py",
        "--pattern",
        "-p",
        help="File pattern to match"
    ),
    format: str = typer.Option(
        "html",
        "--format",
        "-f",
        help="Export format for all notebooks"
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory for exports"
    ),
    **kwargs,
) -> None:
    """Batch export multiple notebooks.
    
    Examples:
        daglab export batch ./notebooks --format html
        daglab export batch ./notebooks --pattern "analysis_*.py" --output-dir ./exports
    """
    # Delegate to main export function with batch=True
    export(
        ctx=typer.Context(),
        notebook=directory,
        format=format,
        output=output_dir,
        batch=True,
        **kwargs,
    )


@app.command()
def cloud(
    notebook: Path = typer.Argument(..., help="Notebook to export"),
    provider: str = typer.Argument(..., help="Cloud provider (s3|gcs|azure)"),
    bucket: str = typer.Argument(..., help="Bucket name"),
    key: Optional[str] = typer.Option(None, help="Object key/path"),
    **kwargs,
) -> None:
    """Export directly to cloud storage.
    
    Examples:
        daglab export cloud notebook.py s3 my-bucket
        daglab export cloud notebook.py gcs reports-bucket --key 2024/january/report.html
    """
    export(
        ctx=typer.Context(),
        notebook=notebook,
        cloud_provider=provider,
        cloud_bucket=bucket,
        cloud_key=key,
        **kwargs,
    )


if __name__ == "__main__":
    app()

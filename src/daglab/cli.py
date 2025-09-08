"""Command-line interface for DAGLab."""

import click
from pathlib import Path
from typing import Optional
import json
import yaml

from daglab import __version__
from daglab.core import DAG
from daglab.visual import DAGVisualizer
from daglab.compute import LocalCompute, RayCompute, DaskCompute
from daglab.utils import setup_logging, get_logger

logger = get_logger(__name__)


@click.group()
@click.version_option(version=__version__)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def cli(verbose: bool) -> None:
    """DAGLab CLI - Build, execute, and analyze computational DAGs."""
    setup_logging(verbose=verbose)


@cli.command()
@click.argument('dag_file', type=click.Path(exists=True))
@click.option('--backend', '-b', type=click.Choice(['local', 'ray', 'dask']), default='local')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.option('--visualize', '-V', is_flag=True, help='Visualize DAG after execution')
def run(dag_file: str, backend: str, output: Optional[str], visualize: bool) -> None:
    """Execute a DAG from a file."""
    logger.info(f"Loading DAG from {dag_file}")
    
    # Load DAG from file
    dag_path = Path(dag_file)
    if dag_path.suffix == '.json':
        with open(dag_path) as f:
            dag_config = json.load(f)
    elif dag_path.suffix in ['.yaml', '.yml']:
        with open(dag_path) as f:
            dag_config = yaml.safe_load(f)
    else:
        raise click.BadParameter(f"Unsupported file format: {dag_path.suffix}")
    
    # Create DAG from config
    dag = DAG.from_dict(dag_config)
    
    # Select compute backend
    if backend == 'local':
        compute = LocalCompute()
    elif backend == 'ray':
        compute = RayCompute()
    elif backend == 'dask':
        compute = DaskCompute()
    
    # Execute DAG
    logger.info(f"Executing DAG '{dag.name}' with {backend} backend")
    result = compute.execute(dag)
    
    # Save output if requested
    if output:
        output_path = Path(output)
        with open(output_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        logger.info(f"Results saved to {output_path}")
    
    # Visualize if requested
    if visualize:
        visualizer = DAGVisualizer()
        visualizer.visualize(dag, show=True)
    
    click.echo(f"DAG execution completed successfully")


@cli.command()
@click.argument('dag_file', type=click.Path(exists=True))
@click.option('--format', '-f', type=click.Choice(['html', 'png', 'svg', 'interactive']), default='interactive')
@click.option('--output', '-o', type=click.Path(), help='Output file for visualization')
def visualize(dag_file: str, format: str, output: Optional[str]) -> None:
    """Visualize a DAG from a file."""
    logger.info(f"Loading DAG from {dag_file}")
    
    # Load DAG
    dag_path = Path(dag_file)
    if dag_path.suffix == '.json':
        with open(dag_path) as f:
            dag_config = json.load(f)
    elif dag_path.suffix in ['.yaml', '.yml']:
        with open(dag_path) as f:
            dag_config = yaml.safe_load(f)
    else:
        raise click.BadParameter(f"Unsupported file format: {dag_path.suffix}")
    
    dag = DAG.from_dict(dag_config)
    
    # Create visualization
    visualizer = DAGVisualizer()
    if format == 'interactive':
        visualizer.visualize(dag, show=True)
    else:
        if not output:
            output = f"{dag.name}_visualization.{format}"
        visualizer.save(dag, output, format=format)
        click.echo(f"Visualization saved to {output}")


@cli.command()
@click.option('--name', '-n', default='my_dag', help='Name for the new DAG')
@click.option('--template', '-t', type=click.Choice(['simple', 'ml-pipeline', 'etl', 'parallel']), default='simple')
@click.option('--output', '-o', type=click.Path(), default='dag.yaml', help='Output file')
def create(name: str, template: str, output: str) -> None:
    """Create a new DAG from a template."""
    templates = {
        'simple': {
            'name': name,
            'nodes': [
                {'id': 'input', 'type': 'function', 'function': 'lambda: {"value": 42}'},
                {'id': 'process', 'type': 'function', 'function': 'lambda x: {"result": x["value"] * 2}'},
                {'id': 'output', 'type': 'function', 'function': 'lambda x: print(f"Result: {x[\'result\']}")'},
            ],
            'edges': [
                {'source': 'input', 'target': 'process'},
                {'source': 'process', 'target': 'output'},
            ]
        },
        'ml-pipeline': {
            'name': name,
            'nodes': [
                {'id': 'data_load', 'type': 'function', 'function': 'load_data'},
                {'id': 'preprocess', 'type': 'function', 'function': 'preprocess_data'},
                {'id': 'train', 'type': 'function', 'function': 'train_model'},
                {'id': 'evaluate', 'type': 'function', 'function': 'evaluate_model'},
                {'id': 'deploy', 'type': 'function', 'function': 'deploy_model'},
            ],
            'edges': [
                {'source': 'data_load', 'target': 'preprocess'},
                {'source': 'preprocess', 'target': 'train'},
                {'source': 'train', 'target': 'evaluate'},
                {'source': 'evaluate', 'target': 'deploy'},
            ]
        }
    }
    
    dag_config = templates.get(template, templates['simple'])
    
    # Save to file
    output_path = Path(output)
    if output_path.suffix == '.json':
        with open(output_path, 'w') as f:
            json.dump(dag_config, f, indent=2)
    else:
        with open(output_path, 'w') as f:
            yaml.dump(dag_config, f, default_flow_style=False)
    
    click.echo(f"Created new DAG '{name}' from template '{template}' at {output_path}")


@cli.command()
@click.argument('dag_file', type=click.Path(exists=True))
def validate(dag_file: str) -> None:
    """Validate a DAG file."""
    logger.info(f"Validating DAG from {dag_file}")
    
    try:
        # Load DAG
        dag_path = Path(dag_file)
        if dag_path.suffix == '.json':
            with open(dag_path) as f:
                dag_config = json.load(f)
        elif dag_path.suffix in ['.yaml', '.yml']:
            with open(dag_path) as f:
                dag_config = yaml.safe_load(f)
        else:
            raise click.BadParameter(f"Unsupported file format: {dag_path.suffix}")
        
        dag = DAG.from_dict(dag_config)
        dag.validate()
        
        click.echo(f"✓ DAG '{dag.name}' is valid")
        click.echo(f"  - Nodes: {len(dag.nodes)}")
        click.echo(f"  - Edges: {len(dag.edges)}")
        click.echo(f"  - Is cyclic: No")
        
    except Exception as e:
        click.echo(f"✗ DAG validation failed: {str(e)}", err=True)
        raise click.Abort()


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
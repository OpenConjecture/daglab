# DagLab

> Scaffold and run paired marimo notebooks for Dagster assets & jobs

DagLab is a powerful CLI tool that bridges the gap between Dagster's robust orchestration capabilities and marimo's interactive notebook environment. It enables data engineers to scaffold, run, and round-trip paired notebooks alongside Dagster repositories, making experimentation feel notebook-native while keeping executions and artifacts visible in Dagster's UI.

## Features

- 🚀 **Quick Start**: Initialize DagLab in existing or new Dagster projects
- 📓 **Notebook Scaffolding**: Generate marimo notebooks from Dagster assets/jobs
- 🔄 **Seamless Integration**: Execute Dagster entities from notebooks
- 📊 **Rich UI**: Beautiful terminal output with progress indicators
- 🔐 **Security First**: Built-in security features and input validation
- ⚡ **Performance**: Optimized for speed with caching and async operations

## Installation

```bash
# Install from PyPI (coming soon)
pip install daglab

# Install in development mode
git clone https://github.com/openconjecture/daglab.git
cd daglab
pip install -e ".[dev]"
```

## Quick Start

### Initialize in an existing Dagster project

```bash
cd your-dagster-project
daglab init
```

### Create a new Dagster project with DagLab

```bash
daglab init my-project --create-project
cd my-project
```

### Run diagnostics

```bash
daglab doctor
```

## Project Structure

```
daglab/
├── src/daglab/         # Main package
│   ├── cli.py          # CLI commands
│   ├── config.py       # Configuration management
│   ├── runtime/        # Runtime utilities
│   ├── helpers/        # Helper utilities
│   └── templates/      # Notebook templates
├── tests/              # Test suite
└── docs/               # Documentation
```

## Configuration

DagLab uses a hierarchical configuration system:

1. **CLI arguments** (highest priority)
2. **Environment variables** (`DAGLAB_*` prefix)
3. **Config files** (`daglab.yaml`)
4. **Defaults** (lowest priority)

Example configuration:

```yaml
# daglab.yaml
version: "1.0"
notebooks_dir: dagster/notebooks

dagster:
  instance_url: http://localhost:3000
  use_cloud: false

marimo:
  port: 2718
  host: localhost

logging:
  level: INFO
  format: pretty
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Type checking
mypy src/daglab

# Linting and formatting
ruff check src/daglab
ruff format src/daglab
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=daglab --cov-report=html

# Specific test file
pytest tests/unit/test_config.py
```

## Architecture

DagLab is built with a modular architecture:

- **Configuration System**: Pydantic-based configuration with validation
- **CLI Framework**: Typer with Rich for beautiful terminal output
- **Runtime**: Logging, error handling, and telemetry
- **Security**: Input validation and sanitization
- **Templates**: Jinja2-based notebook generation

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Roadmap

- [x] Phase 1: Foundation & Core Infrastructure
- [x] Phase 2: CLI Framework & Basic Commands
- [x] Phase 3: Notebook Generation & Templates
- [x] Phase 4: Dagster Integration & GraphQL
- [x] Phase 5: Advanced Features & Polish
- [x] Phase 6: Packaging & Release

## Support

- Documentation: [docs.daglab.io](https://docs.daglab.io)
- Issues: [GitHub Issues](https://github.com/openconjecture/daglab/issues)
- Discussions: [GitHub Discussions](https://github.com/openconjecture/daglab/discussions)

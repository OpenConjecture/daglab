# Contributing to DagLab

We love your input! We want to make contributing to DagLab as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## We Develop with GitHub

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## We Use [GitHub Flow](https://guides.github.com/introduction/flow/index.html)

Pull requests are the best way to propose changes to the codebase. We actively welcome your pull requests:

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Development Process

### Setting up your environment

```bash
# Clone your fork
git clone https://github.com/your-username/daglab.git
cd daglab

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install
```

### Running tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=daglab --cov-report=html

# Run specific test file
pytest tests/test_core.py

# Run tests in parallel
pytest -n auto
```

### Code style

We use Black for code formatting and Ruff for linting:

```bash
# Format code
black src tests

# Check linting
ruff check src tests

# Fix linting issues
ruff check --fix src tests
```

### Type checking

We use mypy for static type checking:

```bash
mypy src/daglab
```

## Any contributions you make will be under the Apache 2.0 License

In short, when you submit code changes, your submissions are understood to be under the same [Apache 2.0 License](LICENSE) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using GitHub's [issues](https://github.com/daglab/daglab/issues)

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/daglab/daglab/issues/new); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Pull Request Process

1. Update the README.md with details of changes to the interface, this includes new environment variables, exposed ports, useful file locations and container parameters.
2. Update the CHANGELOG.md with your changes following the Keep a Changelog format.
3. Increase the version numbers in any examples files and the README.md to the new version that this Pull Request would represent.
4. You may merge the Pull Request in once you have the sign-off of two other developers, or if you do not have permission to do that, you may request the second reviewer to merge it for you.

## Code of Conduct

### Our Pledge

In the interest of fostering an open and welcoming environment, we as contributors and maintainers pledge to making participation in our project and our community a harassment-free experience for everyone.

### Our Standards

Examples of behavior that contributes to creating a positive environment include:

* Using welcoming and inclusive language
* Being respectful of differing viewpoints and experiences
* Gracefully accepting constructive criticism
* Focusing on what is best for the community
* Showing empathy towards other community members

### Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage], version 1.4,
available at http://contributor-covenant.org/version/1/4

[homepage]: http://contributor-covenant.org
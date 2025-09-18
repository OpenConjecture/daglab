# DagLab Release Process

This document outlines the process for releasing new versions of DagLab to PyPI.

## Prerequisites

1. **PyPI Account**: You need an account on [PyPI](https://pypi.org/) and [Test PyPI](https://test.pypi.org/)
2. **API Tokens**: Generate API tokens for both PyPI and Test PyPI
3. **Tools**: Ensure you have the necessary tools installed:
   ```bash
   pip install build twine
   ```

## Release Checklist

Before releasing, ensure:

- [ ] All tests pass: `pytest`
- [ ] Code is properly formatted: `black src tests`
- [ ] No linting errors: `ruff check src tests`
- [ ] Type checking passes: `mypy src/daglab`
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated with the new version
- [ ] Version number is updated (handled by setuptools_scm)

## Build Process

### 1. Clean Previous Builds

```bash
python scripts/build/build_dist.py --clean
```

### 2. Validate Package Structure

```bash
python scripts/validation/validate_package.py
```

### 3. Build Distributions

```bash
python scripts/build/build_dist.py
```

This will create:
- Source distribution (`.tar.gz`)
- Wheel distribution (`.whl`)

### 4. Test Installation

Test the built packages in isolated environments:

```bash
# Test basic installation
python scripts/build/test_install.py

# Test with specific extras
python scripts/build/test_install.py --extras aws --extras ml

# Test all extras
python scripts/build/test_install.py --extras aws --extras gcp --extras azure --extras ray --extras ml
```

## Publishing

### 1. Upload to Test PyPI (Recommended)

First, upload to Test PyPI to verify everything works:

```bash
twine upload --repository testpypi dist/*
```

Test installation from Test PyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ daglab
```

### 2. Upload to PyPI

Once verified on Test PyPI:

```bash
twine upload dist/*
```

### 3. Create GitHub Release

1. Tag the release:
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```

2. Create a release on GitHub:
   - Go to the repository's Releases page
   - Click "Create a new release"
   - Select the tag you just created
   - Add release notes from CHANGELOG.md
   - Upload the built distributions as release assets

## Post-Release

1. **Verify Installation**:
   ```bash
   pip install daglab
   python -c "import daglab; print(daglab.__version__)"
   ```

2. **Update Documentation**: Ensure the documentation site reflects the new version

3. **Announce**: Announce the release on relevant channels

## Automated Release (CI/CD)

For automated releases, you can set up GitHub Actions:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install build twine
      
      - name: Build distributions
        run: python -m build
      
      - name: Upload to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

## Troubleshooting

### Common Issues

1. **Version conflicts**: Ensure setuptools_scm is properly configured
2. **Missing files**: Check MANIFEST.in includes all necessary files
3. **Import errors**: Verify all dependencies are properly specified
4. **Platform-specific issues**: Test on multiple platforms before release

### Validation Commands

```bash
# Check package metadata
twine check dist/*

# Test in a clean environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate
pip install dist/*.whl
python -c "import daglab"
```

## Security Considerations

1. **Use API tokens** instead of passwords for PyPI
2. **Sign releases** with GPG when possible
3. **Verify checksums** of uploaded files
4. **Use 2FA** on PyPI account

## Version Management

DagLab uses `setuptools_scm` for version management:

- Version is automatically determined from git tags
- Development versions include commit hash
- No manual version updates needed

To check the current version:

```bash
python -c "from daglab import __version__; print(__version__)"
```
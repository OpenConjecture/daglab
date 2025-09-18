# Changelog

All notable changes to DagLab will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of DagLab
- Core DAG execution engine with async support
- Modular compute backends (Local, Ray)
- Pluggable storage backends (Local, S3, GCS, Azure)
- Cloud provider integrations (AWS, GCP, Azure)
- MLflow integration for experiment tracking
- GPU acceleration support via CUDA
- Comprehensive type safety with Pydantic
- Rich CLI interface for pipeline management
- Extensive documentation and examples

### Changed
- N/A (initial release)

### Deprecated
- N/A (initial release)

### Removed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- Implemented secure credential management
- Added input validation for all user inputs
- Encrypted storage for sensitive configuration

## [0.1.0] - 2024-01-01

- Initial development release

[Unreleased]: https://github.com/daglab/daglab/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/daglab/daglab/releases/tag/v0.1.0
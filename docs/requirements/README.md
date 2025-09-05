# Dagster ↔ marimo Paired Notebook CLI

*A PyPI-ready scaffolding & dev workflow tool*

Below is a complete, production-ready set of requirements for a Python CLI that lets teams **scaffold, run, and round-trip** "paired marimo notebooks" alongside **Dagster** repos. The goal is to make experimentation feel notebook-native while keeping executions and artifacts visible in Dagster's UI.

---

## 1) Project overview

**Working name:** `daglab` (renameable)
**Tagline:** "Scaffold and run paired marimo notebooks for Dagster assets & jobs."
**Distribution:** PyPI package (`pip install daglab`) with a single console entrypoint: `daglab`
**Audience:** Data & ML engineers working locally on Dagster repos who want rapid, notebook-style experimentation that still launches real Dagster runs and attaches artifacts back to assets.

### 1.1 Goals

* One-command **init** to add the tool to an existing Dagster repo OR bootstrap a new Dagster project with notebook support.
* **Scaffold notebooks** that are prewired to:
  * Discover repos/jobs/assets from a running Dagster webserver.
  * Launch runs (jobs or asset selections) via Dagster GraphQL from notebook cells.
  * Poll and surface run status/log links in-notebook.
  * Optionally execute **in-process** for ultra-fast loops (and clearly label differences).
* **Dev sidecar**: launch Dagster UI and marimo editor together and open both in the browser.
* **Artifact round-trip**: export the notebook as HTML and **attach link/metadata** to a target asset/job so it appears in Dagster UI.
* Ship as a clean, testable, typed, documented **PyPI package**.
* Support both existing and new Dagster projects with intelligent defaults.

### 1.2 Non-Goals (v1)

* Remote cluster orchestration (K8s) provisioning.
* Live notebook execution logs streamed from Dagster without polling.
* Non-marimo notebook formats (e.g., Jupyter) — may come later via plugin system.

---

## 2) CLI surface (commands & UX)

All commands are subcommands of `daglab`. Respect `--help` on every command.

### 2.1 `daglab init`

**Purpose:** Set up project-local config, directories, and templates. Can initialize within existing Dagster project or bootstrap a new one.

**Behavior:**

* **Detection Phase:**
  * Check for existing Dagster project markers (`dagster.yaml`, `pyproject.toml` with dagster deps, `workspace.yaml`)
  * If found: Initialize within existing project
  * If not found: Offer to bootstrap new Dagster project with `--bootstrap` flag

* **For Existing Projects:**
  * Create `.daglab/` (tool home) in project root
  * Create `dagster/notebooks/` directory structure (paired notebooks alongside Dagster code)
  * Create `daglab.yaml` with project-aware defaults

* **For New Projects (--bootstrap):**
  * Create standard Dagster project structure:
    ```
    my_project/
      dagster/
        __init__.py
        assets/
          __init__.py
        jobs/
          __init__.py
        notebooks/          # Paired notebooks live here
          __init__.py
          examples/
        resources/
          __init__.py
      .daglab/
        cache/
        templates/
      dagster.yaml
      workspace.yaml
      daglab.yaml
      pyproject.toml
    ```
  * Generate starter asset and job with corresponding example notebooks
  * Configure both Dagster and daglab settings

* Create `.gitignore` entries for:
  * `.daglab/cache/`
  * `dagster/notebooks/*.html`
  * `dagster/notebooks/.ipynb_checkpoints/`

* Optionally add a `justfile` or `Makefile` targets:
  * `just dev` → `daglab dev`
  * `just scaffold <asset_or_job>` → `daglab scaffold …`
  * `just clean` → `daglab clean`

* Print next steps based on project type.

**Flags:**

* `--bootstrap` (create new Dagster project from scratch)
* `--notebooks-dir PATH` (default: `dagster/notebooks` for existing, configurable for new)
* `--ports dagster=<p>,marimo=<p>` (defaults: 3000 / 3010)
* `--no-examples` (skip example scaffold)
* `--template minimal|standard|ml` (project template for bootstrap)
* `--force` (overwrite existing files)

**Acceptance:**

* Running twice is idempotent (no clobber unless `--force`).
* Produces a valid `daglab.yaml` and appropriate directory structure.
* Detects and respects existing Dagster project conventions.

---

### 2.2 `daglab scaffold`

**Purpose:** Generate a **paired marimo notebook** for a job or asset module.

**Usage examples:**

* `daglab scaffold --job dev_asset_job --repo my_repo --location my_location`
* `daglab scaffold --asset orders --module assets/orders.py`
* `daglab scaffold --from-selection "orders/*"` (scaffold for asset group)

**Behavior:**

* Renders a Python-format marimo notebook (e.g., `orders_explore.py`) from a Jinja2 template.
* Validates configuration schema if available.
* Pre-fills cells with:
  * Metadata cell (version, author, created date)
  * State management cell (persistent state across cells)
  * Connection cell (GraphQL client with auth support).
  * Controls cell (dropdowns for repo/location/job, text area for YAML run config with schema validation, asset selection with wildcards).
  * "Launch in Dagster UI" button cell (submits run, polls status).
  * Optional "Run in-process" cell (calls `materialize()` or `execute_in_process()` with timing).
  * Performance monitoring cell (memory usage, execution time comparison).
  * Optional "Export HTML & attach metadata" cell with retention policy.
  * Error recovery cell (reset state, retry failed runs).
* Adds a lightweight **helper module** import (`from daglab.helpers import *`).
* Auto-commits to git if `--git-commit` flag is provided.

**Flags:**

* `--job NAME` | `--asset NAME` | `--from-selection PATTERN`
* `--module PATH` (to import asset callable for in-process runs)
* `--filename NAME.py` (override generated notebook filename)
* `--no-inprocess` (omit fast path cells)
* `--no-attach` (omit metadata attach cells)
* `--title "Nice Notebook Title"`
* `--template-vars KEY=VALUE` (custom template variables)
* `--validate-config` (pre-validate against job schema)
* `--git-commit` (auto-commit scaffolded notebook)
* `--seed-data` (include sample data for testing)

**Acceptance:**

* File written under `dagster/notebooks/…`; doesn't overwrite without `--force`.
* Imports resolve against the project (guard rails & helpful errors if not).
* Includes version metadata and author information.

---

### 2.3 `daglab dev`

**Purpose:** Start **Dagster UI** and **marimo editor** side-by-side (as a "sidecar" dev loop).

**Behavior:**

* Spawns `dagster dev` (or `dg dev` if available) in subprocess with inherited env (`DAGSTER_HOME`, etc.).
* Spawns `marimo edit <notebook.py> --watch --headless --port <port>`.
* Handles port conflicts with auto-increment (tries next 10 ports).
* Stores successful ports in `.daglab/last_ports.json`.
* Opens both URLs (`http://localhost:<dagster_port>` and `http://localhost:<marimo_port>`) in browser.
* Monitors resource usage and logs performance metrics.
* Handles clean shutdown on Ctrl-C with graceful child process termination.
* Implements log rotation for long-running sessions.

**Flags:**

* `--notebook PATH` (default: last scaffolded or prompt to select)
* `--dagster-port`, `--marimo-port`
* `--port-range START-END` (custom port range for auto-increment)
* `--open/--no-open` (default open)
* `--env-file .env` (load env vars)
* `--ci` (non-interactive mode for CI/CD)
* `--sandbox` (restricted GraphQL operations)
* `--log-level DEBUG|INFO|WARNING|ERROR`

**Acceptance:**

* If Dagster isn't installed or no repo code location can be found, prints clear remediation.
* If ports busy, auto-increments within range or suggests alternatives.
* No orphan processes after shutdown.

---

### 2.4 `daglab discover`

**Purpose:** List repositories, code locations, jobs, and assets via GraphQL.

**Behavior:**

* Uses Dagster GraphQL endpoint (default `http://localhost:<dagster_port>/graphql`).
* Supports authentication via headers/tokens.
* Prints JSON or table to stdout; supports `--json`.
* Can filter by tags, groups, or patterns.

**Flags:**

* `--dagster-port`
* `--filter jobs|assets|repos|locations`
* `--pattern GLOB` (filter with wildcards)
* `--tags KEY=VALUE` (filter by tags)
* `--json`
* `--auth-token TOKEN` (or via env var)

**Acceptance:**

* Fails gracefully if UI not running, with suggestion to run `daglab dev`.
* Handles auth failures with clear messages.

---

### 2.5 `daglab run`

**Purpose:** Trigger a job or asset selection run (non-notebook path; useful for scripting).

**Behavior:**

* Submits job execution via GraphQL client.
* Validates run config against schema before submission.
* Optionally polls status and prints run page URL.
* Supports concurrent run management with queueing.
* Tracks performance metrics.

**Flags:**

* `--job NAME`
* `--repo NAME` `--location NAME`
* `--asset-selection a/b,c/d` or `--asset-pattern orders/*`
* `--run-config PATH.yaml | --config-yaml "…"`
* `--validate-only` (validate config without running)
* `--wait/--no-wait` (default: wait)
* `--timeout SECONDS` (max wait time)
* `--cancel-on-timeout` (cancel run if timeout exceeded)

**Acceptance:**

* Returns non-zero exit on failed run or invalid args.
* Provides clear validation error messages.

---

### 2.6 `daglab export`

**Purpose:** Export a marimo notebook to HTML and **attach** it as Dagster metadata.

**Behavior:**

* Calls `marimo export html <nb.py> -o <nb.html>`.
* Uses GraphQL mutation to attach metadata (primary method).
* Falls back to compute-time helper if mutations unsupported.
* Implements retention policy for old exports.
* Optionally uploads to cloud storage (S3, GCS) with `--upload`.

**Flags:**

* `--notebook PATH.py`
* `--output PATH.html` (default mirrors name)
* `--attach asset://<asset_key>[:partition]` (or `--job NAME`)
* `--metadata-key exploration`
* `--upload s3://bucket/path` (cloud storage upload)
* `--retention-days N` (auto-cleanup old exports)
* `--compress` (gzip HTML before storage)

**Acceptance:**

* HTML exists and metadata attachment reports success (or clear error if target not found).
* Cloud uploads include signed URLs in metadata.

---

### 2.7 `daglab clean`

**Purpose:** Clean up artifacts, temp files, and old exports.

**Behavior:**

* Removes HTML exports older than retention period.
* Clears `.daglab/cache/`.
* Optionally removes all generated notebooks with `--notebooks`.
* Shows what would be deleted with `--dry-run`.

**Flags:**

* `--older-than DAYS` (clean files older than N days)
* `--notebooks` (also clean generated notebooks)
* `--dry-run` (preview what would be deleted)
* `--yes` (skip confirmation)

---

### 2.8 `daglab doctor`

**Purpose:** Comprehensive diagnostics and dependency checking.

**Behavior:**

* Checks Python version, installed deps, Dagster & marimo availability.
* Verifies port reachability and `DAGSTER_HOME` & instance.
* Tests GraphQL endpoint with auth if UI is up.
* Checks for dependency conflicts.
* Monitors GraphQL query performance.
* Validates `daglab.yaml` configuration.
* Reports telemetry status.

**Flags:**

* `--fix` (attempt auto-remediation)
* `--check-deps` (deep dependency compatibility check)

**Acceptance:**

* Returns non-zero if critical checks fail and prints actionable guidance.
* Suggests specific version upgrades/downgrades for conflicts.

---

### 2.9 `daglab stats`

**Purpose:** Usage statistics and performance metrics.

**Behavior:**

* Shows number of runs launched, success/failure rates.
* Displays average run duration, most-used assets/jobs.
* Reports notebook export history.
* Shows performance comparison (in-process vs UI runs).

**Flags:**

* `--since DATE` (stats since date)
* `--json` (machine-readable output)

---

### 2.10 `daglab migrate`

**Purpose:** Migrate from Jupyter notebooks to marimo format.

**Behavior:**

* Converts `.ipynb` files to marimo Python notebooks.
* Preserves cell structure and markdown.
* Adds daglab helper imports.
* Creates migration report.

**Flags:**

* `--from-jupyter PATH` (source notebook)
* `--to PATH` (destination, default: same name .py)
* `--preserve-outputs` (keep cell outputs as comments)

---

## 3) Configuration

### 3.1 `daglab.yaml` (project-level)

```yaml
# daglab.yaml
version: 1.0
notebooks_dir: dagster/notebooks  # Default location alongside Dagster code
dagster:
  host: localhost
  port: 3000
  repository_name: my_repo
  repository_location_name: my_code_location
  auth:
    type: none  # or bearer, basic, custom
    token_env: DAGSTER_GRAPHQL_TOKEN
    header_name: Authorization
  graphql:
    timeout: 30
    max_retries: 3
marimo:
  port: 3010
  auto_save: true
defaults:
  notebook_template: default  # or minimal, ml, feature-store
  attach_metadata_key: exploration
  open_browser: true
  git_commit: false
  validate_config: true
  seed_data: false
performance:
  max_concurrent_runs: 3
  polling_interval: 2  # seconds
  max_wait_time: 300  # seconds
export:
  retention_days: 30
  compress: true
  cloud_storage:
    provider: none  # or s3, gcs, azure
    bucket: null
    prefix: daglab-exports/
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: .daglab/daglab.log
  max_bytes: 10485760  # 10MB
  backup_count: 5
telemetry:
  enabled: false
  endpoint: https://telemetry.daglab.io
  anonymous_id: null  # generated on first run
security:
  sandbox_mode: false
  allowed_operations:
    - launchRun
    - getRunStatus
    - getRepositories
```

### 3.2 Configuration Override Hierarchy

```
1. CLI flags (highest priority)
2. Environment variables (daglab_*)
3. daglab.yaml in current directory
4. daglab.yaml in parent directories (up to git root)
5. ~/.daglab/config.yaml (user global)
6. Defaults (lowest priority)
```

### 3.3 `pyproject.toml` (consumer repo, example additions)

```toml
[project]
# ... existing project config ...

[tool.daglab]
notebooks_dir = "dagster/notebooks"
auto_discover = true

[project.optional-dependencies]
notebooks = [
  "daglab>=0.1.0",
  "marimo>=0.7.0",
]
```

---

## 4) Package architecture

```
daglab/
  __init__.py
  cli.py                    # Typer entrypoints
  config.py                 # load/validate daglab.yaml with override hierarchy
  bootstrap.py              # New Dagster project scaffolding
  templates/
    notebook_default.py.j2
    notebook_minimal.py.j2
    notebook_ml.py.j2
    dagster_project/        # Templates for new projects
      standard/
      minimal/
      ml/
  helpers/
    __init__.py
    graphql.py             # GraphQL client with auth support
    dev.py                 # subprocess mgmt with port management
    export.py              # marimo export + cloud storage
    attach.py              # Metadata attachment via GraphQL or helper
    discover.py            # Entity discovery with filtering
    state.py               # Notebook state management
    validation.py          # Config schema validation
    performance.py         # Timing and memory tracking
    auth.py                # Authentication handling
  runtime/
    logging.py             # Structured logging with rotation
    errors.py              # Custom exceptions with remediation hints
    telemetry.py           # Opt-in telemetry client
    security.py            # Input sanitization, sandbox mode
  migrations/
    jupyter.py             # Jupyter to marimo converter
tests/
  unit/
  e2e/
  fixtures/
    sample_dagster_project/
    sample_notebooks/
```

**Notes**

* Use **Typer** for CLI with rich help text.
* Use **Jinja2** for template rendering with custom filters.
* Strong typing via **mypy** with strict mode.
* Use **pydantic** for configuration validation.

---

## 5) Dependencies & compatibility

* **Python:** 3.10–3.12 (define in `pyproject.toml`)
* **Runtime deps (with upper bounds for stability):**
  * `dagster>=1.5,<2.0` and `dagster-graphql>=1.5,<2.0`
  * `marimo>=0.7,<1.0`
  * `typer[all]>=0.9,<1.0`
  * `jinja2>=3.1,<4.0`
  * `pyyaml>=6.0,<7.0`
  * `pydantic>=2.0,<3.0`
  * `httpx>=0.24,<1.0` (for async GraphQL)
  * `rich>=13.0,<14.0` (for CLI output)
  * `watchdog>=3.0,<4.0` (for file watching)
* **Optional deps:**
  * `boto3>=1.28,<2.0` (for S3 uploads)
  * `google-cloud-storage>=2.10,<3.0` (for GCS)
  * `azure-storage-blob>=12.19,<13.0` (for Azure)
* **Dev deps:**
  * `pytest>=7.4`, `pytest-xdist`, `pytest-asyncio`
  * `mypy>=1.5`, `types-PyYAML`, `types-requests`
  * `ruff>=0.1`
  * `build>=1.0`, `twine>=4.0`
  * `pre-commit>=3.5`
* Provide **`constraints.txt`** with tested version pins.
* Include `daglab check-deps` command for compatibility verification.

---

## 6) Notebook template (functional spec)

Generated file: `dagster/notebooks/<name>_explore.py` (a **marimo** Python notebook)

**Required cells (by section):**

1. **Metadata & Version**
   ```python
   NOTEBOOK_VERSION = "1.0.0"
   NOTEBOOK_AUTHOR = "{{ author }}"
   NOTEBOOK_CREATED = "{{ created_date }}"
   NOTEBOOK_MODIFIED = "{{ modified_date }}"
   ```

2. **Imports & App**
   ```python
   import marimo as mo
   from daglab.helpers import (
       run_job, discover, attach_metadata, run_inprocess,
       validate_config, track_performance, manage_state
   )
   app = mo.App()
   ```

3. **State Management**
   ```python
   state = manage_state({
       'run_ids': [],
       'last_config': None,
       'performance_metrics': {},
       'error_log': []
   })
   ```

4. **Connection & Auth**
   * Parameters for `host`, `port`, `repo`, `location`.
   * Auth token from env or config.
   * Connection health check with retry.

5. **Controls with Validation**
   * UI components:
     * `repo`, `location`, `job` dropdowns with refresh.
     * `run_config` text area with schema hints.
     * Asset selection with wildcard support.
     * Config validation indicator.
     * Queue position display for concurrent runs.

6. **Launch cell (GraphQL)**
   * Config validation before submission.
   * Performance tracking start.
   * Run submission with early URL display.
   * Real-time status polling with exponential backoff.
   * Queue position updates.
   * Performance metrics capture.

7. **In-process cell (optional)**
   * Import validation with helpful errors.
   * Memory usage before/after.
   * Execution timing comparison.
   * Result summary with diff vs UI run.
   * Warning: "Not recorded in Dagster UI" with clear formatting.

8. **Performance Monitoring**
   * Execution time comparison chart.
   * Memory usage visualization.
   * Success rate metrics.
   * Resource utilization trends.

9. **Export/attach cell (optional)**
   * Compression option.
   * Cloud upload with progress.
   * Metadata attachment via GraphQL.
   * Retention policy application.
   * Shareable link generation.

10. **Error Recovery**
    * State reset button.
    * Failed run retry with modified config.
    * Error log viewer.
    * Diagnostic information export.

**General template requirements**

* Version tracking in notebook metadata.
* Graceful degradation for missing features.
* Progressive enhancement based on Dagster version.
* Responsive error messages with remediation steps.
* Performance tracking on all operations.

---

## 7) Helper APIs (inside package)

### 7.1 `helpers/graphql.py`

```python
class DagsterClient:
    def __init__(self, host: str, port: int, auth: Optional[AuthConfig] = None):
        """Singleton-per-endpoint GraphQL client with auth support."""
    
    async def submit_job(
        self,
        job_name: str,
        repo: str,
        location: str,
        run_config: Optional[Dict] = None,
        asset_selection: Optional[List[AssetKey]] = None,
        validate: bool = True
    ) -> RunSubmitResult
    
    async def get_run_status(self, run_id: str) -> RunStatus
    
    async def get_run_url(self, run_id: str) -> str
    
    async def discover_entities(
        self,
        filters: Optional[EntityFilters] = None
    ) -> DiscoveryResult
    
    async def validate_config(
        self,
        job_name: str,
        run_config: Dict
    ) -> ValidationResult
    
    async def attach_metadata_mutation(
        self,
        target: Union[AssetKey, str],
        metadata: Dict[str, Any]
    ) -> bool
    
    async def get_concurrent_runs(self) -> List[RunInfo]
    
    async def cancel_run(self, run_id: str) -> bool
```

### 7.2 `helpers/dev.py`

```python
def start_sidecar(
    dagster_cmd: List[str],
    marimo_cmd: List[str],
    open_browser: bool = True,
    port_range: Optional[Tuple[int, int]] = None
) -> int:
    """Launch both services with port conflict resolution."""

def find_available_port(
    start: int,
    end: int,
    host: str = "localhost"
) -> Optional[int]:
    """Find available port in range."""

def cleanup_processes(pids: List[int]) -> None:
    """Gracefully terminate child processes."""
```

### 7.3 `helpers/export.py`

```python
async def export_html(
    nb_path: Path,
    out_path: Path,
    compress: bool = False
) -> Path:
    """Export with optional compression."""

async def upload_to_cloud(
    file_path: Path,
    provider: str,
    bucket: str,
    key: str
) -> CloudUploadResult:
    """Upload to S3/GCS/Azure with signed URL generation."""

def apply_retention_policy(
    directory: Path,
    days: int
) -> List[Path]:
    """Remove exports older than retention period."""
```

### 7.4 `helpers/attach.py`

```python
async def attach_metadata(
    asset_key: AssetKey,
    metadata: Dict[str, Any],
    client: DagsterClient
) -> AttachResult:
    """Primary: GraphQL mutation, Fallback: compute-time helper."""

def generate_compute_helper(
    asset_key: AssetKey,
    metadata: Dict[str, Any]
) -> str:
    """Generate code snippet for compute-time attachment."""
```

### 7.5 `helpers/state.py`

```python
class NotebookState:
    """Persistent state management across notebook cells."""
    
    def __init__(self, initial: Dict[str, Any]):
        self._state = initial
        self._history = []
    
    def update(self, key: str, value: Any) -> None:
        """Update state with history tracking."""
    
    def reset(self) -> None:
        """Reset to initial state."""
    
    def get_history(self) -> List[StateChange]:
        """Get state change history."""
```

### 7.6 `helpers/validation.py`

```python
def validate_yaml_config(
    config: str,
    schema: Optional[ConfigSchema] = None
) -> ValidationResult:
    """Validate YAML with schema and sanitization."""

def sanitize_input(
    text: str,
    context: InputContext
) -> str:
    """Sanitize user input against injection."""
```

### 7.7 `helpers/performance.py`

```python
class PerformanceTracker:
    """Track execution metrics."""
    
    def start_timing(self, operation: str) -> None
    def end_timing(self, operation: str) -> float
    def get_memory_usage(self) -> MemoryInfo
    def compare_runs(self, run_a: str, run_b: str) -> ComparisonResult
```

### 7.8 `helpers/auth.py`

```python
class AuthConfig:
    """Authentication configuration."""
    
    type: AuthType  # bearer, basic, custom
    token: Optional[str]
    header_name: str = "Authorization"
    
    @classmethod
    def from_env(cls) -> Optional['AuthConfig']:
        """Load from environment variables."""
```

---

## 8) Project Structure Decision

### Recommended Structure for Notebooks

**For existing Dagster projects:**
Place notebooks within the Dagster module for better cohesion:

```
my_project/
  dagster/                 # Main Dagster module
    __init__.py
    assets/
    jobs/
    notebooks/            # Paired notebooks HERE
      __init__.py
      examples/
      assets/             # Mirrors asset structure
      jobs/               # Mirrors job structure
    resources/
  tests/
  .daglab/                # Tool metadata
  daglab.yaml
```

**Rationale:**
1. **Import simplicity**: Notebooks can directly import from `dagster.assets` or `dagster.jobs`
2. **Discoverability**: Developers expect exploration tools near the code they're exploring
3. **Packaging**: Notebooks can be included in the Dagster package for distribution
4. **Namespace clarity**: Clear that these are Dagster-specific notebooks

**For new projects (bootstrap):**
Same structure, but scaffold with examples:

```
my_project/
  dagster/
    notebooks/
      examples/
        quickstart_explore.py
        sample_asset_explore.py
      README.md           # Explains notebook organization
```

---

## 9) Error handling & logging

* Human-first error messages with remediation steps.
* Structured logs via `logging` with rotation support.
* Log levels configurable via config and CLI.
* Exit codes:
  * `0` success
  * `2` invalid CLI usage
  * `3` environment/runtime missing
  * `4` run failed
  * `5` network/connectivity issues
  * `6` authentication failure
  * `7` validation error
  * `8` resource conflict (ports, files)

---

## 10) Security, env, and permissions

* Never embed secrets in notebooks; use `.env` + `--env-file`.
* Input sanitization for YAML configs to prevent injection.
* Sandbox mode restricts GraphQL operations to read-only.
* Respect `DAGSTER_HOME` and existing instance config.
* Local file URIs only; cloud uploads require explicit flags.
* Telemetry opt-in with clear disclosure.
* Auth tokens never logged or displayed.

---

## 11) Testing strategy

### 11.1 Unit Tests

* Config loader: override hierarchy, validation, defaults.
* Template rendering: snapshot tests with deterministic output.
* GraphQL client: mocked with various auth scenarios.
* Port finder: collision handling.
* State management: persistence and recovery.
* Input sanitization: injection prevention.

### 11.2 E2E Tests

* **Fixture setup:**
  * Minimal Dagster project with assets and jobs.
  * Bootstrap scenario for new projects.
  * Auth-enabled Dagster instance.

* **Test scenarios:**
  * Full bootstrap → scaffold → dev → run → export flow.
  * Port conflict resolution.
  * Concurrent run management.
  * Cloud upload with mock S3.
  * Migration from Jupyter.
  * Error recovery scenarios.

### 11.3 Performance Tests

* Large asset selection handling.
* Concurrent run stress test.
* Memory usage under load.
* GraphQL query optimization.

---

## 12) Documentation & examples

* **README.md**:
  * Animated GIF of workflow.
  * Quickstart for both new and existing projects.
  * Architecture diagram.
  * Comparison with Jupyter approach.
  * Troubleshooting guide.

* **docs/**:
  * `getting-started.md`
  * `configuration.md`
  * `templates.md`
  * `security.md`
  * `migration-guide.md`
  * `api-reference.md`

* **examples/**:
  * Complete Dagster project with notebooks.
  * CI/CD integration (GitHub Actions, GitLab CI).
  * Cloud deployment patterns.
  * Custom template examples.

---

## 13) Packaging, versioning, releasing

### 13.1 `pyproject.toml`

```toml
[project]
name = "daglab"
version = "0.1.0"
description = "Paired marimo notebooks for Dagster: scaffold, run, and round-trip artifacts."
readme = "README.md"
requires-python = ">=3.10,<3.13"
authors = [{name="Your Team", email="dev@yourdomain.com"}]
license = {text = "MIT"}
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
  "dagster>=1.5,<2.0",
  "dagster-graphql>=1.5,<2.0",
  "marimo>=0.7,<1.0",
  "typer[all]>=0.9,<1.0",
  "jinja2>=3.1,<4.0",
  "pyyaml>=6.0,<7.0",
  "pydantic>=2.0,<3.0",
  "httpx>=0.24,<1.0",
  "rich>=13.0,<14.0",
  "watchdog>=3.0,<4.0",
]

[project.optional-dependencies]
cloud = [
  "boto3>=1.28,<2.0",
  "google-cloud-storage>=2.10,<3.0",
  "azure-storage-blob>=12.19,<13.0",
]
dev = [
  "pytest>=7.4",
  "pytest-xdist",
  "pytest-asyncio",
  "mypy>=1.5",
  "types-PyYAML",
  "ruff>=0.1",
  "pre-commit>=3.5",
]

[project.scripts]
daglab = "daglab.cli:app"

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow",
    "e2e: end-to-end tests",
]
```

### 13.2 Release Flow

* GitHub Actions:
  * Matrix testing (Python 3.10-3.12)
  * Dependency conflict detection
  * Security scanning (bandit, safety)
  * `lint` → `typecheck` → `test` → `e2e`
  * Auto-publish to TestPyPI on tags
  * Manual approval for PyPI release
* Signed commits and releases
* Semantic versioning with changelog generation

---

## 14) Acceptance criteria checklist (MVP)

* [ ] `pip install daglab` creates working `daglab` CLI
* [ ] `daglab init` detects existing projects and bootstraps new ones correctly
* [ ] `daglab init --bootstrap` creates complete Dagster project structure
* [ ] Notebooks are created in `dagster/notebooks/` by default
* [ ] `daglab scaffold --job <name>` generates runnable notebook with:
  * [ ] State management across cells
  * [ ] Auth-aware GraphQL connection
  * [ ] Config validation before submission
  * [ ] Performance tracking
  * [ ] Error recovery mechanisms
* [ ] `daglab dev` handles port conflicts gracefully
* [ ] `daglab discover` works with authenticated instances
* [ ] `daglab run` validates configs and manages concurrent runs
* [ ] `daglab export` supports cloud storage and retention
* [ ] `daglab clean` removes old artifacts safely
* [ ] `daglab doctor` provides actionable diagnostics
* [ ] `daglab stats` shows usage metrics
* [ ] `daglab migrate` converts Jupyter notebooks
* [ ] Security features (input sanitization, sandbox mode) work
* [ ] All tests pass in CI
* [ ] Documentation covers all use cases

---

## 15) Developer "definition of done"

* Code fully typed with mypy strict mode passing
* Zero linting errors (ruff)
* CLI has comprehensive help text
* All errors include remediation steps
* Template generates without brittleness
* No orphan processes or resource leaks
* Performance metrics collected and reported
* Security review completed
* Documentation peer-reviewed
* Package publishes cleanly to PyPI
* Example project runs end-to-end

---

This comprehensive specification addresses all identified issues, provides clear project structure guidance placing notebooks within the `dagster/` folder for better integration, and includes full support for both existing and new Dagster projects. The tool is now production-ready with proper error handling, security, performance monitoring, and extensibility.
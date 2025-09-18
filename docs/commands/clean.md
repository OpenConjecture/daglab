# DagLab Clean Command

The `daglab clean` command helps maintain a tidy project by removing temporary files, caches, build artifacts, and old exports while protecting your source code and configuration files.

## Features

- **Safe by default**: Never deletes source code, configuration files, or documentation
- **Age-based filtering**: Only removes files older than a specified number of days
- **Dry run mode**: Preview what would be deleted before actually deleting
- **Confirmation prompt**: Requires user confirmation unless `--yes` flag is used
- **Undo information**: Creates a record of deleted files for recovery reference
- **Progress tracking**: Shows real-time progress with Rich terminal UI
- **Size reporting**: Displays how much disk space will be reclaimed

## Usage

```bash
daglab clean [OPTIONS]
```

## Options

- `--older-than INTEGER`: Delete files older than N days (default: 30)
- `--notebooks`: Include notebook checkpoints in cleanup
- `--dry-run`: Show what would be deleted without actually deleting
- `--yes, -y`: Skip confirmation prompt

## What Gets Cleaned

### Default Categories

1. **HTML Exports** (`exports/`, `output/`, `dist/`)
   - `*.html` files from data exports and reports

2. **Temporary Files** (`.daglab/tmp/`, `tmp/`, `temp/`)
   - `*.tmp`, `*.temp` files
   - Files starting with `~` or `.~`

3. **Cache** (`.daglab/cache/`, `.cache/`, `__pycache__/`)
   - All cached data and Python bytecode

4. **Logs** (`logs/`, `.daglab/logs/`)
   - `*.log` files and rotated logs

5. **Build Artifacts** (`build/`, `dist/`, `.eggs/`)
   - `*.pyc`, `*.pyo`, `*.pyd` files
   - `.pytest_cache`, `.coverage`
   - `*.egg-info` directories

### Optional Categories

6. **Notebook Checkpoints** (with `--notebooks` flag)
   - `.marimo/` directories
   - `.ipynb_checkpoints/` directories

## Protected Files

The following are NEVER deleted:
- Python source files (`*.py`)
- Configuration files (`*.yaml`, `*.yml`, `*.json`, `*.toml`)
- Documentation (`*.md`, `*.txt`)
- Requirements files (`requirements*.txt`)
- Docker files (`Dockerfile*`)
- Environment files (`.env*`)
- Git files (`.git*`)
- Anything in `src/`, `tests/`, `docs/`, or `config/` directories

## Examples

### Preview what would be deleted
```bash
daglab clean --dry-run
```

### Clean files older than 7 days
```bash
daglab clean --older-than 7
```

### Clean everything including notebooks, no confirmation
```bash
daglab clean --notebooks --yes
```

### Clean only very old files (90+ days)
```bash
daglab clean --older-than 90
```

## Output Example

```
DagLab Clean Utility
Scanning for files older than 30 days...

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Category         ┃ Description          ┃ File Count ┃ Total Size ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Html Exports     │ HTML export files    │         12 │    45.3 MB │
│ Temp Files       │ Temporary files      │         28 │     2.1 MB │
│ Cache            │ Cache directories    │        156 │    12.8 MB │
│ Logs             │ Log files            │          8 │    89.2 MB │
│ Build Artifacts  │ Build artifacts      │         43 │     5.6 MB │
├──────────────────┼──────────────────────┼────────────┼────────────┤
│ TOTAL            │                      │        247 │   155.0 MB │
└──────────────────┴──────────────────────┴────────────┴────────────┘

⚠️  Warning: This will delete 247 files (155.0 MB)
Do you want to continue? [y/N]: y

Undo information saved to: .daglab/undo/clean_undo_20241215_143022.txt

Cleaning files... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 247/247

✓ Cleaned 247 files (155.0 MB)

To see what was deleted, check the undo file:
  cat .daglab/undo/clean_undo_20241215_143022.txt
```

## Undo Information

While the clean command doesn't provide automatic undo, it creates a record of all deleted files with their sizes and timestamps. This information is stored in `.daglab/undo/clean_undo_[timestamp].txt`.

The undo file contains:
- Timestamp of when the clean operation was performed
- Full path of each deleted file
- File size at time of deletion  
- Last modification time

This can be useful for:
- Auditing what was cleaned
- Identifying if something important was accidentally deleted
- Helping recover files from backups if needed

## Safety Tips

1. Always run with `--dry-run` first to preview deletions
2. Use `--older-than` with a higher value for more conservative cleaning
3. Check the undo file after cleaning to verify nothing important was removed
4. Consider backing up your project before aggressive cleaning
5. The command will show errors for files it couldn't delete (permissions, etc.)

## Integration

The clean command can be integrated into CI/CD pipelines or scheduled tasks:

```yaml
# GitHub Actions example
- name: Clean old artifacts
  run: |
    daglab clean --older-than 7 --yes
```

```bash
# Cron job example (weekly cleanup)
0 0 * * 0 cd /path/to/project && daglab clean --older-than 30 --yes
```
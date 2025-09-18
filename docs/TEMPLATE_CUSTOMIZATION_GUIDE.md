# DagLab Template Customization Guide

## Overview

DagLab's template system is built on Jinja2 and provides powerful customization capabilities for generating marimo notebooks. This guide covers how to create, modify, and use custom templates.

## Template System Architecture

### Built-in Templates

DagLab includes three built-in templates:

1. **Default Template** - Full-featured notebook with all capabilities
2. **Minimal Template** - Lightweight notebook for quick exploration
3. **ML Template** - Specialized for machine learning workflows

### Template Structure

```
src/daglab/templates/
├── notebooks/           # Main notebook templates
│   ├── notebook_default.py.j2
│   ├── notebook_minimal.py.j2
│   └── notebook_ml.py.j2
├── partials/           # Reusable components
│   ├── _imports.j2
│   ├── _metadata.j2
│   ├── _connection.j2
│   ├── _state.j2
│   └── _run_controls.j2
└── base/               # Base templates for inheritance
    └── notebook_base.ipynb.j2
```

## Creating Custom Templates

### 1. Template Location

Custom templates can be placed in:
- `~/.daglab/templates/` (user-specific)
- `PROJECT_ROOT/.daglab/templates/` (project-specific)
- Any directory specified in `daglab.yaml`

### 2. Template Structure

A marimo notebook template should include these sections:

```python
# {{ template_name }} - {{ title }}
"""
{{ description }}

Generated: {{ created_date }}
Author: {{ author }}
Target: {{ target_type }}:{{ target_name }}
"""

import marimo as mo
{% include 'partials/_imports.j2' %}

app = mo.App()

{% include 'partials/_metadata.j2' %}

{% include 'partials/_connection.j2' %}

{% include 'partials/_state.j2' %}

# Your custom content here
{% block content %}
{% endblock %}

{% include 'partials/_run_controls.j2' %}
```

### 3. Template Variables

All templates have access to these context variables:

#### Metadata Variables
- `notebook_version` - Template version
- `author` - Current user
- `created_date` - ISO timestamp
- `target_type` - "job", "asset", or "selection"
- `target_name` - Name of the target
- `template_name` - Template being used
- `title` - Custom title or auto-generated
- `description` - Template description

#### Configuration Variables
- `dagster_host` - Dagster instance host
- `dagster_port` - Dagster instance port
- `repository_name` - Dagster repository name
- `location_name` - Repository location name
- `auth_config` - Authentication configuration
- `marimo_port` - Marimo server port

#### Feature Flags
- `include_inprocess` - Include in-process execution
- `include_attach` - Include metadata attachment
- `include_seed_data` - Include sample data
- `validate_config` - Enable config validation

#### Custom Variables
Access custom variables passed via `--template-vars`:
```python
# If --template-vars "model_type=xgboost,epochs=100"
model_type = "{{ model_type | default('random_forest') }}"
epochs = {{ epochs | default(50) }}
```

## Template Examples

### 1. Simple Custom Template

Create `~/.daglab/templates/simple.py.j2`:

```python
# Simple Template - {{ title }}
"""Simple notebook for {{ target_name }}"""

import marimo as mo
import dagster

app = mo.App()

@app.cell
def setup():
    # Basic setup
    target = "{{ target_name }}"
    target_type = "{{ target_type }}"
    return target, target_type

@app.cell
def run_target(target, target_type):
    if target_type == "job":
        # Run job logic
        result = f"Running job: {target}"
    else:
        # Run asset logic
        result = f"Materializing asset: {target}"
    
    mo.md(f"**Result:** {result}")
    return result,
```

Usage:
```bash
daglab scaffold --asset my_asset --template simple
```

### 2. Custom ML Template

Create `~/.daglab/templates/custom_ml.py.j2`:

```python
# Custom ML Pipeline - {{ title }}
"""
Custom ML notebook for {{ target_name }}
Model Type: {{ model_type | default('random_forest') }}
"""

import marimo as mo
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
{% if model_type == 'xgboost' %}
import xgboost as xgb
{% endif %}

app = mo.App()

@app.cell
def load_data():
    """Load and prepare data"""
    {% if include_seed_data %}
    # Sample data
    data = pd.DataFrame({
        'feature1': np.random.randn(1000),
        'feature2': np.random.randn(1000),
        'target': np.random.randn(1000)
    })
    {% else %}
    # Load your data here
    data = pd.read_csv("your_data.csv")
    {% endif %}
    
    return data,

@app.cell
def train_model(data):
    """Train {{ model_type | default('random_forest') }} model"""
    X = data[['feature1', 'feature2']]
    y = data['target']
    
    {% if model_type == 'xgboost' %}
    model = xgb.XGBRegressor(n_estimators={{ epochs | default(100) }})
    {% else %}
    model = RandomForestRegressor(n_estimators={{ epochs | default(100) }})
    {% endif %}
    
    model.fit(X, y)
    score = model.score(X, y)
    
    mo.md(f"**Model Score:** {score:.4f}")
    return model, score
```

Usage:
```bash
daglab scaffold --asset model --template custom_ml --template-vars "model_type=xgboost,epochs=200"
```

## Template Inheritance

### Base Template

Create `~/.daglab/templates/base.py.j2`:

```python
# Base Template
import marimo as mo
{% block imports %}
{% endblock %}

app = mo.App()

{% block metadata %}
{% include 'partials/_metadata.j2' %}
{% endblock %}

{% block setup %}
{% endblock %}

{% block content %}
# Override this block in child templates
{% endblock %}

{% block cleanup %}
{% endblock %}
```

### Child Template

Create `~/.daglab/templates/child.py.j2`:

```python
{% extends "base.py.j2" %}

{% block imports %}
import pandas as pd
import matplotlib.pyplot as plt
{% endblock %}

{% block setup %}
@app.cell
def setup():
    config = {
        'target': "{{ target_name }}",
        'type': "{{ target_type }}"
    }
    return config,
{% endblock %}

{% block content %}
@app.cell
def main_logic(config):
    # Your main logic here
    result = f"Processing {config['target']}"
    return result,
{% endblock %}
```

## Custom Filters

Register custom Jinja2 filters for advanced processing:

```python
# In your custom template engine
from daglab.templates.custom import CustomTemplateLoader

loader = CustomTemplateLoader()

# Register custom filter
@loader.register_filter
def format_snake_case(value):
    """Convert to snake_case"""
    return value.lower().replace(' ', '_').replace('-', '_')

# Use in template
filename = "{{ target_name | format_snake_case }}.py"
```

## Template Configuration

### Project Configuration

Add custom template settings to `daglab.yaml`:

```yaml
templates:
  directories:
    - ~/.daglab/templates
    - ./custom_templates
  default_template: my_custom_default
  variables:
    author: "My Team"
    company: "My Company"
    default_epochs: 100
```

### Template Metadata

Include metadata in your templates:

```python
# Template: custom_ml.py.j2
# Description: Custom ML pipeline template
# Author: Your Name
# Version: 1.0.0
# Variables:
#   - model_type: Type of model to use (default: random_forest)
#   - epochs: Number of training epochs (default: 100)
#   - use_gpu: Enable GPU training (default: false)
```

## Validation

DagLab automatically validates custom templates:

1. **Syntax Validation** - Checks Python syntax
2. **Structure Validation** - Ensures proper marimo structure
3. **Variable Validation** - Checks all variables are defined
4. **Import Validation** - Verifies imports are available

Handle validation errors:

```bash
# Check template before using
daglab scaffold --template my_template --validate-only

# Force generation despite warnings
daglab scaffold --template my_template --force-validation
```

## Best Practices

### 1. Template Organization
- Use descriptive names
- Include template metadata
- Organize by use case
- Document template variables

### 2. Variable Handling
```python
# Good: Provide defaults
epochs = {{ epochs | default(100) }}

# Good: Type checking
{% if model_type in ['xgboost', 'lightgbm'] %}
# Use gradient boosting
{% endif %}

# Good: Error handling
{% if not target_name %}
{% error "target_name is required" %}
{% endif %}
```

### 3. Reusable Components
- Use partials for common functionality
- Create base templates for inheritance
- Keep templates DRY (Don't Repeat Yourself)

### 4. Documentation
```python
"""
Template: {{ template_name }}
Purpose: {{ description }}
Target: {{ target_type }}:{{ target_name }}

Variables:
{% for key, value in template_vars.items() %}
- {{ key }}: {{ value }}
{% endfor %}

Generated: {{ created_date }}
"""
```

## Troubleshooting

### Common Issues

1. **Template Not Found**
   - Check template directory exists
   - Verify template name spelling
   - Ensure file has `.j2` extension

2. **Variable Errors**
   - Use default filters: `{{ var | default('fallback') }}`
   - Check variable names match context
   - Validate custom variables

3. **Syntax Errors**
   - Run template validation
   - Check Jinja2 syntax
   - Verify Python code blocks

### Debug Mode

Enable debug mode for detailed template information:

```bash
daglab scaffold --template my_template --debug --verbose
```

This guide covers the essential aspects of template customization in DagLab. For more advanced features, refer to the Jinja2 documentation and DagLab API reference.
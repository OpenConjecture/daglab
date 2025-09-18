"""Template context builder for DAGLab notebook generation."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from daglab.config import DagLabConfig


class TemplateContext:
    """Build and manage context for template rendering."""

    def __init__(self, config: Optional[DagLabConfig] = None):
        """Initialize context builder.
        
        Args:
            config: DAGLab configuration instance
        """
        self.config = config or DagLabConfig()
        self._base_context = self._build_base_context()

    def _build_base_context(self) -> Dict[str, Any]:
        """Build base context available to all templates."""
        return {
            "daglab_version": self._get_version(),
            "generation_time": datetime.now().isoformat(),
            "environment": os.environ.get("DAGLAB_ENV", "development"),
            "project_root": str(Path.cwd()),
            "python_version": self._get_python_version(),
        }

    def _get_version(self) -> str:
        """Get DAGLab version."""
        try:
            from daglab import __version__
            return __version__
        except ImportError:
            return "0.0.0"

    def _get_python_version(self) -> str:
        """Get Python version."""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def build_metadata_context(
        self,
        notebook_name: str,
        author: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build metadata context for notebook.
        
        Args:
            notebook_name: Name of the notebook
            author: Notebook author
            description: Notebook description
            tags: List of tags
            custom_metadata: Additional metadata
            
        Returns:
            Metadata context dictionary
        """
        metadata = {
            "name": notebook_name,
            "author": author or os.environ.get("USER", "daglab"),
            "description": description or f"DAGLab notebook: {notebook_name}",
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "kernel_spec": {
                "name": "python3",
                "display_name": "Python 3",
                "language": "python",
            },
        }
        
        if custom_metadata:
            metadata.update(custom_metadata)
        
        return {"metadata": metadata}

    def build_config_context(
        self,
        target_type: str = "dagster",
        job_name: Optional[str] = None,
        asset_name: Optional[str] = None,
        schedule: Optional[Dict[str, Any]] = None,
        resources: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build configuration context for target platform.
        
        Args:
            target_type: Target platform (dagster, marimo, etc.)
            job_name: Dagster job name
            asset_name: Dagster asset name
            schedule: Schedule configuration
            resources: Resource configuration
            
        Returns:
            Configuration context dictionary
        """
        context = {
            "target_type": target_type,
            "config": {},
        }
        
        if target_type == "dagster":
            dagster_config = {
                "job_name": job_name or "generated_job",
                "asset_name": asset_name or "generated_asset",
                "io_manager": "fs_io_manager",
                "compute_kind": "python",
            }
            
            if schedule:
                dagster_config["schedule"] = schedule
            
            if resources:
                dagster_config["resources"] = resources
            
            context["config"]["dagster"] = dagster_config
            
        elif target_type == "marimo":
            context["config"]["marimo"] = {
                "layout": "vertical",
                "width": "medium",
                "reactive": True,
            }
        
        return context

    def build_target_context(
        self,
        imports: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, str]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build target-specific context.
        
        Args:
            imports: List of import statements
            parameters: Parameter definitions
            outputs: Output definitions
            dependencies: List of dependencies
            
        Returns:
            Target context dictionary
        """
        return {
            "imports": imports or ["import pandas as pd", "import numpy as np"],
            "parameters": parameters or {},
            "outputs": outputs or {},
            "dependencies": dependencies or [],
        }

    def build_complete_context(
        self,
        notebook_name: str,
        target_type: str = "dagster",
        author: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_metadata: Optional[Dict[str, Any]] = None,
        job_name: Optional[str] = None,
        asset_name: Optional[str] = None,
        schedule: Optional[Dict[str, Any]] = None,
        resources: Optional[Dict[str, Any]] = None,
        imports: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, str]] = None,
        dependencies: Optional[List[str]] = None,
        custom_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build complete context for template rendering.
        
        Combines all context builders into a single context.
        
        Returns:
            Complete context dictionary
        """
        context = self._base_context.copy()
        
        # Add metadata context
        context.update(self.build_metadata_context(
            notebook_name=notebook_name,
            author=author,
            description=description,
            tags=tags,
            custom_metadata=custom_metadata,
        ))
        
        # Add config context
        context.update(self.build_config_context(
            target_type=target_type,
            job_name=job_name,
            asset_name=asset_name,
            schedule=schedule,
            resources=resources,
        ))
        
        # Add target context
        context.update(self.build_target_context(
            imports=imports,
            parameters=parameters,
            outputs=outputs,
            dependencies=dependencies,
        ))
        
        # Add custom context last to allow overrides
        if custom_context:
            context.update(custom_context)
        
        return context

    def validate_context(
        self,
        context: Dict[str, Any],
        required_keys: Optional[List[str]] = None,
    ) -> tuple[bool, List[str]]:
        """Validate context completeness.
        
        Args:
            context: Context dictionary to validate
            required_keys: List of required keys
            
        Returns:
            Tuple of (is_valid, missing_keys)
        """
        if required_keys is None:
            # Default required keys
            required_keys = ["metadata", "config", "imports"]
        
        missing_keys = []
        for key in required_keys:
            if key not in context:
                missing_keys.append(key)
            elif isinstance(context[key], dict):
                # Check nested required keys
                if key == "metadata":
                    for sub_key in ["name", "author"]:
                        if sub_key not in context[key]:
                            missing_keys.append(f"{key}.{sub_key}")
        
        return len(missing_keys) == 0, missing_keys

    def merge_contexts(self, *contexts: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple contexts together.
        
        Later contexts override earlier ones.
        
        Args:
            *contexts: Variable number of context dictionaries
            
        Returns:
            Merged context dictionary
        """
        result = {}
        for context in contexts:
            self._deep_merge(result, context)
        return result

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Deep merge source into target dictionary."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def add_custom_variables(
        self,
        context: Dict[str, Any],
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add custom template variables to context.
        
        Args:
            context: Existing context
            variables: Custom variables to add
            
        Returns:
            Updated context
        """
        context["custom"] = variables
        return context
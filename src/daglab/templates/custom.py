"""
Custom template support for DagLab.

This module provides support for user-defined templates, including
template discovery, validation, custom filter registration, and
inheritance from built-in templates.
"""

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from jinja2 import (
    Environment, FileSystemLoader, TemplateNotFound, 
    select_autoescape, ChoiceLoader
)

from ..validation.template import TemplateValidator, ValidationResult


class CustomTemplateLoader:
    """Loader for custom user templates."""
    
    def __init__(
        self,
        custom_dirs: Optional[List[Path]] = None,
        builtin_dir: Optional[Path] = None
    ):
        """
        Initialize custom template loader.
        
        Args:
            custom_dirs: List of custom template directories
            builtin_dir: Directory containing built-in templates
        """
        self.custom_dirs = custom_dirs or self._get_default_custom_dirs()
        self.builtin_dir = builtin_dir or self._get_builtin_dir()
        self.env = self._create_environment()
        self.validator = TemplateValidator(self.custom_dirs + [self.builtin_dir])
        self._custom_filters: Dict[str, Callable] = {}
        self._template_cache: Dict[str, Path] = {}
    
    def discover(self, refresh: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discover available templates.
        
        Args:
            refresh: Whether to refresh the cache
            
        Returns:
            Dict mapping categories to template info
        """
        if refresh:
            self._template_cache.clear()
        
        templates = {
            "builtin": [],
            "custom": [],
            "user": []
        }
        
        # Discover built-in templates
        if self.builtin_dir and self.builtin_dir.exists():
            for template_path in self.builtin_dir.glob("*.py.j2"):
                info = self._get_template_info(template_path)
                info["source"] = "builtin"
                templates["builtin"].append(info)
        
        # Discover custom templates
        for custom_dir in self.custom_dirs:
            if custom_dir.exists():
                category = "user" if ".daglab" in str(custom_dir) else "custom"
                
                for template_path in custom_dir.glob("**/*.py.j2"):
                    info = self._get_template_info(template_path)
                    info["source"] = category
                    info["directory"] = str(custom_dir)
                    templates[category].append(info)
                    
                    # Cache the template
                    rel_path = template_path.relative_to(custom_dir)
                    self._template_cache[str(rel_path)] = template_path
        
        return templates
    
    def validate_all(self) -> Dict[str, ValidationResult]:
        """
        Validate all discovered templates.
        
        Returns:
            Dict mapping template paths to validation results
        """
        results = {}
        templates = self.discover()
        
        for category in templates:
            for template_info in templates[category]:
                path = Path(template_info["path"])
                result = self.validator.validate(path)
                results[str(path)] = result
        
        return results
    
    def register_filter(self, name: str, filter_func: Callable) -> None:
        """
        Register a custom filter.
        
        Args:
            name: Filter name
            filter_func: Filter function
        """
        self._custom_filters[name] = filter_func
        self.env.filters[name] = filter_func
    
    def register_filters(self, filters: Dict[str, Callable]) -> None:
        """
        Register multiple custom filters.
        
        Args:
            filters: Dict mapping filter names to functions
        """
        for name, func in filters.items():
            self.register_filter(name, func)
    
    def load_template(self, name: str) -> Any:
        """
        Load a template by name.
        
        Args:
            name: Template name (with or without .py.j2 extension)
            
        Returns:
            Loaded template object
        """
        # Normalize name
        if not name.endswith(".py.j2"):
            name += ".py.j2"
        
        try:
            return self.env.get_template(name)
        except TemplateNotFound:
            # Try to find in cache
            if name in self._template_cache:
                path = self._template_cache[name]
                return self.env.get_template(str(path))
            
            raise TemplateNotFound(f"Template '{name}' not found")
    
    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any],
        validate: bool = True
    ) -> str:
        """
        Render a template with context.
        
        Args:
            template_name: Name of the template
            context: Context variables
            validate: Whether to validate before rendering
            
        Returns:
            Rendered template content
        """
        template = self.load_template(template_name)
        
        if validate:
            # Find template path for validation
            template_path = None
            if template_name in self._template_cache:
                template_path = self._template_cache[template_name]
            else:
                # Search for template
                for loader in self.env.loader.loaders:
                    try:
                        source, filename, _ = loader.get_source(self.env, template_name)
                        template_path = Path(filename)
                        break
                    except TemplateNotFound:
                        continue
            
            if template_path:
                result = self.validator.validate(template_path)
                if not result.is_valid:
                    raise ValueError(f"Template validation failed: {result.summary()}")
        
        # Add default context
        full_context = self._get_default_context()
        full_context.update(context)
        
        return template.render(**full_context)
    
    def create_template(
        self,
        name: str,
        content: str,
        directory: Optional[Path] = None,
        validate: bool = True
    ) -> Path:
        """
        Create a new custom template.
        
        Args:
            name: Template name
            content: Template content
            directory: Directory to save in (uses user dir by default)
            validate: Whether to validate the template
            
        Returns:
            Path to created template
        """
        # Determine save directory
        if directory is None:
            directory = self._get_user_template_dir()
        
        # Ensure directory exists
        directory.mkdir(parents=True, exist_ok=True)
        
        # Normalize name
        if not name.endswith(".py.j2"):
            name += ".py.j2"
        
        template_path = directory / name
        
        # Write template
        template_path.write_text(content)
        
        # Validate if requested
        if validate:
            result = self.validator.validate(template_path)
            if not result.is_valid:
                # Remove invalid template
                template_path.unlink()
                raise ValueError(f"Template validation failed: {result.summary()}")
        
        # Update cache
        self._template_cache[name] = template_path
        
        return template_path
    
    def get_inheritance_chain(self, template_name: str) -> List[str]:
        """
        Get the inheritance chain for a template.
        
        Args:
            template_name: Template name
            
        Returns:
            List of template names in inheritance order
        """
        chain = []
        template = self.load_template(template_name)
        
        # Walk up the inheritance chain
        current = template
        while current:
            chain.append(current.name)
            
            # Check for extends
            if hasattr(current, 'parent'):
                current = current.parent
            else:
                break
        
        return chain
    
    def _create_environment(self) -> Environment:
        """Create Jinja2 environment with custom and builtin loaders."""
        loaders = []
        
        # Add custom directories
        for custom_dir in self.custom_dirs:
            if custom_dir.exists():
                loaders.append(FileSystemLoader(str(custom_dir)))
        
        # Add builtin directory
        if self.builtin_dir and self.builtin_dir.exists():
            loaders.append(FileSystemLoader(str(self.builtin_dir)))
        
        # Create environment with choice loader
        env = Environment(
            loader=ChoiceLoader(loaders),
            autoescape=False,  # For Python code
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # Add default filters
        env.filters.update(self._get_default_filters())
        
        # Add custom filters
        env.filters.update(self._custom_filters)
        
        return env
    
    def _get_template_info(self, path: Path) -> Dict[str, Any]:
        """Extract template information."""
        info = {
            "name": path.stem,  # Remove .py.j2
            "path": str(path),
            "size": path.stat().st_size,
            "modified": path.stat().st_mtime
        }
        
        # Try to extract metadata from template
        try:
            content = path.read_text()
            
            # Look for metadata comment block
            import re
            metadata_match = re.search(
                r'{#\s*METADATA\s*(.*?)\s*#}',
                content,
                re.DOTALL
            )
            
            if metadata_match:
                # Parse YAML-like metadata
                metadata_text = metadata_match.group(1)
                for line in metadata_text.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip().lower()] = value.strip()
        except Exception:
            pass
        
        return info
    
    def _get_default_custom_dirs(self) -> List[Path]:
        """Get default custom template directories."""
        dirs = []
        
        # User home directory
        user_dir = self._get_user_template_dir()
        if user_dir:
            dirs.append(user_dir)
        
        # Current working directory templates
        cwd_templates = Path.cwd() / "templates"
        if cwd_templates.exists():
            dirs.append(cwd_templates)
        
        # Environment variable
        if "DAGLAB_TEMPLATE_PATH" in os.environ:
            for path in os.environ["DAGLAB_TEMPLATE_PATH"].split(":"):
                dirs.append(Path(path))
        
        return dirs
    
    def _get_user_template_dir(self) -> Path:
        """Get user template directory."""
        return Path.home() / ".daglab" / "templates"
    
    def _get_builtin_dir(self) -> Path:
        """Get built-in template directory."""
        return Path(__file__).parent / "builtin"
    
    def _get_default_context(self) -> Dict[str, Any]:
        """Get default context for templates."""
        # Import helpers
        from ..helpers.notebook import (
            run_job, run_asset, discover, attach_metadata,
            validate_config, track_performance, manage_state
        )
        
        return {
            # Helper functions
            "run_job": run_job,
            "run_asset": run_asset,
            "discover": discover,
            "attach_metadata": attach_metadata,
            "validate_config": validate_config,
            "track_performance": track_performance,
            "manage_state": manage_state,
            
            # Utilities
            "datetime": __import__("datetime"),
            "json": __import__("json"),
            "Path": Path,
            
            # Template metadata
            "template_engine": "daglab",
            "template_version": "1.0.0"
        }
    
    def _get_default_filters(self) -> Dict[str, Callable]:
        """Get default template filters."""
        return {
            # Python-specific filters
            "python_repr": repr,
            "python_str": str,
            "python_type": lambda x: type(x).__name__,
            
            # JSON filters
            "to_json": lambda x: __import__("json").dumps(x),
            "from_json": lambda x: __import__("json").loads(x),
            
            # String filters
            "snake_case": lambda x: x.lower().replace(" ", "_").replace("-", "_"),
            "camel_case": lambda x: "".join(w.capitalize() for w in x.split("_")),
            "kebab_case": lambda x: x.lower().replace(" ", "-").replace("_", "-"),
            
            # List filters
            "join_paths": lambda x: "/".join(x),
            "unique": lambda x: list(set(x)),
            
            # Dict filters
            "dict_keys": lambda x: list(x.keys()) if isinstance(x, dict) else [],
            "dict_values": lambda x: list(x.values()) if isinstance(x, dict) else [],
        }


# Convenience functions
def load_custom_template(name: str, custom_dirs: Optional[List[Path]] = None) -> Any:
    """Load a custom template."""
    loader = CustomTemplateLoader(custom_dirs=custom_dirs)
    return loader.load_template(name)


def render_custom_template(
    name: str,
    context: Dict[str, Any],
    custom_dirs: Optional[List[Path]] = None
) -> str:
    """Render a custom template."""
    loader = CustomTemplateLoader(custom_dirs=custom_dirs)
    return loader.render_template(name, context)
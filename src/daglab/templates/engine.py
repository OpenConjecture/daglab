"""Jinja2 template engine for DAGLab notebook generation."""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from jinja2 import (
    Environment,
    FileSystemLoader,
    PackageLoader,
    TemplateNotFound,
    select_autoescape,
)
from jinja2.exceptions import TemplateError


class TemplateEngine:
    """Jinja2-based template engine for notebook generation."""

    def __init__(
        self,
        template_dirs: Optional[List[Union[str, Path]]] = None,
        enable_cache: bool = True,
        strict_undefined: bool = False,
        trim_blocks: bool = True,
        lstrip_blocks: bool = True,
    ):
        """Initialize the template engine.
        
        Args:
            template_dirs: Additional directories to search for templates
            enable_cache: Whether to cache compiled templates
            strict_undefined: Whether to raise errors on undefined variables
            trim_blocks: Whether to trim newlines after template tags
            lstrip_blocks: Whether to strip leading spaces from template tags
        """
        self.template_dirs = [Path(d) for d in (template_dirs or [])]
        
        # Set up loaders - package loader first, then custom dirs
        loaders = []
        
        # Add built-in templates from package
        try:
            loaders.append(PackageLoader("daglab.templates", "notebooks"))
        except ImportError:
            # Package not installed yet, use file system loader
            builtin_dir = Path(__file__).parent / "notebooks"
            if builtin_dir.exists():
                loaders.append(FileSystemLoader(str(builtin_dir)))
        
        # Add custom template directories
        for template_dir in self.template_dirs:
            if template_dir.exists():
                loaders.append(FileSystemLoader(str(template_dir)))
        
        # Create Jinja2 environment
        from jinja2 import ChoiceLoader
        self.env = Environment(
            loader=ChoiceLoader(loaders),
            autoescape=select_autoescape(["html", "xml"]),
            cache_size=400 if enable_cache else 0,
            undefined=self._get_undefined_class(strict_undefined),
            trim_blocks=trim_blocks,
            lstrip_blocks=lstrip_blocks,
        )
        
        # Register custom filters
        self._register_filters()
        
        # Template cache for custom caching logic
        self._template_cache: Dict[str, Any] = {}

    def _get_undefined_class(self, strict: bool):
        """Get the appropriate undefined class based on strictness."""
        from jinja2 import StrictUndefined, Undefined
        return StrictUndefined if strict else Undefined

    def _register_filters(self):
        """Register custom Jinja2 filters."""
        self.env.filters["to_json"] = self._filter_to_json
        self.env.filters["format_date"] = self._filter_format_date
        self.env.filters["slugify"] = self._filter_slugify
        self.env.filters["camel_to_snake"] = self._filter_camel_to_snake
        self.env.filters["snake_to_camel"] = self._filter_snake_to_camel
        self.env.filters["truncate_path"] = self._filter_truncate_path
        self.env.filters["indent_code"] = self._filter_indent_code
        self.env.filters["escape_quotes"] = self._filter_escape_quotes

    @staticmethod
    def _filter_to_json(value: Any, indent: int = 2) -> str:
        """Convert value to JSON string."""
        return json.dumps(value, indent=indent, default=str)

    @staticmethod
    def _filter_format_date(value: Union[str, datetime], fmt: str = "%Y-%m-%d") -> str:
        """Format date/datetime."""
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        return value.strftime(fmt)

    @staticmethod
    def _filter_slugify(value: str) -> str:
        """Convert string to slug format."""
        value = re.sub(r"[^\w\s-]", "", value.lower())
        return re.sub(r"[-\s]+", "-", value).strip("-")

    @staticmethod
    def _filter_camel_to_snake(value: str) -> str:
        """Convert CamelCase to snake_case."""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", value)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @staticmethod
    def _filter_snake_to_camel(value: str, capitalize_first: bool = True) -> str:
        """Convert snake_case to CamelCase."""
        components = value.split("_")
        if capitalize_first:
            return "".join(x.title() for x in components)
        else:
            return components[0] + "".join(x.title() for x in components[1:])

    @staticmethod
    def _filter_truncate_path(value: str, max_parts: int = 3) -> str:
        """Truncate long paths to last N parts."""
        parts = Path(value).parts
        if len(parts) <= max_parts:
            return value
        return str(Path(*parts[-max_parts:]))

    @staticmethod
    def _filter_indent_code(value: str, spaces: int = 4) -> str:
        """Indent code block."""
        indent = " " * spaces
        return "\n".join(indent + line if line else "" for line in value.split("\n"))

    @staticmethod
    def _filter_escape_quotes(value: str, quote_type: str = "double") -> str:
        """Escape quotes in string."""
        if quote_type == "double":
            return value.replace('"', '\\"')
        else:
            return value.replace("'", "\\'")

    def add_template_dir(self, directory: Union[str, Path]) -> None:
        """Add a template directory to the search path."""
        directory = Path(directory)
        if not directory.exists():
            raise ValueError(f"Template directory does not exist: {directory}")
        
        self.template_dirs.append(directory)
        
        # Update loader
        from jinja2 import ChoiceLoader
        loaders = list(self.env.loader.loaders)  # type: ignore
        loaders.append(FileSystemLoader(str(directory)))
        self.env.loader = ChoiceLoader(loaders)

    def get_template(self, name: str) -> Any:
        """Get a template by name."""
        try:
            return self.env.get_template(name)
        except TemplateNotFound:
            # List available templates for debugging
            available = self.list_templates()
            raise TemplateNotFound(
                f"Template '{name}' not found. Available templates: {available}"
            )

    def list_templates(self, extensions: Optional[List[str]] = None) -> List[str]:
        """List all available templates."""
        if extensions is None:
            extensions = [".j2", ".jinja2", ".jinja", ".ipynb.j2"]
        
        templates = []
        for loader in self.env.loader.loaders:  # type: ignore
            try:
                templates.extend(loader.list_templates())
            except Exception:
                # Some loaders might not support listing
                pass
        
        # Filter by extensions
        if extensions:
            templates = [
                t for t in templates
                if any(t.endswith(ext) for ext in extensions)
            ]
        
        return sorted(set(templates))

    def render_notebook(
        self,
        template_name: str,
        context: Dict[str, Any],
        validate: bool = True,
    ) -> str:
        """Render a notebook template.
        
        Args:
            template_name: Name of the template to render
            context: Context dictionary for rendering
            validate: Whether to validate the output
            
        Returns:
            Rendered notebook content as string
        """
        try:
            template = self.get_template(template_name)
            content = template.render(**context)
            
            if validate:
                # Basic validation - check if it's valid JSON for .ipynb
                if template_name.endswith(".ipynb") or template_name.endswith(".ipynb.j2"):
                    try:
                        json.loads(content)
                    except json.JSONDecodeError as e:
                        raise TemplateError(f"Invalid notebook JSON output: {e}")
            
            return content
            
        except Exception as e:
            # Add context information to error
            raise TemplateError(
                f"Error rendering template '{template_name}': {str(e)}"
            ) from e

    def render_string(
        self,
        template_string: str,
        context: Dict[str, Any],
        name: str = "string_template",
    ) -> str:
        """Render a template from string.
        
        Args:
            template_string: Template content as string
            context: Context dictionary for rendering
            name: Optional name for the template
            
        Returns:
            Rendered content as string
        """
        try:
            template = self.env.from_string(template_string, globals=context)
            return template.render(**context)
        except Exception as e:
            raise TemplateError(
                f"Error rendering string template '{name}': {str(e)}"
            ) from e

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self.env.cache.clear()  # type: ignore
        self._template_cache.clear()
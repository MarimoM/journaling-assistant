#!/usr/bin/env python3
"""
Template manager for handling Jinja2 templates for LLM prompts.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template

class TemplateManager:
    """Manages Jinja2 templates for LLM prompts."""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """Initialize the template manager."""
        if templates_dir is None:
            # Default to templates directory relative to project root
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            templates_dir = project_root / "templates"
        
        self.templates_dir = Path(templates_dir)
        
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {self.templates_dir}")
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # Add custom filters if needed
        self.env.filters['join'] = lambda x, sep=', ': sep.join(str(i) for i in x if i)
        
        print(f"✅ Template manager initialized with templates from: {self.templates_dir}")
    
    def get_template(self, template_name: str) -> Template:
        """Get a template by name."""
        try:
            return self.env.get_template(template_name)
        except Exception as e:
            raise FileNotFoundError(f"Template '{template_name}' not found: {e}")
    
    def render_template(self, template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Render a template with the given context."""
        if context is None:
            context = {}
        
        template = self.get_template(template_name)
        return template.render(**context)
    
    def list_templates(self) -> list[str]:
        """List all available templates."""
        return [f.name for f in self.templates_dir.glob("*.j2")]
    
    def render_system_prompt(self, user_context: Optional[Dict[str, Any]] = None) -> str:
        """Render the system prompt template with user context."""
        context = {
            "user_context": user_context
        }
        return self.render_template("system_prompt.j2", context)

# Global template manager instance
template_manager = TemplateManager()
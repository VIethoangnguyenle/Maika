"""Jinja2 renderer — renders plugin templates with platform context."""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


# Extensions that are safe to read and render as text templates.
# Binary files (images, zips, etc.) should never be rendered.
_TEXT_EXTENSIONS = {
    ".md", ".yaml", ".yml", ".json", ".txt", ".py", ".sh",
    ".toml", ".cfg", ".ini", ".xml", ".html", ".j2", ".tpl",
}

# Marker to detect Jinja2 template content
_JINJA_MARKER = "{{ "


def create_renderer(template_base_dir: str) -> Environment:
    """Create a Jinja2 environment rooted at the template base directory.

    Args:
        template_base_dir: Absolute path to the directory containing
                          plugin templates (e.g., /path/to/maika/plugins/).
    """
    env = Environment(
        loader=FileSystemLoader(template_base_dir),
        autoescape=select_autoescape([]),  # no HTML escaping for markdown
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    return env


def render_string(env: Environment, content: str, context: Dict) -> str:
    """Render a string containing Jinja2 variables.

    Uses env.from_string() — does NOT require the content to be a file
    on the FileSystemLoader. Ideal for rendering files discovered during
    directory copy.
    """
    template = env.from_string(content)
    return template.render(**context)


def render_template(
    env: Environment,
    template_path: str,
    context: Dict,
) -> str:
    """Render a single .j2 template with the given context.

    Args:
        env: Jinja2 Environment.
        template_path: Relative path to the template file (from template base dir).
        context: Render context containing tools, capabilities, etc.

    Returns:
        Rendered content as string.
    """
    template = env.get_template(template_path)
    return template.render(**context)


def render_file_to_target(
    env: Environment,
    template_path: str,
    context: Dict,
    target_path: str,
) -> None:
    """Render a template and write the result to target path.

    Creates parent directories if they don't exist.
    """
    rendered = render_template(env, template_path, context)
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")


def _is_text_file(path: Path) -> bool:
    """Check if a file is a text file safe for Jinja2 rendering."""
    return path.suffix.lower() in _TEXT_EXTENSIONS


def _has_jinja_vars(content: str) -> bool:
    """Quick check if content contains Jinja2 variable markers."""
    return _JINJA_MARKER in content


def copy_and_render_directory(
    env: Environment,
    src: Path,
    dst: Path,
    context: Dict,
    exclude_patterns: Optional[List[str]] = None,
) -> tuple:
    """Copy directory recursively, auto-rendering files with Jinja2 variables.

    For each file:
      1. If it's a text file AND contains '{{ ' → render through Jinja2
      2. Otherwise → plain copy (binary-safe)

    Returns:
        Tuple of (total_files_copied, files_rendered).
    """
    exclude = exclude_patterns or [
        "__pycache__", ".pytest_cache", "*.pyc", ".git",
        # Framework CI artifacts — no scaffolded consumer downstream:
        "tests",               # tools/*/tests, hooks/write-gate/tests
        # Per-project instance / build artifacts that must never be scaffolded
        # from the framework source (only their templates/seeds ship):
        "persona.yaml",        # ship persona.template.yaml; user creates persona.yaml
        "rules.json",          # rule-projector build output (regenerated per project)
        "*.generated.xml",     # rule-projector checkstyle output
    ]
    total = 0
    rendered = 0

    def should_exclude(path: Path) -> bool:
        name = path.name
        for pattern in exclude:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        return False

    for item in src.rglob("*"):
        if should_exclude(item) or any(should_exclude(p) for p in item.parents):
            continue
        if item.is_file():
            rel = item.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)

            # Try to render text files containing Jinja2 variables.
            # Only UnicodeDecodeError (binary file with a text extension) is
            # tolerated; template errors must surface, never ship unrendered.
            if _is_text_file(item):
                try:
                    content = item.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = None
                if content is not None and _has_jinja_vars(content):
                    output = render_string(env, content, context)
                    target.write_text(output, encoding="utf-8")
                    # Preserve original file timestamps
                    shutil.copystat(item, target)
                    rendered += 1
                    total += 1
                    continue

            # Plain copy (binary files or text without Jinja2)
            shutil.copy2(item, target)
            total += 1

    return total, rendered

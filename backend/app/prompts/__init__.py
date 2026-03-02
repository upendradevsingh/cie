"""Prompt template loading utilities for SalesLens.

Provides a simple interface for loading and rendering Jinja2 prompt templates
from the ``app/prompts/`` directory.  Templates are loaded fresh on each call
to support development-time iteration without restarts.

Usage::

    from app.prompts import load_prompt

    rendered = load_prompt(
        "call_analysis",
        transcript="...",
        quality_parameters=[...],
        intent_signals=[...],
        persona_types=[...],
    )
"""

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent

# Jinja2 environment with auto-escape disabled (prompts are plain text, not
# HTML) and trailing newlines preserved.
_env = Environment(
    loader=FileSystemLoader(str(PROMPTS_DIR)),
    autoescape=False,
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def load_prompt(name: str, **kwargs: Any) -> str:
    """Load a Jinja2 template by name and render it with the given context.

    Parameters
    ----------
    name:
        Template name **without** the ``.jinja2`` extension.
        For example, ``"call_analysis"`` loads ``call_analysis.jinja2``.
    **kwargs:
        Template context variables passed to ``Template.render()``.

    Returns
    -------
    str
        The fully rendered prompt string.

    Raises
    ------
    FileNotFoundError
        If the template file does not exist in the prompts directory.

    Examples
    --------
    >>> prompt = load_prompt(
    ...     "call_analysis",
    ...     transcript="[00:00] Agent: Hello...",
    ...     quality_parameters=[
    ...         {"name": "Opening & Greeting", "description": "...", "weight": 1.0}
    ...     ],
    ...     intent_signals=[
    ...         {"name": "Budget mentioned", "description": "..."}
    ...     ],
    ...     persona_types=[
    ...         {"name": "Decision Maker", "description": "..."}
    ...     ],
    ... )
    """
    template_filename = f"{name}.jinja2"

    try:
        template = _env.get_template(template_filename)
    except TemplateNotFound:
        raise FileNotFoundError(
            f"Prompt template '{template_filename}' not found in {PROMPTS_DIR}. "
            f"Available templates: {[p.name for p in PROMPTS_DIR.glob('*.jinja2')]}"
        )

    rendered = template.render(**kwargs)

    logger.debug(
        "Rendered prompt '%s' — %d characters, %d context keys",
        name,
        len(rendered),
        len(kwargs),
    )

    return rendered


def list_prompts() -> list[str]:
    """Return a list of available prompt template names (without extension).

    Returns
    -------
    list[str]
        Template names that can be passed to :func:`load_prompt`.
    """
    return [p.stem for p in PROMPTS_DIR.glob("*.jinja2")]

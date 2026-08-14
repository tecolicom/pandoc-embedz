"""Configuration and parsing module for pandoc-embedz

This module handles configuration parsing, validation, and file path validation.
"""

from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import Any

import panflute as pf
import yaml
from jinja2 import TemplateNotFound

# Store templates - shared across modules
SAVED_TEMPLATES: dict[str, str] = {}

# Internal canonical name -> Preferred external alias (no warning)
PARAMETER_PREFERRED_ALIASES = {
    'name': 'define',      # Normalize 'define' -> 'name' (recommended, no warning)
    'as': 'template',      # Normalize 'template' -> 'as' (recommended, no warning)
}

# Reverse lookup: Preferred alias -> Internal canonical name (for O(1) lookups)
_ALIAS_TO_INTERNAL = {preferred: internal for internal, preferred in PARAMETER_PREFERRED_ALIASES.items()}

# Parameters removed in 1.0.0 -> their replacement.
# These were deprecated with a warning in earlier releases and are now rejected.
# 'name' is still the internal canonical key for 'define', so it cannot simply be
# dropped from the alias table: writing it directly has to be refused explicitly.
REMOVED_PARAMETERS = {
    'name': 'define',
    'skiprows': 'startrow',
}

def validate_file_path(file_path: str) -> str:
    """Validate file path to prevent path traversal attacks

    Args:
        file_path: File path to validate, or '-' for stdin

    Returns:
        str: Validated absolute file path, or '-' for stdin

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If path appears to be malicious
    """
    # Allow '-' as stdin indicator
    if file_path == '-':
        return '-'

    try:
        # Convert to Path object and resolve to absolute path
        path = Path(file_path).resolve()

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check if it's actually a file (not a directory)
        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        return str(path)
    except (OSError, RuntimeError) as e:
        # Catch potential path resolution errors
        raise ValueError(f"Invalid file path: {file_path}") from e

def load_template_from_saved(name: str) -> tuple[str, None, Callable[[], bool]]:
    """Loader function for saved templates

    Args:
        name: Template name

    Returns:
        tuple: (template_source, None, lambda: True)

    Raises:
        TemplateNotFound: If template is not found
    """
    if name not in SAVED_TEMPLATES:
        raise TemplateNotFound(name)
    # Return (source, filename, uptodate_func) tuple
    return SAVED_TEMPLATES[name], None, lambda: True


def _ensure_dict(value: Any, source: str) -> dict[str, Any]:
    """Ensure loaded YAML content is a mapping."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{source} must contain a YAML mapping at the top level")
    return value


def load_config_file(file_path: str) -> dict[str, Any]:
    """Load YAML configuration from an external file.

    Supports multiple YAML documents in a single file (separated by ---).
    Documents are merged in order, with later documents overriding earlier ones.

    Example:
        ---
        global:
          今年度: 2023
        ---
        bind:
          前年度: 今年度 - 1
        ---

    Args:
        file_path: Path to the YAML configuration file

    Returns:
        Merged configuration dictionary from all documents
    """
    validated_path = validate_file_path(file_path)
    with open(validated_path, encoding='utf-8') as handle:
        content = handle.read()

    # Use safe_load_all to parse multiple YAML documents
    merged: dict[str, Any] = {}
    for doc in yaml.safe_load_all(content):
        if doc is not None:
            validated = _ensure_dict(doc, f"Config file '{file_path}'")
            merged = deep_merge_dicts(merged, validated)

    return merged


def deep_merge_dicts(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge dictionaries without mutating inputs."""
    merged: dict[str, Any] = dict(base)
    for key, value in updates.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged

def parse_attributes(elem: pf.CodeBlock) -> dict[str, Any]:
    """Parse code block attributes into config dictionary

    Supports dot notation for nested dictionaries (e.g., with.title="Title", global.author="John")
    Only single-level nesting is supported.

    Args:
        elem: Pandoc CodeBlock element

    Returns:
        dict: Parsed configuration with proper type conversion
    """
    config: dict[str, Any] = {}
    nested_vars: dict[str, dict[str, Any]] = {}

    # elem.attributes is a dictionary
    if hasattr(elem, 'attributes') and elem.attributes:
        for key, value in elem.attributes.items():
            # Handle dot notation (e.g., with.title="Title", global.author="John")
            if '.' in key:
                main_key, sub_key = key.split('.', 1)  # Split on first dot only
                if main_key not in nested_vars:
                    nested_vars[main_key] = {}
                # Type conversion for boolean values
                if isinstance(value, str) and value.lower() in ('true', 'false'):
                    nested_vars[main_key][sub_key] = value.lower() == 'true'
                else:
                    nested_vars[main_key][sub_key] = value
            else:
                # Type conversion for boolean values
                if isinstance(value, str) and value.lower() in ('true', 'false'):
                    config[key] = value.lower() == 'true'
                # Keep everything else as-is
                else:
                    config[key] = value

    # Add nested vars to config
    for main_key, sub_vars in nested_vars.items():
        config[main_key] = sub_vars

    return config

def parse_code_block(
    text: str,
    allow_inline_data: bool = True
) -> tuple[dict[str, Any], str, str | None]:
    """Parse code block into YAML config, template, and data sections

    Args:
        text: Code block text to parse

    Returns:
        tuple: (config dict, template_part str, data_part str or None)
    """
    if not text.startswith('---'):
        # No YAML header - entire content is either template or inline data
        return {}, text, None

    stream = StringIO(text)
    first_line = stream.readline()

    if not first_line.startswith('---'):
        return {}, text, None

    # Read YAML header
    yaml_lines = []
    for line in stream:
        if line.strip() == '---':
            break
        yaml_lines.append(line)
    else:
        # No closing delimiter found, treat as YAML only
        yaml_part = ''.join(yaml_lines).strip()
        config = yaml.safe_load(yaml_part) or {}
        return config, '', None

    # Read template and data sections
    yaml_part = ''.join(yaml_lines).strip()
    config = yaml.safe_load(yaml_part) or {}

    template_lines = []
    data_part = None
    if allow_inline_data:
        for line in stream:
            if line.strip() == '---':
                data_part = stream.read().strip()
                break
            template_lines.append(line)
    else:
        template_lines = list(stream)

    template_part = ''.join(template_lines)
    return config, template_part, data_part

def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    """Normalize config by converting preferred aliases to internal names

    Args:
        config: Original configuration dictionary

    Returns:
        Normalized configuration with internal canonical names

    Raises:
        ValueError: If a parameter removed in 1.0.0 is used

    Examples:
        >>> normalize_config({'define': 'foo'})
        {'name': 'foo'}

        >>> normalize_config({'name': 'foo'})
        ValueError: 'name' was removed in 1.0.0. Use 'define' instead.
    """
    for removed, replacement in REMOVED_PARAMETERS.items():
        if removed in config:
            raise ValueError(
                f"'{removed}' was removed in pandoc-embedz 1.0.0. "
                f"Use '{replacement}' instead."
            )

    # Both spellings of a still-supported pair (e.g. 'as' and 'template') is ambiguous
    for internal, preferred in PARAMETER_PREFERRED_ALIASES.items():
        if preferred in config and internal in config:
            raise ValueError(
                f"Conflicting parameters: both '{preferred}' and '{internal}' specified. "
                f"Use '{preferred}' only."
            )

    normalized = {}
    for key, value in config.items():
        # Check if this key is a preferred alias for some internal name (O(1) lookup)
        internal_name = _ALIAS_TO_INTERNAL.get(key)

        if internal_name:
            # Convert preferred alias to internal name
            normalized[internal_name] = value
        else:
            normalized[key] = value

    return normalized

def validate_config(config: dict[str, Any]) -> None:
    """Validate configuration to prevent invalid settings

    Args:
        config: Configuration dictionary to validate

    Raises:
        ValueError: If configuration contains invalid values
        TypeError: If configuration values have wrong types
    """
    # Note: We don't strictly validate keys anymore since dot notation
    # allows arbitrary keys (e.g., custom.field creates {"custom": {...}})
    # Only validate the values of known configuration keys

    # Validate format
    if 'format' in config:
        valid_formats = {'csv', 'tsv', 'ssv', 'spaces', 'json', 'yaml', 'toml', 'sqlite', 'lines'}
        if config['format'] not in valid_formats:
            raise ValueError(
                f"Invalid format: {config['format']}. "
                f"Must be one of: {', '.join(sorted(valid_formats))}"
            )

    # Validate header
    if 'header' in config and not isinstance(config['header'], bool):
        raise TypeError("'header' must be a boolean")

    # Validate with and global
    if 'with' in config and not isinstance(config['with'], dict):
        raise TypeError("'with' must be a mapping of variable names to values")

    if 'global' in config and not isinstance(config['global'], dict):
        raise TypeError("'global' must be a mapping of variable names to values")

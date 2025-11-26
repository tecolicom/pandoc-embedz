#!/usr/bin/env python3
"""pandoc-embedz: Pandoc filter for embedding data-driven content using Jinja2 templates

This filter allows you to embed data from various formats (CSV, TSV, JSON, YAML, etc.)
into your Markdown documents using Jinja2 template syntax within code blocks.
"""

from typing import Dict, Any, Tuple, Optional, Union, List
import panflute as pf
from jinja2 import Environment, FunctionLoader, TemplateNotFound
import pandas as pd
import yaml
import sys
import os

# Import from local modules
from .config import (
    load_template_from_saved,
    parse_attributes,
    parse_code_block,
    validate_config,
    normalize_config,
    load_config_file,
    deep_merge_dicts,
    SAVED_TEMPLATES
)
from .data_loader import _load_embedz_data

# Debug mode controlled by environment variable
DEBUG = os.getenv('PANDOC_EMBEDZ_DEBUG', '').lower() in ('1', 'true', 'yes')

def _debug(msg: str) -> None:
    """Print debug message to stderr if DEBUG is enabled"""
    if DEBUG:
        sys.stderr.write(f"[DEBUG] {msg}\n")

# Store global variables and control structures
GLOBAL_VARS: Dict[str, Any] = {}
GLOBAL_ENV: Optional[Environment] = None
CONTROL_STRUCTURES_STR: str = ""
KNOWN_EXCEPTIONS = (
    FileNotFoundError,
    ValueError,
    TypeError,
    yaml.YAMLError,
    pd.errors.ParserError,
    TemplateNotFound,
    KeyError,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions for process_embedz
#
# These functions encapsulate the main processing steps:
# 1. Utility functions (_get_jinja_env, _render_template, _build_render_context)
# 2. Configuration parsing (_parse_and_merge_config)
# 3. Template management (_process_template_references)
# 4. Variable preparation (_prepare_variables)
# 5. Data loading (_prepare_data_loading)
# 6. Template rendering (_render_embedz_template)


def _normalize_config_refs(value: Any) -> List[str]:
    """Normalize config references into a list of file paths."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        refs: List[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError("'config' entries must be file paths (strings)")
            refs.append(item)
        return refs
    raise TypeError("'config' must be a string or list of strings")


def _merge_config_sources(
    attr_config: Dict[str, Any],
    yaml_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge configuration from attributes, YAML, and external files."""
    attr_copy = dict(attr_config)
    yaml_copy = dict(yaml_config)

    config_refs: List[str] = []
    if 'config' in attr_copy:
        config_refs.extend(_normalize_config_refs(attr_copy.pop('config')))
    if 'config' in yaml_copy:
        config_refs.extend(_normalize_config_refs(yaml_copy.pop('config')))

    merged: Dict[str, Any] = {}
    for ref in config_refs:
        file_config = load_config_file(ref)
        merged = deep_merge_dicts(merged, file_config)

    merged = deep_merge_dicts(merged, attr_copy)
    merged = deep_merge_dicts(merged, yaml_copy)
    return merged

def _get_jinja_env() -> Environment:
    """Get or create global Jinja2 Environment with access to saved templates

    Returns:
        Environment: Shared Jinja2 Environment instance
    """
    global GLOBAL_ENV
    if GLOBAL_ENV is None:
        GLOBAL_ENV = Environment(loader=FunctionLoader(load_template_from_saved))
    return GLOBAL_ENV

def _render_template(template_str: str, context: Dict[str, Any]) -> str:
    """Unified template rendering with control structures prepended

    Args:
        template_str: Jinja2 template string
        context: Template rendering context

    Returns:
        str: Rendered template result
    """
    env = _get_jinja_env()
    full_template = CONTROL_STRUCTURES_STR + template_str
    template = env.from_string(full_template)
    return template.render(**context)

def _build_render_context(with_vars: Dict[str, Any], data: Optional[Any] = None) -> Dict[str, Any]:
    """Build render context for Jinja2 template rendering

    Args:
        with_vars: Local variables from 'with' section
        data: Optional data to include in context

    Returns:
        dict: Render context with global, with, and data variables
    """
    context = {
        **GLOBAL_VARS,           # Expand global variables
        **with_vars,             # Expand with variables (override globals)
        'global': GLOBAL_VARS,   # Also accessible as global.xxx
        'with': with_vars,       # Also accessible as with.xxx
    }
    if data is not None:
        context['data'] = data
    return context

def _parse_and_merge_config(
    elem: pf.CodeBlock,
    text: str
) -> Tuple[Dict[str, Any], str, Optional[str]]:
    """Parse and merge configuration from attributes and YAML header

    Args:
        elem: Pandoc CodeBlock element
        text: Code block text content

    Returns:
        tuple: (merged_config, template_part, data_part)
    """
    # Parse attributes from code block
    attr_config = parse_attributes(elem)
    _debug(f"Attribute config: {attr_config}")

    # Parse code block content
    yaml_config, template_part, data_part = parse_code_block(text)
    _debug(f"YAML config: {yaml_config}")

    # Special handling: if 'as' attribute without YAML header
    if not text.startswith('---') and 'as' in attr_config:
        # Try parsing content as YAML config (only when 'data' attribute present)
        parsed_as_yaml = False
        if 'data' in attr_config and text.strip():
            try:
                content_config = yaml.safe_load(text) or {}
                if isinstance(content_config, dict):
                    yaml_config = content_config
                    data_part = None
                    template_part = ''
                    parsed_as_yaml = True
            except yaml.YAMLError:
                pass

        # If not parsed as YAML, treat content as inline data
        if not parsed_as_yaml:
            data_part = text
            template_part = ''

    return _build_config_from_text(text, attr_config, yaml_config, template_part, data_part)


def _build_config_from_text(
    text: str,
    attr_config: Optional[Dict[str, Any]] = None,
    yaml_config: Optional[Dict[str, Any]] = None,
    template_part: Optional[str] = None,
    data_part: Optional[str] = None,
    allow_inline_data: bool = True
) -> Tuple[Dict[str, Any], str, Optional[str]]:
    """Shared helper to merge configs for both filter and standalone modes."""
    if yaml_config is None or template_part is None:
        yaml_config, template_part, data_part = parse_code_block(
            text, allow_inline_data=allow_inline_data
        )

    merged_attr = attr_config or {}

    # Merge configurations from external files, attributes, and YAML header
    config = _merge_config_sources(merged_attr, yaml_config)
    _debug(f"Merged config: {config}")

    # Normalize configuration (resolve aliases)
    config = normalize_config(config)
    _debug(f"Normalized config: {config}")

    # Validate configuration
    validate_config(config)

    return config, template_part, data_part

def _process_template_references(
    config: Dict[str, Any],
    template_part: str
) -> str:
    """Process template save/load operations

    Args:
        config: Configuration dictionary
        template_part: Template content

    Returns:
        str: Updated template_part (from saved template if 'as' is specified)

    Side effects:
        - Updates SAVED_TEMPLATES dictionary if 'name' is specified
        - Updates CONTROL_STRUCTURES_STR if template contains macro definitions

    Raises:
        ValueError: If referenced template is not found
    """
    global CONTROL_STRUCTURES_STR

    # Save named template
    template_name = config.get('name')
    if template_name:
        if template_name in SAVED_TEMPLATES:
            sys.stderr.write(f"Warning: Overwriting template '{template_name}'\n")
        SAVED_TEMPLATES[template_name] = template_part
        _debug(f"Saved template '{template_name}'")

        # If template contains macro definitions, add to CONTROL_STRUCTURES_STR
        # so macros are available globally without explicit import
        if '{%' in template_part and 'macro' in template_part:
            CONTROL_STRUCTURES_STR += template_part + '\n'
            _debug(f"Added macros from template '{template_name}' to global control structures")

    # Load saved template
    template_ref = config.get('as')
    if template_ref:
        if template_ref not in SAVED_TEMPLATES:
            raise ValueError(
                f"Template '{template_ref}' not found. "
                f"Define it first with define='{template_ref}'"
            )
        template_part = SAVED_TEMPLATES[template_ref]
        _debug(f"Loaded template '{template_ref}'")

    return template_part

def _prepare_variables(config: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare local and global variables for rendering

    Args:
        config: Configuration dictionary containing 'with', 'global', and/or 'preamble' keys

    Returns:
        dict: Local variables (with_vars)

    Side effects:
        Updates GLOBAL_VARS dictionary if 'global' key is present
        Updates CONTROL_STRUCTURES_STR if 'preamble' key is present
    """
    global CONTROL_STRUCTURES_STR

    # Process preamble (control structures for entire document)
    if 'preamble' in config:
        preamble_content = config['preamble']
        if isinstance(preamble_content, str):
            if preamble_content.strip():  # Only add non-empty content
                CONTROL_STRUCTURES_STR += preamble_content + '\n'
                _debug(f"Added preamble to control structures")
        else:
            raise ValueError(
                f"'preamble' must be a string, got {type(preamble_content).__name__}"
            )

    # Prepare local variables
    with_vars: Dict[str, Any] = {}
    if 'with' in config:
        with_vars.update(config['with'])
        _debug(f"Local variables (with): {with_vars}")

    # Process global variables if present
    if 'global' in config:
        for key, value in config['global'].items():
            # Check if value contains template syntax
            if isinstance(value, str) and ('{{' in value or '{%' in value):
                # Process template variable using unified rendering
                context = _build_render_context({})  # Empty with_vars, no data
                rendered = _render_template(value, context)
                # Remove leading newlines that may be added by preamble
                value = rendered.lstrip('\n')
                _debug(f"Expanded global variable '{key}': {value}")

            GLOBAL_VARS[key] = value
        _debug(f"Global variables: {GLOBAL_VARS}")

    return with_vars

def _prepare_data_loading(
    config: Dict[str, Any],
    with_vars: Dict[str, Any]
) -> Tuple[Optional[Union[str, Dict[str, Any]]], Optional[str], bool, Dict[str, Any]]:
    """Prepare data loading parameters with query template expansion

    Args:
        config: Configuration dictionary
        with_vars: Local variables from 'with' section

    Returns:
        tuple: (data_file, data_format, has_header, load_kwargs)
    """
    data_file = config.get('data')
    data_format = config.get('format')  # None = auto-detect
    has_header = config.get('header', True)

    _debug(f"Data file: {data_file}, format: {data_format}, has_header: {has_header}")

    # Prepare format-specific kwargs (e.g., for SQLite)
    load_kwargs = {}
    if 'table' in config:
        load_kwargs['table'] = config['table']
        _debug(f"SQLite table: {config['table']}")

    if 'query' in config:
        query_template = config['query']
        # Expand Jinja2 template variables in query if present
        if '{{' in query_template or '{%' in query_template:
            context = _build_render_context(with_vars)
            query_value = _render_template(query_template, context)
            load_kwargs['query'] = query_value
            _debug(f"Expanded query: {query_value}")
        else:
            load_kwargs['query'] = query_template
            _debug(f"Query: {query_template}")

    return data_file, data_format, has_header, load_kwargs

def _split_template_and_newlines(template_part: str) -> Tuple[str, str]:
    """Return template body and trailing newline suffix (at least one newline)."""
    if not template_part:
        return '', '\n'
    stripped = template_part.rstrip('\n')
    newline_count = len(template_part) - len(stripped)
    if newline_count == 0:
        return template_part, '\n'
    return template_part[:-newline_count], '\n' * newline_count


def _render_embedz_template(
    template_part: str,
    data: Union[List[Any], Dict[str, Any]],
    with_vars: Dict[str, Any]
) -> str:
    """Render template with data and variables

    Args:
        template_part: Jinja2 template string
        data: Loaded data (list or dict)
        with_vars: Local variables from 'with' section

    Returns:
        str: Rendered template result
    """
    # Build render context and render template using unified rendering
    context = _build_render_context(with_vars, data)
    _debug(f"Rendering template with context keys: {list(context.keys())}")

    template_body, newline_suffix = _split_template_and_newlines(template_part)
    result = _render_template(template_body, context)
    _debug(f"Rendered result length: {len(result)} characters")
    _debug(f"Rendered result (raw): {repr(result)}")
    result = (result or '') + newline_suffix
    _debug(f"Final result (with newline suffix): {repr(result)}")

    return result


def _execute_embedz_pipeline(
    config: Dict[str, Any],
    template_part: str,
    data_part: Optional[str]
) -> Tuple[Optional[str], Optional[str], bool]:
    """Run the core embedz pipeline shared by block and standalone modes."""
    _debug("Step 3: Preparing variables")
    with_vars = _prepare_variables(config)

    _debug("Step 4: Preparing data loading")
    data_file, data_format, has_header, load_kwargs = _prepare_data_loading(
        config, with_vars
    )

    _debug("Step 5: Loading data")
    data = _load_embedz_data(
        data_file, data_part, config, data_format, has_header, load_kwargs
    )

    template_has_content = bool(template_part.strip())
    definition_block = bool(config.get('name')) or not template_has_content
    if not data and definition_block:
        _debug("Definition-only block, returning empty output")
        return None, data_file, has_header

    render_data: Union[List[Any], Dict[str, Any]] = data or []

    _debug("Step 6: Rendering template")
    result = _render_embedz_template(template_part, render_data, with_vars)

    return result, data_file, has_header

def print_error_info(
    e: Exception,
    template_part: str,
    config: Dict[str, Any],
    data_file: Optional[str],
    has_header: bool,
    data_part: Optional[str] = None
) -> None:
    """Print error information to stderr"""
    sys.stderr.write(f"\n{'='*60}\n")
    sys.stderr.write(f"pandoc-embedz Error\n")
    sys.stderr.write(f"{'='*60}\n")
    sys.stderr.write(f"Error: {e}\n")

    # Add helpful hints for common errors
    error_msg = str(e)
    if 'ParserError' in type(e).__name__ or 'Expected' in error_msg:
        sys.stderr.write(f"\nHint: Data parsing failed. Common causes:\n")
        sys.stderr.write(f"  - SSV format with spaces in field values\n")
        sys.stderr.write(f"  - Inconsistent number of fields\n")
        sys.stderr.write(f"  - Try using 'tsv' or 'csv' format instead\n")
    elif 'FileNotFoundError' in type(e).__name__:
        sys.stderr.write(f"\nHint: Data file not found.\n")
        sys.stderr.write(f"  - Check the file path: {data_file}\n")
        sys.stderr.write(f"  - Use relative paths from the markdown file location\n")
    elif 'Template' in error_msg or 'not found' in error_msg.lower():
        sys.stderr.write(f"\nHint: Template issue.\n")
        sys.stderr.write(f"  - Check template syntax\n")
        sys.stderr.write(f"  - Ensure referenced templates are defined first\n")

    sys.stderr.write(f"\nConfig:\n")
    sys.stderr.write(f"  Data file: {data_file or 'inline'}\n")
    sys.stderr.write(f"  Format: {config.get('format', 'auto-detect')}\n")
    sys.stderr.write(f"  Header: {has_header}\n")
    sys.stderr.write(f"  Template: {config.get('as', config.get('name', 'inline'))}\n")

    if data_part and len(data_part) < 500:
        sys.stderr.write(f"\nInline data:\n")
        sys.stderr.write(f"{'-'*60}\n")
        sys.stderr.write(f"{data_part}\n")
        sys.stderr.write(f"{'-'*60}\n")

    sys.stderr.write(f"\nFor more information, see the documentation.\n")
    sys.stderr.write(f"{'='*60}\n\n")


def process_embedz(elem: pf.Element, doc: pf.Doc) -> Union[pf.Element, List[pf.Element], None]:
    """Process code blocks with .embedz class

    Args:
        elem: Pandoc element to process
        doc: Pandoc document

    Returns:
        Processed element(s) or None
    """
    # Guard: return element unchanged if not an embedz code block
    if not isinstance(elem, pf.CodeBlock):
        return elem
    if 'embedz' not in elem.classes:
        return elem

    text = elem.text.strip()
    _debug("=" * 60)
    _debug("Processing embedz code block")

    try:
        # Step 1: Parse and merge configuration
        _debug("Step 1: Parsing configuration")
        config, template_part, data_part = _parse_and_merge_config(elem, text)

        # Step 2: Process template references (save/load)
        _debug("Step 2: Processing template references")
        template_part = _process_template_references(config, template_part)

        # Steps 3-6: Shared pipeline
        result, data_file, has_header = _execute_embedz_pipeline(
            config, template_part, data_part
        )

        _debug("Processing complete")
        _debug("=" * 60)

        if result is None:
            return []

        # Convert to AST (Pandoc re-parses the markdown text)
        return pf.convert_text(result, input_format='markdown')

    except KNOWN_EXCEPTIONS as e:
        # Handle known exceptions with detailed error info
        print_error_info(
            e,
            template_part if 'template_part' in locals() else 'N/A',
            config if 'config' in locals() else {},
            data_file if 'data_file' in locals() else None,
            has_header if 'has_header' in locals() else True,
            data_part if 'data_part' in locals() else None
        )
        # In test environment, raise exception; otherwise exit
        if os.environ.get('PYTEST_CURRENT_TEST'):
            raise
        sys.exit(1)
    except Exception as e:
        # Unexpected exception - always show and raise
        sys.stderr.write(f"\n{'='*60}\n")
        sys.stderr.write(f"pandoc-embedz: Unexpected Error\n")
        sys.stderr.write(f"{'='*60}\n")
        sys.stderr.write(f"Error: {type(e).__name__}: {e}\n")
        sys.stderr.write(f"This may be a bug. Please report at:\n")
        sys.stderr.write(f"https://github.com/tecolicom/pandoc-embedz/issues\n")
        sys.stderr.write(f"{'='*60}\n\n")
        raise

def main() -> None:
    """Backward-compatible entry point delegating to pandoc_embedz.main."""
    from .main import main as cli_main
    cli_main()


if __name__ == '__main__':  # pragma: no cover
    main()

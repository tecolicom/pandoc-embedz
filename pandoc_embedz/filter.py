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
    validate_file_path,
    load_template_from_saved,
    parse_attributes,
    parse_code_block,
    validate_config,
    SAVED_TEMPLATES
)
from .data_loader import _load_embedz_data

# Store global variables and control structures
GLOBAL_VARS: Dict[str, Any] = {}
CONTROL_STRUCTURES: List[str] = []

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions for process_embedz
#
# These functions encapsulate the main processing steps:
# 1. Utility functions (_create_jinja_env, _build_render_context)
# 2. Configuration parsing (_parse_and_merge_config)
# 3. Template management (_process_template_references)
# 4. Variable preparation (_prepare_variables)
# 5. Data loading (_prepare_data_loading)
# 6. Template rendering (_render_embedz_template)

def _create_jinja_env() -> Environment:
    """Create Jinja2 Environment with access to saved templates

    Returns:
        Environment: Configured Jinja2 Environment
    """
    return Environment(loader=FunctionLoader(load_template_from_saved))

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

    # Parse code block content
    yaml_config, template_part, data_part = parse_code_block(text)

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

    # Merge configurations: YAML takes precedence over attributes
    config = {**attr_config, **yaml_config}

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
        - Updates CONTROL_STRUCTURES list if template contains macro definitions

    Raises:
        ValueError: If referenced template is not found
    """
    # Save named template
    template_name = config.get('name')
    if template_name:
        if template_name in SAVED_TEMPLATES:
            sys.stderr.write(f"Warning: Overwriting template '{template_name}'\n")
        SAVED_TEMPLATES[template_name] = template_part

        # If template contains macro definitions, add to CONTROL_STRUCTURES
        # so macros are available globally without explicit import
        if '{%' in template_part and 'macro' in template_part:
            CONTROL_STRUCTURES.append(template_part)

    # Load saved template
    template_ref = config.get('as')
    if template_ref:
        if template_ref not in SAVED_TEMPLATES:
            raise ValueError(
                f"Template '{template_ref}' not found. "
                f"Define it first with name='{template_ref}'"
            )
        template_part = SAVED_TEMPLATES[template_ref]

    return template_part

def _prepare_variables(config: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare local and global variables for rendering

    Args:
        config: Configuration dictionary containing 'with' and/or 'global' keys

    Returns:
        dict: Local variables (with_vars)

    Side effects:
        Updates GLOBAL_VARS dictionary and CONTROL_STRUCTURES list if 'global' key is present
    """
    # Prepare local variables
    with_vars: Dict[str, Any] = {}
    if 'with' in config:
        with_vars.update(config['with'])

    # Process global variables if present
    if 'global' in config:
        env = _create_jinja_env()

        for key, value in config['global'].items():
            # Check if value contains template syntax
            if isinstance(value, str) and ('{{' in value or '{%' in value):
                stripped = value.strip()
                # Check if this is a control structure (macro, import, include)
                if (stripped.startswith('{%') and
                    not stripped.startswith('{{') and
                    ('macro' in stripped or 'import' in stripped or 'include' in stripped)):
                    # Control structure - collect globally for use in all template expansions
                    CONTROL_STRUCTURES.append(value)
                    continue

                # Process template variable
                # Prepend all control structures if any exist
                if CONTROL_STRUCTURES:
                    template_str = '\n'.join(CONTROL_STRUCTURES) + '\n' + value
                else:
                    template_str = value

                template = env.from_string(template_str)
                rendered = template.render(
                    **GLOBAL_VARS,
                    **{'global': GLOBAL_VARS}
                )

                # Remove leading newlines from control structures that produce no output
                value = rendered.lstrip('\n') if CONTROL_STRUCTURES else rendered

            GLOBAL_VARS[key] = value

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

    # Prepare format-specific kwargs (e.g., for SQLite)
    load_kwargs = {}
    if 'table' in config:
        load_kwargs['table'] = config['table']

    if 'query' in config:
        query_template = config['query']
        # Expand Jinja2 template variables in query if present
        if '{{' in query_template or '{%' in query_template:
            env = _create_jinja_env()
            # Prepend control structures (macro imports) if any exist
            if CONTROL_STRUCTURES:
                template_str = '\n'.join(CONTROL_STRUCTURES) + '\n' + query_template
            else:
                template_str = query_template
            template = env.from_string(template_str)
            context = _build_render_context(with_vars)
            query_value = template.render(**context)
            load_kwargs['query'] = query_value
        else:
            load_kwargs['query'] = query_template

    return data_file, data_format, has_header, load_kwargs

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
    # Create Jinja2 Environment with access to saved templates
    env = _create_jinja_env()

    # Build render context and render template
    context = _build_render_context(with_vars, data)
    # Prepend control structures (macro imports) if any exist
    if CONTROL_STRUCTURES:
        template_str = '\n'.join(CONTROL_STRUCTURES) + '\n' + template_part
    else:
        template_str = template_part
    template = env.from_string(template_str)
    result = template.render(**context)

    # Ensure output ends with newline (prevents concatenation with next paragraph)
    if result and not result.endswith('\n'):
        result += '\n'

    return result

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

    try:
        # Step 1: Parse and merge configuration
        config, template_part, data_part = _parse_and_merge_config(elem, text)

        # Step 2: Process template references (save/load)
        template_part = _process_template_references(config, template_part)

        # Step 3: Prepare variables (with and global)
        with_vars = _prepare_variables(config)

        # Step 4: Prepare data loading parameters
        data_file, data_format, has_header, load_kwargs = _prepare_data_loading(
            config, with_vars
        )

        # Step 5: Load data
        data = _load_embedz_data(
            data_file, data_part, config, data_format, has_header, load_kwargs
        )

        # If no data, only save template (no output)
        if not data:
            return []

        # Step 6: Render template
        result = _render_embedz_template(template_part, data, with_vars)

        return pf.convert_text(result, input_format='markdown')

    except (FileNotFoundError, ValueError, TypeError, yaml.YAMLError,
            pd.errors.ParserError, TemplateNotFound, KeyError) as e:
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
    """Entry point for pandoc filter"""
    pf.run_filter(process_embedz)

if __name__ == '__main__':
    main()

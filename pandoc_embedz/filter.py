#!/usr/bin/env python3
"""pandoc-embedz: Pandoc filter for embedding data-driven content using Jinja2 templates

This filter allows you to embed data from various formats (CSV, TSV, JSON, YAML, etc.)
into your Markdown documents using Jinja2 template syntax within code blocks.
"""

from typing import Dict, Any, Tuple, Optional, Union, List, Callable
import panflute as pf
from jinja2 import Environment, FunctionLoader, TemplateNotFound
import pandas as pd
import yaml
import sys
import os

# Use regex module if available (supports Unicode properties like \p{P})
# Falls back to standard re module
try:
    import regex as re
    REGEX_MODULE = 'regex'
except ImportError:
    import re
    REGEX_MODULE = 're'

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

def _debug(msg: str, *args: Any) -> None:
    """Print debug message to stderr if DEBUG is enabled

    Uses lazy evaluation - formatting only happens if DEBUG is True.
    Usage: _debug("Message: %s", value)
    """
    if DEBUG:
        if args:
            msg = msg % args
        sys.stderr.write(f"[DEBUG] {msg}\n")

def _has_template_syntax(text: str) -> bool:
    """Check if text contains Jinja2 template syntax.

    Args:
        text: Text to check

    Returns:
        True if text contains Jinja2 variable or control syntax
    """
    return '{{' in text or '{%' in text

# Store global variables and control structures
GLOBAL_VARS: Dict[str, Any] = {}
GLOBAL_ENV: Optional[Environment] = None
CONTROL_STRUCTURES_PARTS: List[str] = []
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
# 7. Result validation (_validate_convert_result)


def _validate_convert_result(result: str, ast_elements: List[Any]) -> List[Any]:
    """Validate that pf.convert_text() produced expected result.

    When the template output starts with a fenced code block (```),
    we expect pf.convert_text() to return a CodeBlock element. If it returns
    something else (e.g., Table), the identifier likely contains problematic
    characters that Pandoc cannot parse correctly.

    Args:
        result: The rendered template result (markdown string)
        ast_elements: The result from pf.convert_text()

    Returns:
        The ast_elements if valid

    Raises:
        ValueError: If code block was expected but not produced
    """
    # Check if template output starts with a fenced code block
    stripped = result.lstrip()
    if not stripped.startswith('```'):
        return ast_elements

    # Extract the identifier from the code block header for error message
    first_line = stripped.split('\n')[0]

    # Check if we got a CodeBlock
    if ast_elements and isinstance(ast_elements[0], pf.CodeBlock):
        return ast_elements

    # Code block expected but not produced - likely identifier parsing issue
    actual_types = [type(e).__name__ for e in ast_elements]
    raise ValueError(
        f"Template output starts with fenced code block but Pandoc parsed it as "
        f"{actual_types} instead of CodeBlock.\n"
        f"Code block header: {first_line}\n"
        f"This usually happens when the identifier (#id:...) contains "
        f"characters that Pandoc cannot parse correctly, such as:\n"
        f"  - Full-width parentheses: （ ）\n"
        f"  - Brackets: [ ] 【 】\n"
        f"  - Other special characters\n"
        f"Solution: Remove problematic characters from the identifier, "
        f"or use a separate 'id' and 'title/caption' in your template."
    )


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

def _filter_to_dict(data: List[Dict[str, Any]], key: str,
                    strict: bool = True,
                    transpose: bool = False) -> Dict[Any, Dict[str, Any]]:
    """Convert a list of dicts to a dict keyed by a specified field.

    Args:
        data: List of dictionaries
        key: Field name to use as dictionary key
        strict: If True (default), raise ValueError on duplicate keys
        transpose: If True, also add column-keyed dicts for dual access

    Returns:
        Dictionary with values from 'key' field as keys.
        If transpose=True, also includes column names as keys mapping to
        {key_value: column_value} dicts.

    Example:
        data | to_dict('year')
        [{'year': 2023, 'value': 100}, {'year': 2024, 'value': 200}]
        -> {2023: {'year': 2023, 'value': 100}, 2024: {'year': 2024, 'value': 200}}

        data | to_dict('year', strict=False)
        Allows duplicate keys (last value wins)

        data | to_dict('year', transpose=True)
        -> {2023: {'year': 2023, 'value': 100}, 2024: {...},
            'value': {2023: 100, 2024: 200}}
        Enables both result[2023].value and result.value[2023] access patterns
    """
    if not isinstance(data, list):
        raise TypeError(f"to_dict expects a list, got {type(data).__name__}")
    if strict:
        result = {}
        for row in data:
            k = row[key]
            if k in result:
                raise ValueError(f"to_dict: duplicate key '{k}' in field '{key}'")
            result[k] = row
    else:
        result = {row[key]: row for row in data}

    if transpose and data:
        # Add column-keyed dicts for each field (except the key field)
        columns = [col for col in data[0].keys() if col != key]
        for col in columns:
            result[col] = {row[key]: row[col] for row in data}

    return result


def _filter_raise(message: str) -> None:
    """Raise an error with a custom message.

    Usage in template:
        {{ "error message" | raise }}

    Args:
        message: Error message to display

    Raises:
        ValueError: Always raises with the given message
    """
    raise ValueError(message)


def _filter_regex_replace(value: str, pattern: str, replacement: str = '',
                          ignorecase: bool = False,
                          multiline: bool = False,
                          count: int = 0) -> str:
    """Replace substring using regular expression.

    Compatible with Ansible's regex_replace filter.
    Maps to Python's re.sub.

    Usage in template:
        {{ "ansible" | regex_replace('^a.*i(.*)$', 'a\\1') }}
        {{ value | regex_replace('\\W', '') }}  # Remove non-word characters

    Args:
        value: Input string
        pattern: Regular expression pattern
        replacement: Replacement string (default: empty string)
        ignorecase: Case-insensitive matching (default: False)
        multiline: Multiline mode (default: False)
        count: Maximum number of replacements (0 = unlimited)

    Returns:
        String with replacements applied
    """
    flags = 0
    if ignorecase:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.MULTILINE
    return re.sub(pattern, replacement, str(value), count=count, flags=flags)


def _filter_regex_search(value: str, pattern: str,
                         ignorecase: bool = False,
                         multiline: bool = False) -> str:
    """Search for a pattern in a string and return the match.

    Compatible with Ansible's regex_search filter.
    Maps to Python's re.search.

    Usage in template:
        {{ "hello world" | regex_search('world') }}         # Returns 'world'
        {{ "foo bar" | regex_search('baz') }}               # Returns ''
        {{ "備考: 保留中" | regex_search('保留|済|喪中') }} # Returns '保留'

    Args:
        value: Input string
        pattern: Regular expression pattern
        ignorecase: Case-insensitive matching (default: False)
        multiline: Multiline mode (default: False)

    Returns:
        The matched string, or empty string if no match
    """
    flags = 0
    if ignorecase:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.MULTILINE
    match = re.search(pattern, str(value), flags=flags)
    return match.group(0) if match else ''


def _get_jinja_env() -> Environment:
    """Get or create global Jinja2 Environment with access to saved templates

    Returns:
        Environment: Shared Jinja2 Environment instance
    """
    global GLOBAL_ENV
    if GLOBAL_ENV is None:
        GLOBAL_ENV = Environment(loader=FunctionLoader(load_template_from_saved))
        # Register custom filters
        GLOBAL_ENV.filters['to_dict'] = _filter_to_dict
        GLOBAL_ENV.filters['raise'] = _filter_raise
        GLOBAL_ENV.filters['regex_replace'] = _filter_regex_replace
        GLOBAL_ENV.filters['regex_search'] = _filter_regex_search
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
    control_structures_str = '\n'.join(CONTROL_STRUCTURES_PARTS)
    if control_structures_str:
        control_structures_str = control_structures_str.rstrip('\n') + '\n'
    full_template = control_structures_str + template_str
    template = env.from_string(full_template)
    result = template.render(**context)
    # Strip leading newline caused by control structures (e.g., macro definitions)
    if control_structures_str and result.startswith('\n'):
        result = result[1:]
    return result

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
    _debug("Attribute config: %s", attr_config)

    # Parse code block content
    yaml_config, template_part, data_part = parse_code_block(text)
    _debug("YAML config: %s", yaml_config)

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
    _debug("Merged config: %s", config)

    # Normalize configuration (resolve aliases)
    config = normalize_config(config)
    _debug("Normalized config: %s", config)

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
        - Updates CONTROL_STRUCTURES_PARTS if template contains macro definitions

    Raises:
        ValueError: If referenced template is not found
    """
    global CONTROL_STRUCTURES_PARTS

    # Save named template
    template_name = config.get('name')
    if template_name:
        if template_name in SAVED_TEMPLATES:
            sys.stderr.write(f"Warning: Overwriting template '{template_name}'\n")
        SAVED_TEMPLATES[template_name] = template_part
        _debug("Saved template '%s'", template_name)

        # If template contains macro definitions, add to CONTROL_STRUCTURES_PARTS
        # so macros are available globally without explicit import
        if _has_template_syntax(template_part) and 'macro' in template_part:
            CONTROL_STRUCTURES_PARTS.append(template_part)
            _debug("Added macros from template '%s' to global control structures", template_name)

    # Load saved template
    template_ref = config.get('as')
    if template_ref:
        if template_ref not in SAVED_TEMPLATES:
            raise ValueError(
                f"Template '{template_ref}' not found. "
                f"Define it first with define='{template_ref}'"
            )
        template_part = SAVED_TEMPLATES[template_ref]
        _debug("Loaded template '%s'", template_ref)

    return template_part

def _prepare_preamble_and_with(config: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare preamble and with variables (before data loading)

    Args:
        config: Configuration dictionary containing 'preamble' and/or 'with' keys

    Returns:
        dict: Local variables (with_vars)

    Side effects:
        Updates CONTROL_STRUCTURES_PARTS if 'preamble' key is present
    """
    global CONTROL_STRUCTURES_PARTS

    # Process preamble
    if 'preamble' in config:
        preamble_content = config['preamble']
        if isinstance(preamble_content, str):
            if preamble_content.strip():  # Only add non-empty content
                CONTROL_STRUCTURES_PARTS.append(preamble_content)
                _debug("Added preamble to control structures")
        else:
            raise ValueError(
                f"'preamble' must be a string, got {type(preamble_content).__name__}"
            )

    # Process with variables (no data access - these are input parameters)
    with_vars: Dict[str, Any] = {}
    if 'with' in config:
        with_vars.update(config['with'])
        _debug("Local variables (with): %s", with_vars)

    return with_vars


def _process_nested_structure(
    value: Any,
    context: Dict[str, Any],
    processor: Callable[[str, Dict[str, Any], str], Any],
    path: str = ""
) -> Any:
    """Recursively process nested structures (dict/list) with a string processor.

    Args:
        value: Value to process (can be str, dict, list, or other)
        context: Template rendering context
        processor: Function to process string values, signature: (str, context, path) -> Any
        path: Current path in the nested structure (e.g., "foo.bar.baz")

    Returns:
        Processed value with same structure
    """
    if isinstance(value, str):
        return processor(value, context, path)
    elif isinstance(value, dict):
        return {k: _process_nested_structure(v, context, processor,
                    f"{path}.{k}" if path else k) for k, v in value.items()}
    elif isinstance(value, list):
        return [_process_nested_structure(item, context, processor,
                    f"{path}[{i}]") for i, item in enumerate(value)]
    else:
        # Non-string primitives (int, float, bool, None) pass through unchanged
        return value


def _set_nested_value(target: Dict[str, Any], key: str, value: Any) -> None:
    """Set a value in a nested dictionary using dot-separated key.

    If key contains dots, it is interpreted as a path to a nested location.
    Intermediate dictionaries are created if they don't exist.
    If a parent exists and is a dictionary, the value is added/updated.

    Args:
        target: The dictionary to update
        key: The key, possibly dot-separated (e.g., "foo.bar.baz")
        value: The value to set

    Examples:
        _set_nested_value(d, "foo", 1)           # d["foo"] = 1
        _set_nested_value(d, "foo.bar", 2)       # d["foo"]["bar"] = 2
        _set_nested_value(d, "foo.bar.baz", 3)   # d["foo"]["bar"]["baz"] = 3
    """
    if '.' not in key:
        target[key] = value
        return

    parts = key.split('.')
    current = target

    # Navigate to parent, creating intermediate dicts as needed
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            # Parent exists but is not a dict - cannot add nested key
            raise ValueError(
                f"Cannot set '{key}': '{part}' is not a dictionary"
            )
        current = current[part]

    # Set the final value
    current[parts[-1]] = value


def _apply_aliases(alias_config: Dict[str, str]) -> None:
    """Apply aliases to all dicts in GLOBAL_VARS.

    For each alias mapping (e.g., {'のアレ': 'ラベル'}), recursively walk
    through GLOBAL_VARS and add the alias key wherever the source key exists.

    Args:
        alias_config: Dictionary mapping alias names to source names
                      e.g., {'のアレ': 'ラベル'}

    Side effects:
        Modifies dicts in GLOBAL_VARS by adding alias keys
    """
    def add_aliases_recursive(obj: Any) -> None:
        """Recursively add aliases to all dicts in obj."""
        if isinstance(obj, dict):
            # First, add aliases to this dict
            for alias_name, source_name in alias_config.items():
                if source_name in obj and alias_name not in obj:
                    obj[alias_name] = obj[source_name]
                    _debug("Added alias '%s' -> '%s': %r", alias_name, source_name, obj[source_name])
            # Then, recurse into nested values
            for value in obj.values():
                add_aliases_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                add_aliases_recursive(item)

    add_aliases_recursive(GLOBAL_VARS)
    _debug("Applied aliases: %s", alias_config)


def _process_bind_section(
    bind_config: Dict[str, Any],
    with_vars: Dict[str, Any],
    data: Optional[Any],
    env: Environment
) -> None:
    """Process bind section: evaluate expressions with type preservation.

    Keys can use dot notation to set nested values:
        bind:
          foo: data | first           # GLOBAL_VARS["foo"] = ...
          foo.bar: foo.value          # GLOBAL_VARS["foo"]["bar"] = ...

    Args:
        bind_config: Dictionary of variable names to expressions
        with_vars: Local variables from 'with' section
        data: Loaded data (available for expression evaluation)
        env: Jinja2 Environment

    Side effects:
        Updates GLOBAL_VARS dictionary
    """
    def eval_expression(expr_str: str, ctx: Dict[str, Any], path: str) -> Any:
        """Evaluate expression and preserve type."""
        expr_str = expr_str.strip()
        compiled = env.compile_expression(expr_str)
        result = compiled(**ctx)
        _debug("Evaluated expression '%s' -> %r (type: %s)",
               expr_str, result, type(result).__name__)
        if result is None:
            sys.stderr.write(f"Warning: bind '{path}' evaluated to None: '{expr_str}'\n")
        return result

    for bind_key, bind_expr in bind_config.items():
        context = _build_render_context(with_vars, data)
        result = _process_nested_structure(bind_expr, context, eval_expression, bind_key)
        _set_nested_value(GLOBAL_VARS, bind_key, result)
        _debug("Bound '%s': %r (type: %s)", bind_key, result, type(result).__name__)


def _expand_global_variables(
    config: Dict[str, Any],
    with_vars: Dict[str, Any],
    data: Optional[Any] = None
) -> None:
    """Expand global variables with access to loaded data

    Processing order: bind: -> global:
    - bind: evaluates expressions with type preservation
    - global: expands templates to strings

    Both support nested structures processed recursively.

    Args:
        config: Configuration dictionary containing 'global' and/or 'bind' keys
        with_vars: Local variables from 'with' section
        data: Loaded data (available for template expansion)

    Side effects:
        Updates GLOBAL_VARS dictionary
    """
    def expand_template(text: str, ctx: Dict[str, Any], path: str) -> str:
        """Expand template if it contains Jinja2 syntax."""
        if _has_template_syntax(text):
            rendered = _render_template(text, ctx)
            return rendered.lstrip('\n')
        return text

    env = _get_jinja_env()

    # Process bind: first (so global: can reference bound variables)
    if 'bind' in config and isinstance(config['bind'], dict):
        _process_bind_section(config['bind'], with_vars, data, env)

    # Process global: section
    if 'global' in config:
        for key, value in config['global'].items():
            context = _build_render_context(with_vars, data)
            expanded = _process_nested_structure(value, context, expand_template)
            _set_nested_value(GLOBAL_VARS, key, expanded)
            _debug("Set global variable '%s': %r", key, expanded)

    # Process alias: section (add aliases to all dicts in GLOBAL_VARS)
    if 'alias' in config and isinstance(config['alias'], dict):
        _apply_aliases(config['alias'])

    if GLOBAL_VARS:
        _debug("Global variables: %s", GLOBAL_VARS)


def _resolve_data_variable(
    data_value: Optional[Union[str, Dict[str, Any]]]
) -> Optional[Union[List[Any], Dict[str, Any]]]:
    """Resolve data= value as a variable reference from GLOBAL_VARS.

    Called before _load_embedz_data to check if data= refers to an existing
    variable instead of a file path. Only dict/list variables (typically from
    bind:) can be referenced; string variables (from global:) are ignored.

    Args:
        data_value: The value from data= attribute (string or dict for multi-table)

    Returns:
        The variable's data (dict or list) if found, None to proceed with file loading

    Resolution rules:
        1. Non-string or None -> None (proceed to file loading)
        2. Starts with './' or '/' -> None (explicit file path)
        3. Try to resolve as variable (supports dot notation for nested access)
        4. If resolved to dict/list -> return that object
        5. Otherwise -> None (will attempt file loading, may fail)
    """
    if not isinstance(data_value, str):
        return None

    # Explicit file path: starts with './' or '/'
    if data_value.startswith('./') or data_value.startswith('/'):
        return None

    # Try to resolve variable (supports dot notation like "IR年度別.報告件数")
    obj = _resolve_nested_variable(data_value, GLOBAL_VARS)
    if obj is not None:
        if isinstance(obj, (dict, list)):
            _debug("Resolved data='%s' as variable: %s", data_value, type(obj).__name__)
            return obj
        _debug("Variable '%s' resolved but is not dict/list (type: %s), treating as file path",
               data_value, type(obj).__name__)

    return None


def _resolve_nested_variable(
    path: str,
    context: Dict[str, Any]
) -> Optional[Any]:
    """Resolve a dot-notated variable path from context.

    Args:
        path: Variable path like "foo" or "foo.bar.baz"
        context: Dictionary to look up variables from

    Returns:
        The resolved value, or None if not found
    """
    parts = path.split('.')
    obj = context.get(parts[0])
    if obj is None:
        return None

    for part in parts[1:]:
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            return None

    return obj


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

    _debug("Data file: %s, format: %s, has_header: %s", data_file, data_format, has_header)

    # Prepare format-specific kwargs (e.g., for SQLite, SSV with columns)
    load_kwargs = {}
    if 'table' in config:
        load_kwargs['table'] = config['table']
        _debug("SQLite table: %s", config['table'])

    if 'columns' in config:
        try:
            load_kwargs['columns'] = int(config['columns'])
        except (ValueError, TypeError):
            raise ValueError(f"'columns' must be an integer, got: {config['columns']!r}")
        _debug("SSV columns: %s", config['columns'])

    if 'query' in config:
        query_template = config['query']
        # Expand Jinja2 template variables in query if present
        if _has_template_syntax(query_template):
            context = _build_render_context(with_vars)
            query_value = _render_template(query_template, context)
            load_kwargs['query'] = query_value
            _debug("Expanded query: %s", query_value)
        else:
            load_kwargs['query'] = query_template
            _debug("Query: %s", query_template)

    return data_file, data_format, has_header, load_kwargs

def _split_template_and_newlines(template_part: str) -> Tuple[str, str]:
    """Return template body and trailing newline suffix (at least one newline)."""
    if not template_part:
        return '', '\n'
    stripped = template_part.rstrip('\n')
    newline_count = len(template_part) - len(stripped)
    return stripped, '\n' * max(1, newline_count)


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
    _debug("Rendering template with context keys: %s", list(context.keys()))

    template_body, newline_suffix = _split_template_and_newlines(template_part)
    result = _render_template(template_body, context)
    _debug("Rendered result length: %d characters", len(result))
    _debug("Rendered result (raw): %r", result)
    result = (result or '') + newline_suffix
    _debug("Final result (with newline suffix): %r", result)

    return result


def _execute_embedz_pipeline(
    config: Dict[str, Any],
    template_part: str,
    data_part: Optional[str]
) -> Tuple[Optional[str], Optional[str], bool]:
    """Run the core embedz pipeline shared by block and standalone modes.

    Processing order (Steps 3-7, continuing from process_embedz Steps 1-2):
    3. Prepare preamble and with variables (input parameters)
    4. Prepare data loading (query expansion uses with vars and existing GLOBAL_VARS)
    5. Load data
    6. Expand global variables (with access to loaded data)
    7. Render template

    Note: with: variables are input parameters, usable in query:.
          global: variables in the same block can reference loaded data.
    """
    _debug("Step 3: Preparing preamble and with variables")
    with_vars = _prepare_preamble_and_with(config)

    _debug("Step 4: Preparing data loading")
    data_file, data_format, has_header, load_kwargs = _prepare_data_loading(
        config, with_vars
    )

    _debug("Step 5: Loading data")
    data = _resolve_data_variable(data_file)
    if data is not None:
        if data_part:
            raise ValueError(
                "Cannot specify both data= variable reference and inline data. "
                "Use either 'data: varname' or provide inline data after '---', not both."
            )
        # Apply query to variable data if specified
        if 'query' in load_kwargs:
            from .data_loader import _apply_sql_query
            # Convert dict to list if needed (e.g., from to_dict result)
            if isinstance(data, dict):
                data_list = list(data.values())
            else:
                data_list = data
            df = pd.DataFrame(data_list)
            data = _apply_sql_query(df, load_kwargs['query'])
            _debug("Applied query to variable data, result: %d rows", len(data))
    else:
        # _load_embedz_data handles its own data_file+data_part validation
        data = _load_embedz_data(
            data_file, data_part, config, data_format, has_header, load_kwargs
        )

    _debug("Step 6: Expanding global variables (with data access)")
    _expand_global_variables(config, with_vars, data)

    template_has_content = bool(template_part.strip())
    definition_block = bool(config.get('name')) or not template_has_content
    if not data and definition_block:
        _debug("Definition-only block, returning empty output")
        return None, data_file, has_header

    render_data: Union[List[Any], Dict[str, Any]] = data or []

    _debug("Step 7: Rendering template")
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

    # Initialize variables for error handling
    config: Dict[str, Any] = {}
    template_part = 'N/A'
    data_part: Optional[str] = None
    data_file: Optional[str] = None
    has_header = True

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
        ast_elements = pf.convert_text(result, input_format='markdown')

        # Validate the conversion result
        return _validate_convert_result(result, ast_elements)

    except KNOWN_EXCEPTIONS as e:
        # Handle known exceptions with detailed error info
        print_error_info(e, template_part, config, data_file, has_header, data_part)
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

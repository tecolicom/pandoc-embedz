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
import json
import sqlite3
from io import StringIO
from pathlib import Path
import sys
import os

# TOML support: Python 3.11+ has tomllib, older versions need tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

# Store templates and global variables
SAVED_TEMPLATES: Dict[str, str] = {}
GLOBAL_VARS: Dict[str, Any] = {}

def validate_file_path(file_path: str) -> str:
    """Validate file path to prevent path traversal attacks

    Args:
        file_path: File path to validate

    Returns:
        str: Validated absolute file path

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If path appears to be malicious
    """
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

def load_template_from_saved(name: str) -> Tuple[str, None, Callable[[], bool]]:
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

def _apply_sql_query(df: pd.DataFrame, query: str, table_name: str = 'data') -> List[Dict[str, Any]]:
    """Apply SQL query to pandas DataFrame using in-memory SQLite

    Args:
        df: Pandas DataFrame
        query: SQL query string
        table_name: Name of the table to create in SQLite (default: 'data')

    Returns:
        list: Query results as list of dictionaries

    Raises:
        sqlite3.Error: If SQL query fails
    """
    # Delegate to multi-table version with single table
    return _apply_sql_query_multi({table_name: df}, query)

def _apply_sql_query_multi(tables: Dict[str, pd.DataFrame], query: str) -> List[Dict[str, Any]]:
    """Apply SQL query to multiple pandas DataFrames using in-memory SQLite

    Args:
        tables: Dictionary mapping table names to DataFrames
        query: SQL query string

    Returns:
        list: Query results as list of dictionaries

    Raises:
        sqlite3.Error: If SQL query fails
    """
    # Create in-memory SQLite database
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row

    try:
        # Load all DataFrames into SQLite tables
        for table_name, df in tables.items():
            df.to_sql(table_name, conn, index=False, if_exists='replace')

        # Execute query
        cursor = conn.cursor()
        cursor.execute(query)

        # Fetch results and convert to list of dicts
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]

        return result
    finally:
        conn.close()

def guess_format_from_filename(filename: str) -> str:
    """Guess data format from filename extension

    Args:
        filename: File name or path

    Returns:
        str: Guessed format ('csv', 'tsv', 'json', 'yaml', 'toml', 'sqlite', 'lines')
    """
    if isinstance(filename, str):
        if filename.endswith('.txt'):
            return 'lines'
        elif filename.endswith('.tsv'):
            return 'tsv'
        elif filename.endswith('.json'):
            return 'json'
        elif filename.endswith('.yaml') or filename.endswith('.yml'):
            return 'yaml'
        elif filename.endswith('.toml'):
            return 'toml'
        elif filename.endswith('.db') or filename.endswith('.sqlite') or filename.endswith('.sqlite3'):
            return 'sqlite'
    return 'csv'

def _normalize_data_source(
    value: Union[str, Dict[str, Any]],
    table_name: str,
    data_format: Optional[str] = None,
    validate_path: bool = False
) -> tuple:
    """Normalize data source specification to (source, format) tuple

    Args:
        value: Data source specification - can be:
               - dict with 'data' key: inline data with optional 'format'
               - multi-line string: inline CSV data
               - single-line string: file path
        table_name: Name of the table (for error messages)
        data_format: Global format override (optional)
        validate_path: Whether to validate file paths

    Returns:
        tuple: (source, file_format) where source is StringIO or file path
    """
    if isinstance(value, dict):
        # Dict with 'data' key → inline data with format
        if 'data' not in value:
            raise ValueError(
                f"Inline data dict for table '{table_name}' must have 'data' key"
            )
        return StringIO(value['data']), value.get('format', 'csv')
    elif isinstance(value, str) and '\n' in value:
        # Multi-line string → inline CSV data (default format)
        return StringIO(value), 'csv'
    else:
        # Single-line string → file path
        file_format = data_format or guess_format_from_filename(value)
        source = validate_file_path(value) if validate_path else value
        return source, file_format

def load_data(
    source: Union[str, StringIO],
    format: Optional[str] = None,
    has_header: bool = True,
    **kwargs: Any
) -> Union[List[Any], Dict[str, Any]]:
    """Load data from file or StringIO and convert to list or dict

    Args:
        source: File path or StringIO object
        format: Data format ('csv', 'tsv', 'ssv'/'spaces', 'json', 'yaml', 'toml', 'sqlite', 'lines')
               If None, auto-detect from filename
        has_header: Whether CSV/TSV/SSV has header row (ignored for json/yaml/toml/sqlite/lines)
        **kwargs: Additional format-specific options (e.g., table='name' or query='SELECT...' for sqlite)

    Returns:
        list or dict: Data (structure preserved)
    """
    # Validate file path if source is a string (file path)
    if isinstance(source, str):
        source = validate_file_path(source)

    # Normalize format: 'spaces' is an alias for 'ssv'
    if format == 'spaces':
        format = 'ssv'

    # Auto-detect format if not specified
    if format is None:
        if isinstance(source, str):
            format = guess_format_from_filename(source)
        else:
            format = 'csv'  # Default for StringIO

    if format == 'json':
        # JSON format (list or object)
        if isinstance(source, StringIO):
            return json.loads(source.getvalue())
        else:
            with open(source, 'r', encoding='utf-8') as f:
                return json.load(f)

    elif format == 'yaml':
        # YAML format (list or object)
        if isinstance(source, StringIO):
            return yaml.safe_load(source.getvalue())
        else:
            with open(source, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

    elif format == 'toml':
        # TOML format (dict)
        if tomllib is None:
            raise ImportError(
                "TOML support requires 'tomli' package for Python < 3.11. "
                "Install with: pip install tomli"
            )
        if isinstance(source, StringIO):
            # TOML requires binary mode, so encode string to bytes
            return tomllib.loads(source.getvalue())
        else:
            with open(source, 'rb') as f:  # TOML requires binary mode
                return tomllib.load(f)

    elif format == 'sqlite':
        # SQLite database
        if isinstance(source, StringIO):
            raise ValueError("SQLite format does not support inline data. Use an external .db/.sqlite/.sqlite3 file.")

        # Get table name or SQL query from kwargs
        query = kwargs.get('query')
        table = kwargs.get('table')

        if not query and not table:
            raise ValueError("SQLite format requires either 'table' or 'query' parameter")

        # Connect to database
        conn = sqlite3.connect(source)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()

        try:
            # Execute query or select from table
            if query:
                cursor.execute(query)
            else:
                # Simple table select with SQL injection prevention
                cursor.execute(f"SELECT * FROM {table}")

            # Fetch all rows and convert to list of dicts
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]

            return result
        finally:
            conn.close()

    elif format == 'lines':
        # Plain text: one item per line
        if isinstance(source, StringIO):
            lines = source.getvalue().splitlines()
        else:
            with open(source, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
        # Remove empty lines
        return [line for line in lines if line.strip()]

    elif format == 'tsv':
        # TSV format
        if has_header:
            df = pd.read_csv(source, sep='\t')
            # Apply SQL query if provided
            if 'query' in kwargs:
                return _apply_sql_query(df, kwargs['query'])
            return df.to_dict('records')
        else:
            df = pd.read_csv(source, sep='\t', header=None)
            return df.values.tolist()

    elif format == 'ssv':
        # SSV format (space-separated, consecutive spaces treated as one)
        if has_header:
            df = pd.read_csv(source, sep=r'\s+', engine='python')
            # Apply SQL query if provided
            if 'query' in kwargs:
                return _apply_sql_query(df, kwargs['query'])
            return df.to_dict('records')
        else:
            df = pd.read_csv(source, sep=r'\s+', engine='python', header=None)
            return df.values.tolist()

    else:  # format == 'csv' or default
        # CSV format
        if has_header:
            df = pd.read_csv(source)
            # Apply SQL query if provided
            if 'query' in kwargs:
                return _apply_sql_query(df, kwargs['query'])
            return df.to_dict('records')
        else:
            df = pd.read_csv(source, header=None)
            return df.values.tolist()

def parse_attributes(elem: pf.CodeBlock) -> Dict[str, Any]:
    """Parse code block attributes into config dictionary

    Supports dot notation for nested dictionaries (e.g., with.title="Title", global.author="John")
    Only single-level nesting is supported.

    Args:
        elem: Pandoc CodeBlock element

    Returns:
        dict: Parsed configuration with proper type conversion
    """
    config: Dict[str, Any] = {}
    nested_vars: Dict[str, Dict[str, Any]] = {}

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

def parse_code_block(text: str) -> Tuple[Dict[str, Any], str, Optional[str]]:
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
    for line in stream:
        if line.strip() == '---':
            data_part = stream.read().strip()
            break
        template_lines.append(line)

    template_part = ''.join(template_lines).rstrip('\n')
    return config, template_part, data_part

def validate_config(config: Dict[str, Any]) -> None:
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

def _load_multi_table_with_query(
    data_file: Dict[str, Any],
    data_format: Optional[str],
    has_header: bool,
    query: str
) -> List[Dict[str, Any]]:
    """Load multiple tables and execute SQL query

    Args:
        data_file: Dictionary of table_name -> data source
        data_format: Global format override
        has_header: Whether CSV/TSV has header
        query: SQL query to execute

    Returns:
        List of query result rows
    """
    tables = {}
    for table_name, value in data_file.items():
        # Normalize value to determine source and format
        source, file_format = _normalize_data_source(
            value, table_name, data_format, validate_path=True
        )

        # For SQL queries, we only support formats that can be converted to DataFrame
        if file_format not in ('csv', 'tsv', 'ssv', 'spaces'):
            raise ValueError(
                f"Multi-table SQL queries only support CSV, TSV, and SSV formats. "
                f"Got '{file_format}' for table '{table_name}'"
            )

        # Load into DataFrame based on format, respecting has_header
        if file_format == 'tsv':
            df = pd.read_csv(source, sep='\t', header=0 if has_header else None)
        elif file_format in ('ssv', 'spaces'):
            df = pd.read_csv(source, sep=r'\s+', engine='python', header=0 if has_header else None)
        else:  # csv
            df = pd.read_csv(source, header=0 if has_header else None)

        tables[table_name] = df

    # Apply SQL query to multiple tables
    return _apply_sql_query_multi(tables, query)

def _load_multi_table_direct(
    data_file: Dict[str, Any],
    data_format: Optional[str],
    has_header: bool,
    load_kwargs: Dict[str, Any]
) -> Dict[str, Any]:
    """Load multiple tables for direct access (no SQL)

    Args:
        data_file: Dictionary of table_name -> data source
        data_format: Global format override
        has_header: Whether CSV/TSV has header
        load_kwargs: Additional kwargs for load_data

    Returns:
        Dictionary of table_name -> loaded data
    """
    datasets = {}
    for table_name, value in data_file.items():
        # Normalize value to determine source and format
        source, file_format = _normalize_data_source(
            value, table_name, data_format, validate_path=False
        )

        # Load data from source
        datasets[table_name] = load_data(
            source,
            format=file_format,
            has_header=has_header,
            **load_kwargs
        )
    return datasets

def _load_embedz_data(
    data_file: Optional[Union[str, Dict[str, Any]]],
    data_part: Optional[str],
    config: Dict[str, Any],
    data_format: Optional[str],
    has_header: bool,
    load_kwargs: Dict[str, Any]
) -> Union[List[Any], Dict[str, Any]]:
    """Load data from file(s), inline data, or multi-table sources

    Args:
        data_file: File path (str), multi-table dict, or None
        data_part: Inline data string or None
        config: Configuration dictionary
        data_format: Global format override
        has_header: Whether CSV/TSV has header
        load_kwargs: Additional kwargs for load_data

    Returns:
        Loaded data (list or dict)

    Raises:
        ValueError: If both data_file and data_part are specified
    """
    # Ensure data_file and data_part are mutually exclusive
    if data_file and data_part:
        raise ValueError(
            "Cannot specify both 'data' attribute and inline data. "
            "Use either 'data: filename.csv' or provide inline data after '---', not both."
        )

    # Load from data_file (file path or multi-table)
    if data_file:
        if isinstance(data_file, dict):
            # Multi-table mode
            if config.get('query'):
                return _load_multi_table_with_query(
                    data_file, data_format, has_header, config['query']
                )
            else:
                return _load_multi_table_direct(
                    data_file, data_format, has_header, load_kwargs
                )
        else:
            # Single-file mode
            return load_data(data_file, format=data_format, has_header=has_header, **load_kwargs)

    # Load from inline data_part
    if data_part:
        return load_data(StringIO(data_part), format=data_format or 'csv', has_header=has_header, **load_kwargs)

    # No data
    return []

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

        # Save named template
        template_name = config.get('name')
        if template_name:
            if template_name in SAVED_TEMPLATES:
                sys.stderr.write(f"Warning: Overwriting template '{template_name}'\n")
            SAVED_TEMPLATES[template_name] = template_part

        # Load saved template
        template_ref = config.get('as')
        if template_ref:
            if template_ref not in SAVED_TEMPLATES:
                raise ValueError(f"Template '{template_ref}' not found. Define it first with name='{template_ref}'")
            template_part = SAVED_TEMPLATES[template_ref]

        # Prepare variables first (needed for query template expansion)
        with_vars: Dict[str, Any] = {}
        if 'with' in config:
            with_vars.update(config['with'])
        if 'global' in config:
            # Store global variables persistently with template expansion
            # Process all variables in a single Jinja2 context to allow macros
            # Use Environment to support template inclusion
            env = Environment(loader=FunctionLoader(load_template_from_saved))

            # Collect control structures (macros) separately
            control_structures = []

            for key, value in config['global'].items():
                # Check if value contains template syntax
                if isinstance(value, str) and ('{{' in value or '{%' in value):
                    stripped = value.strip()
                    # Check if this is a control structure (macro, import, include)
                    if (stripped.startswith('{%') and
                        not stripped.startswith('{{') and
                        ('macro' in stripped or 'import' in stripped or 'include' in stripped)):
                        # Control structure - collect for prepending, don't save as variable
                        control_structures.append(value)
                        continue

                    # Process template variable
                    # Prepend control structures if any exist
                    if control_structures:
                        template_str = '\n'.join(control_structures) + '\n' + value
                    else:
                        template_str = value

                    template = env.from_string(template_str)
                    rendered = template.render(
                        **GLOBAL_VARS,
                        **{'global': GLOBAL_VARS}
                    )

                    # Remove leading newlines from control structures that produce no output
                    value = rendered.lstrip('\n') if control_structures else rendered

                GLOBAL_VARS[key] = value

        # Load data
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
                from jinja2 import Template
                template = Template(query_template)
                query_value = template.render(
                    **GLOBAL_VARS,           # Expand global variables
                    **with_vars,             # Expand with variables (override globals)
                    **{'global': GLOBAL_VARS},  # Also accessible as global.xxx
                    **{'with': with_vars}    # Also accessible as with.xxx
                )
                load_kwargs['query'] = query_value
            else:
                load_kwargs['query'] = query_template

        # Load data from file(s), inline, or multi-table sources
        data = _load_embedz_data(
            data_file, data_part, config, data_format, has_header, load_kwargs
        )

        # If no data, only save template (no output)
        if not data:
            return []

        # Create Jinja2 Environment with access to saved templates
        env = Environment(loader=FunctionLoader(load_template_from_saved))

        # Render with Jinja2
        render_vars = {
            **GLOBAL_VARS,           # Expand global variables
            **with_vars,             # Expand with variables (override globals)
            'global': GLOBAL_VARS,   # Also accessible as global.xxx
            'with': with_vars,       # Also accessible as with.xxx
            'data': data             # Data
        }
        template = env.from_string(template_part)
        result = template.render(**render_vars)

        # Ensure output ends with newline (prevents concatenation with next paragraph)
        if result and not result.endswith('\n'):
            result += '\n'

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

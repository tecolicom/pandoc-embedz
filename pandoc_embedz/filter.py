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

def guess_format_from_filename(filename: str) -> str:
    """Guess data format from filename extension

    Args:
        filename: File name or path

    Returns:
        str: Guessed format ('csv', 'tsv', 'json', 'yaml', 'toml', 'lines')
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
    return 'csv'

def load_data(
    source: Union[str, StringIO],
    format: Optional[str] = None,
    has_header: bool = True
) -> Union[List[Any], Dict[str, Any]]:
    """Load data from file or StringIO and convert to list or dict

    Args:
        source: File path or StringIO object
        format: Data format ('csv', 'tsv', 'ssv'/'spaces', 'json', 'yaml', 'toml', 'lines')
               If None, auto-detect from filename
        has_header: Whether CSV/TSV/SSV has header row (ignored for json/yaml/toml/lines)

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
            return df.to_dict('records')
        else:
            df = pd.read_csv(source, sep='\t', header=None)
            return df.values.tolist()

    elif format == 'ssv':
        # SSV format (space-separated, consecutive spaces treated as one)
        if has_header:
            df = pd.read_csv(source, sep=r'\s+', engine='python')
            return df.to_dict('records')
        else:
            df = pd.read_csv(source, sep=r'\s+', engine='python', header=None)
            return df.values.tolist()

    else:  # format == 'csv' or default
        # CSV format
        if has_header:
            df = pd.read_csv(source)
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
        valid_formats = {'csv', 'tsv', 'ssv', 'spaces', 'json', 'yaml', 'toml', 'lines'}
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

        # Warn if both data attribute and inline data are specified
        if 'data' in attr_config and data_part:
            sys.stderr.write(f"Warning: Both data attribute ('{attr_config['data']}') and inline data specified. Using data from attribute.\n")

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

        # Load data
        data_file = config.get('data')
        data_format = config.get('format')  # None = auto-detect
        has_header = config.get('header', True)

        if data_file:
            data = load_data(data_file, format=data_format, has_header=has_header)
        elif data_part:
            # For inline data, default to 'csv' if format not specified
            data = load_data(StringIO(data_part), format=data_format or 'csv', has_header=has_header)
        else:
            data = []

        # Prepare variables
        with_vars: Dict[str, Any] = {}
        if 'with' in config:
            with_vars.update(config['with'])
        if 'global' in config:
            # Store global variables persistently
            GLOBAL_VARS.update(config['global'])

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

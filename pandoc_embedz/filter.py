#!/usr/bin/env python3
"""pandoc-embedz: Pandoc filter for embedding data-driven content using Jinja2 templates

This filter allows you to embed data from various formats (CSV, TSV, JSON, YAML, etc.)
into your Markdown documents using Jinja2 template syntax within code blocks.
"""

import panflute as pf
from jinja2 import Environment, FunctionLoader, TemplateNotFound
import pandas as pd
import yaml
import json
from io import StringIO
import sys
import os

# Store templates and global variables
SAVED_TEMPLATES = {}
GLOBAL_VARS = {}

def load_template_from_saved(name):
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

def guess_format_from_filename(filename):
    """Guess data format from filename extension

    Args:
        filename: File name or path

    Returns:
        str: Guessed format ('csv', 'tsv', 'json', 'yaml', 'lines')
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
    return 'csv'

def load_data(source, format=None, has_header=True):
    """Load data from file or StringIO and convert to list or dict

    Args:
        source: File path or StringIO object
        format: Data format ('csv', 'tsv', 'ssv', 'json', 'yaml', 'lines')
               If None, auto-detect from filename
        has_header: Whether CSV/TSV/SSV has header row (ignored for json/yaml/lines)

    Returns:
        list or dict: Data (structure preserved)
    """
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

def parse_code_block(text):
    """Parse code block into YAML config, template, and data sections

    Returns:
        tuple: (config dict, template_part str, data_part str or None)
    """
    if not text.startswith('---'):
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

    template_part = ''.join(template_lines).strip()
    return config, template_part, data_part

def print_error_info(e, template_part, config, data_file, has_header, data_part=None):
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
    sys.stderr.write(f"  Template: {config.get('template', config.get('name', 'inline'))}\n")

    if data_part and len(data_part) < 500:
        sys.stderr.write(f"\nInline data:\n")
        sys.stderr.write(f"{'-'*60}\n")
        sys.stderr.write(f"{data_part}\n")
        sys.stderr.write(f"{'-'*60}\n")

    sys.stderr.write(f"\nFor more information, see the documentation.\n")
    sys.stderr.write(f"{'='*60}\n\n")

def process_embedz(elem, doc):
    """Process code blocks with .embedz class"""
    # Guard: return element unchanged if not an embedz code block
    if not isinstance(elem, pf.CodeBlock):
        return elem
    if 'embedz' not in elem.classes:
        return elem

    text = elem.text.strip()

    try:
        # Parse code block
        config, template_part, data_part = parse_code_block(text)

        # Save named template
        template_name = config.get('name')
        if template_name:
            SAVED_TEMPLATES[template_name] = template_part

        # Load saved template
        template_ref = config.get('template')
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
        local_vars = {}
        if 'local' in config:
            if not isinstance(config['local'], dict):
                raise TypeError("Expected 'local' to be a mapping of variable names to values.")
            local_vars.update(config['local'])
        if 'global' in config:
            if not isinstance(config['global'], dict):
                raise TypeError("Expected 'global' to be a mapping of variable names to values.")
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
            **local_vars,            # Expand local variables (override globals)
            'global': GLOBAL_VARS,   # Also accessible as global.xxx
            'local': local_vars,     # Also accessible as local.xxx
            'data': data             # Data
        }
        template = env.from_string(template_part)
        result = template.render(**render_vars)

        return pf.convert_text(result, input_format='markdown')

    except Exception as e:
        # Print debug info on error
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

def main():
    """Entry point for pandoc filter"""
    pf.run_filter(process_embedz)

if __name__ == '__main__':
    main()

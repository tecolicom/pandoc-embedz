"""Data loading module for pandoc-embedz

Handles loading data from various formats using a dispatch table pattern.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
from functools import partial
import pandas as pd
import yaml
import json
import sqlite3
import sys
from io import StringIO
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    from sqlite_utils import Database as SqliteUtilsDatabase
except ImportError:
    SqliteUtilsDatabase = None

try:
    import openpyxl  # noqa: F401 - imported for availability check
except ImportError:
    openpyxl = None

# ─────────────────────────────────────────────────────────────────────────────
# Constants

FORMAT_EXTENSIONS = {
    '.txt': 'lines',
    '.tsv': 'tsv',
    '.json': 'json',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.db': 'sqlite',
    '.sqlite': 'sqlite',
    '.sqlite3': 'sqlite',
    '.xlsx': 'excel',
    '.xls': 'excel',
}

DEFAULT_FORMAT = 'csv'

# ─────────────────────────────────────────────────────────────────────────────
# SQL Query Support

def _apply_sql_query(df: pd.DataFrame, query: str, table_name: str = 'data') -> List[Dict[str, Any]]:
    """Apply SQL query to DataFrame using in-memory SQLite"""
    return _apply_sql_query_multi({table_name: df}, query)

def _apply_sql_query_multi(tables: Dict[str, pd.DataFrame], query: str) -> List[Dict[str, Any]]:
    """Apply SQL query to multiple DataFrames using in-memory SQLite"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row

    try:
        for table_name, df in tables.items():
            df.to_sql(table_name, conn, index=False, if_exists='replace')

        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────────────────────
# Format Loaders

def _build_csv_read_kwargs(sep: str) -> Dict[str, Any]:
    r"""Build pandas read_csv kwargs for the given separator.

    Args:
        sep: Separator string (e.g., ',', '\t', r'\s+')

    Returns:
        Dict of kwargs for pd.read_csv()
    """
    kwargs: Dict[str, Any] = {'sep': sep}

    if sep == r'\s+':
        kwargs['engine'] = 'python'

    return kwargs

def _read_source(source: Union[str, StringIO]) -> str:
    """Read content from file path or StringIO.

    Args:
        source: File path string or StringIO object

    Returns:
        Content as string
    """
    return source.getvalue() if isinstance(source, StringIO) else Path(source).read_text(encoding='utf-8')

def _load_json(source: Union[str, StringIO], **kwargs) -> Union[List[Any], Dict[str, Any]]:
    """Load JSON format

    Returns empty list for empty input instead of raising an error.
    """
    content = _read_source(source)

    # Handle empty input - return empty list
    if not content.strip():
        return []

    return json.loads(content)

def _load_yaml(source: Union[str, StringIO], **kwargs) -> Union[List[Any], Dict[str, Any]]:
    """Load YAML format"""
    content = _read_source(source)
    return yaml.safe_load(content)

def _load_toml(source: Union[str, StringIO], **kwargs) -> Dict[str, Any]:
    """Load TOML format"""
    if tomllib is None:
        raise ImportError(
            "TOML support requires 'tomli' package for Python < 3.11. "
            "Install with: pip install tomli"
        )
    content = _read_source(source)
    return tomllib.loads(content)

def _quote_identifier(name: str) -> str:
    """Quote SQLite identifier (table/column name) to prevent SQL injection.

    Uses double-quote escaping per SQL standard (supported by SQLite).
    Any double quotes in the name are escaped by doubling them.

    Args:
        name: Identifier name to quote

    Returns:
        str: Safely quoted identifier

    Examples:
        >>> _quote_identifier('items')
        '"items"'
        >>> _quote_identifier('my table')
        '"my table"'
        >>> _quote_identifier('test"quote')
        '"test""quote"'
    """
    return '"' + name.replace('"', '""') + '"'


def _load_sqlite(source: Union[str, StringIO], **kwargs) -> List[Dict[str, Any]]:
    """Load SQLite database

    Uses sqlite-utils if available for improved API, falls back to sqlite3.
    """
    if isinstance(source, StringIO):
        raise ValueError(
            "SQLite format does not support inline data. "
            "Use an external .db/.sqlite/.sqlite3 file."
        )

    query = kwargs.get('query')
    table = kwargs.get('table')

    if not query and not table:
        raise ValueError("SQLite format requires either 'table' or 'query' parameter")

    # Use sqlite-utils if available (cleaner API)
    if SqliteUtilsDatabase is not None:
        db = SqliteUtilsDatabase(source)
        if query:
            # Execute query and convert to dicts using column names
            cursor = db.execute(query)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            return list(db[table].rows)

    # Fallback to standard sqlite3
    conn = sqlite3.connect(source)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()
        if query:
            cursor.execute(query)
        else:
            # Quote table name to prevent SQL injection
            cursor.execute(f"SELECT * FROM {_quote_identifier(table)}")

        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def _clean_column_names(columns: list) -> list:
    """Clean up column names: strip whitespace, replace empty/NaN, deduplicate.

    Follows the same pattern as script/xls2sqlite:
    - Empty or NaN column names are replaced with 'column_N' (0-based index)
    - String column names are stripped of leading/trailing whitespace
    - Duplicate names get a numeric suffix: 'name_1', 'name_2', etc.
    """
    cleaned = []
    seen: Dict[str, int] = {}
    for i, col in enumerate(columns):
        if pd.isna(col):
            col = f'column_{i}'
        elif isinstance(col, str):
            col = col.strip()
            if col == '':
                col = f'column_{i}'
        else:
            col = str(col)

        if col in seen:
            seen[col] += 1
            col = f'{col}_{seen[col]}'
        else:
            seen[col] = 0

        cleaned.append(col)
    return cleaned


def _parse_skip_pattern(pattern: str) -> Tuple[Optional[int], str]:
    """Parse a skiprows pattern string into (column_index, search_text).

    Args:
        pattern: Pattern string - either "text" or "N:text" (N is 1-based)

    Returns:
        Tuple of (column_index, search_text).
        column_index is None for "text" format, or 0-based int for "N:text".
    """
    if ':' in pattern:
        prefix, rest = pattern.split(':', 1)
        try:
            return (int(prefix) - 1, rest)
        except ValueError:
            pass  # Not "N:text" format, use entire string
    return (None, pattern)


def _row_matches_pattern(
    df: pd.DataFrame, row_idx: int, col_index: Optional[int], search_text: str
) -> bool:
    """Check if a row contains a cell exactly matching the given text.

    Args:
        df: DataFrame to search
        row_idx: Row index to check
        col_index: Column index (0-based) to check, or None to check all columns
        search_text: Text to match (exact match via str comparison)

    Returns:
        True if matching cell found, False otherwise.
    """
    cols = [col_index] if col_index is not None else range(len(df.columns))
    for j in cols:
        if j < len(df.columns):
            cell = df.iloc[row_idx, j]
            if pd.notna(cell) and str(cell) == search_text:
                return True
    return False


def _skip_to_matching_row(
    df: pd.DataFrame, pattern: Union[str, List[str]], source: str, table: Optional[str]
) -> pd.DataFrame:
    """Skip rows until finding one matching the pattern(s).

    Args:
        df: DataFrame to search
        pattern: Pattern string, or list of pattern strings (AND logic).
            Each pattern can be "text" or "N:text" (N is 1-based column index).
        source: File path (for error messages)
        table: Sheet name (for error messages), or None

    Returns:
        DataFrame starting from the matching row.

    Raises:
        ValueError: If no matching row is found.
    """
    patterns = pattern if isinstance(pattern, list) else [pattern]
    parsed = [_parse_skip_pattern(p) for p in patterns]
    for i in range(len(df)):
        if all(_row_matches_pattern(df, i, col_idx, text) for col_idx, text in parsed):
            return df.iloc[i:].reset_index(drop=True)

    sheet_info = f" (sheet: {table})" if table else ""
    raise ValueError(
        f"skiprows pattern '{pattern}' not found in "
        f"Excel file '{source}'{sheet_info}"
    )


def _load_excel(
    source: Union[str, StringIO],
    has_header: bool = True,
    **kwargs
) -> Union[List[Dict[str, Any]], List[List[Any]]]:
    """Load Excel file (.xlsx, .xls)

    Requires openpyxl package for .xlsx files.

    Args:
        source: File path to Excel file
        has_header: Whether first row is header
        **kwargs: Options including 'table' (sheet name), 'query' (SQL),
                  'transpose' (swap rows/columns), and 'skiprows' (rows to skip)

    Returns:
        List of dicts (with header) or list of lists (without header)
    """
    if isinstance(source, StringIO):
        raise ValueError(
            "Excel format does not support inline data. "
            "Use an external .xlsx/.xls file."
        )

    if openpyxl is None:
        raise ImportError(
            "Excel support requires 'openpyxl' package. "
            "Install with: pip install openpyxl"
        )

    table = kwargs.get('table')
    sheet_name = table if table is not None else 0

    # Read sheet; skip leading rows if requested
    skiprows = kwargs.get('skiprows')
    read_kwargs: Dict[str, Any] = {'sheet_name': sheet_name, 'header': None}
    if isinstance(skiprows, int):
        read_kwargs['skiprows'] = skiprows
    df = pd.read_excel(source, **read_kwargs)
    if isinstance(skiprows, (str, list)):
        df = _skip_to_matching_row(df, skiprows, source, table)

    # Drop rows and columns where all values are NaN
    df = df.dropna(how='all').dropna(axis=1, how='all')
    df = df.reset_index(drop=True)

    if df.empty:
        sheet_info = f" (sheet: {table})" if table else ""
        sys.stderr.write(
            f"Warning: Excel file '{source}'{sheet_info} contains no data\n"
        )
        return []

    # Transpose if requested (swap rows and columns)
    if kwargs.get('transpose'):
        df = df.T.reset_index(drop=True)
        df.columns = range(len(df.columns))

    # Replace NaN with empty string for template-friendly output
    df = df.astype(object).where(df.notna(), '')

    if has_header:
        # Use first row as header, clean up names
        df.columns = _clean_column_names(df.iloc[0].tolist())
        df = df.iloc[1:].reset_index(drop=True)
        if 'query' in kwargs:
            return _apply_sql_query(df, kwargs['query'])
        return df.to_dict('records')
    else:
        return df.values.tolist()


def _load_lines(source: Union[str, StringIO], **kwargs) -> List[str]:
    """Load plain text lines

    Returns each line as a string. Empty lines are preserved as empty strings.
    """
    content = _read_source(source)
    return content.splitlines()

def _load_ssv_with_columns(
    source: Union[str, StringIO],
    columns: int,
    has_header: bool = True,
    **kwargs
) -> Union[List[Dict[str, Any]], List[List[Any]]]:
    """Load SSV format with fixed column count.

    Uses str.split(maxsplit=columns-1) to preserve spaces in the last column.

    Args:
        source: File path or StringIO object
        columns: Number of columns (last column gets all remaining content)
        has_header: Whether first line is header
        **kwargs: Additional options (e.g., query)

    Returns:
        List of dicts (with header) or list of lists (without header)
    """
    content = _read_source(source)
    lines = content.splitlines()

    if not lines:
        return []

    maxsplit = columns - 1
    result: List[List[str]] = []
    header: Optional[List[str]] = None

    for line in lines:
        if not line.strip():
            continue

        parts = line.split(maxsplit=maxsplit)

        # Pad with empty strings if fewer columns than expected
        while len(parts) < columns:
            parts.append('')

        if has_header and header is None:
            header = parts
        else:
            result.append(parts)

    if has_header and header is not None:
        records = [dict(zip(header, row)) for row in result]
        if 'query' in kwargs:
            df = pd.DataFrame(records)
            return _apply_sql_query(df, kwargs['query'])
        return records
    else:
        return result


def _load_csv(
    source: Union[str, StringIO],
    sep: str = ',',
    has_header: bool = True,
    **kwargs
) -> Union[List[Dict[str, Any]], List[List[Any]]]:
    """Load CSV/TSV/SSV format with optional SQL query support

    Returns empty list for empty input instead of raising an error.
    """
    # For SSV with columns parameter, use special handler
    if sep == r'\s+' and 'columns' in kwargs:
        columns = kwargs['columns']
        rest_kwargs = {k: v for k, v in kwargs.items() if k != 'columns'}
        return _load_ssv_with_columns(source, columns, has_header, **rest_kwargs)

    read_kwargs = _build_csv_read_kwargs(sep)

    try:
        if has_header:
            df = pd.read_csv(source, **read_kwargs)
            if 'query' in kwargs:
                return _apply_sql_query(df, kwargs['query'])
            return df.to_dict('records')
        else:
            df = pd.read_csv(source, header=None, **read_kwargs)
            # Strip trailing NaN values from each row (caused by ragged input)
            result = []
            for row in df.values.tolist():
                while row and (row[-1] is None or
                               (isinstance(row[-1], float) and
                                pd.isna(row[-1]))):
                    row.pop()
                result.append(row)
            return result
    except pd.errors.EmptyDataError:
        # pandas raises EmptyDataError for empty or whitespace-only input
        return []

# ─────────────────────────────────────────────────────────────────────────────
# Loader Dispatch Table

LOADERS = {
    'json': _load_json,
    'yaml': _load_yaml,
    'toml': _load_toml,
    'sqlite': _load_sqlite,
    'excel': _load_excel,
    'lines': _load_lines,
    'tsv': partial(_load_csv, sep='\t'),
    'ssv': partial(_load_csv, sep=r'\s+'),
    'csv': _load_csv,
}

# ─────────────────────────────────────────────────────────────────────────────
# Public API

def guess_format_from_filename(filename: str) -> str:
    """Guess data format from filename extension"""
    return FORMAT_EXTENSIONS.get(Path(filename).suffix.lower(), DEFAULT_FORMAT)

def _normalize_data_source(
    value: Union[str, Dict[str, Any]],
    table_name: str,
    data_format: Optional[str] = None,
) -> Tuple[Union[str, StringIO], str, Dict[str, Any]]:
    """Normalize data source specification to (source, format, load_kwargs) tuple.

    Path validation is not performed here; load_data() handles it via
    validate_file_path().
    """
    if isinstance(value, dict):
        if 'data' in value:
            # Inline data: {data: "...", format: "csv"}
            return StringIO(value['data']), value.get('format', DEFAULT_FORMAT), {}
        elif 'file' in value:
            # File with parameters: {file: "path.xlsx", table: "Sheet1", skiprows: "年"}
            filepath = value['file']
            fmt = value.get('format') or data_format or guess_format_from_filename(filepath)
            extra = {k: v for k, v in value.items() if k not in ('file', 'format')}
            return filepath, fmt, extra
        else:
            raise ValueError(
                f"Inline data dict for table '{table_name}' must have 'data' or 'file' key"
            )
    elif isinstance(value, str) and '\n' in value:
        return StringIO(value), DEFAULT_FORMAT, {}
    else:
        file_format = data_format or guess_format_from_filename(value)
        return value, file_format, {}

def load_data(
    source: Union[str, StringIO],
    format: Optional[str] = None,
    has_header: bool = True,
    **kwargs: Any
) -> Union[List[Any], Dict[str, Any]]:
    """Load data from file or StringIO

    Uses a dispatch table to delegate to format-specific loaders.

    Args:
        source: File path, StringIO object, or '-' for stdin
        format: Data format (csv, tsv, ssv, json, yaml, toml, sqlite, excel, lines)
               If None, auto-detect from filename
        has_header: Whether CSV/TSV/SSV has header row
        **kwargs: Format-specific options (e.g., table/query for sqlite)

    Returns:
        Loaded data (list or dict depending on format)
    """
    from .config import validate_file_path

    # Handle stdin
    if isinstance(source, str) and source == '-':
        source = StringIO(sys.stdin.read())
    elif isinstance(source, str):
        source = validate_file_path(source)

    # Normalize format aliases
    if format == 'spaces':
        format = 'ssv'

    # Auto-detect format
    if format is None:
        format = guess_format_from_filename(source) if isinstance(source, str) else DEFAULT_FORMAT

    # Dispatch to appropriate loader
    loader = LOADERS.get(format, LOADERS[DEFAULT_FORMAT])
    return loader(source, has_header=has_header, **kwargs)

# ─────────────────────────────────────────────────────────────────────────────
# Multi-table Support

def _is_resolved_data(value: Any) -> bool:
    """Check if value is already resolved variable data (not inline data spec)."""
    if isinstance(value, list):
        return True
    # Inline data dicts have 'data' key; file dicts have 'file' key
    return isinstance(value, dict) and 'data' not in value and 'format' not in value and 'file' not in value


def _to_dataframe(value: Any) -> pd.DataFrame:
    """Convert loaded data to DataFrame for SQL queries."""
    if isinstance(value, list):
        return pd.DataFrame(value)
    if isinstance(value, dict):
        return pd.DataFrame(list(value.values()))
    return pd.DataFrame()


def _query_tables(
    data_file: Dict[str, Any],
    data_format: Optional[str],
    has_header: bool,
    query: str
) -> List[Dict[str, Any]]:
    """Load multiple tables and execute SQL query"""
    datasets = _load_tables(data_file, data_format, has_header, {})
    tables = {name: _to_dataframe(data) for name, data in datasets.items()}
    return _apply_sql_query_multi(tables, query)

def _load_tables(
    data_file: Dict[str, Any],
    data_format: Optional[str],
    has_header: bool,
    load_kwargs: Dict[str, Any]
) -> Dict[str, Any]:
    """Load multiple tables for direct access"""
    datasets = {}
    for table_name, value in data_file.items():
        if _is_resolved_data(value):
            datasets[table_name] = value
            continue
        source, file_format, extra_kwargs = _normalize_data_source(
            value, table_name, data_format
        )
        merged_kwargs = {**load_kwargs, **extra_kwargs}
        datasets[table_name] = load_data(
            source,
            format=file_format,
            has_header=has_header,
            **merged_kwargs
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
    """Load data from file(s), inline data, or multi-table sources"""
    if data_file and data_part:
        raise ValueError(
            "Cannot specify both 'data' attribute and inline data. "
            "Use either 'data: filename.csv' or provide inline data after '---', not both."
        )

    if data_file:
        if isinstance(data_file, dict):
            if config.get('query'):
                return _query_tables(data_file, data_format, has_header, config['query'])
            else:
                return _load_tables(data_file, data_format, has_header, load_kwargs)
        else:
            return load_data(data_file, format=data_format, has_header=has_header, **load_kwargs)

    if data_part:
        return load_data(StringIO(data_part), format=data_format or DEFAULT_FORMAT, has_header=has_header, **load_kwargs)

    return []

# Jinja2 Macro Examples

This document demonstrates how to use Jinja2 macros in pandoc-embedz for creating parameterized, reusable template functions.

## What are Macros?

Macros are like functions in programming - they accept parameters and return formatted output. They're more powerful than `{% include %}` because you can pass different values each time you call them.

## Basic Macros

Define simple formatting macros:

```embedz
---
name: basic-formatters
---
{% macro bold(text) -%}
**{{ text }}**
{%- endmacro %}

{% macro italic(text) -%}
*{{ text }}*
{%- endmacro %}

{% macro code(text) -%}
`{{ text }}`
{%- endmacro %}
```

Use them with different parameters:

```embedz
---
format: json
---
{% from 'basic-formatters' import bold, italic, code %}

## Formatting Examples

{% for item in data %}
- {{ bold(item.name) }}: {{ italic(item.description) }} - {{ code(item.command) }}
{% endfor %}
---
[
  {"name": "Install", "description": "Install the package", "command": "pip install pandoc-embedz"},
  {"name": "Run", "description": "Execute the filter", "command": "pandoc --filter pandoc-embedz"},
  {"name": "Test", "description": "Run tests", "command": "pytest"}
]
```

## Conditional Macros

Create macros with conditional logic:

```embedz
---
name: status-macros
---
{% macro severity_badge(level) -%}
{% if level == "high" or level == "critical" %}🔴 Critical
{%- elif level == "medium" %}🟡 Medium
{%- elif level == "low" %}🟢 Low
{%- else %}⚪ Unknown
{%- endif %}
{%- endmacro %}

{% macro status_icon(status) -%}
{% if status == "resolved" %}✅
{%- elif status == "investigating" %}🔍
{%- elif status == "pending" %}⏳
{%- else %}❓
{%- endif %}
{%- endmacro %}
```

Use them together:

```embedz
---
format: json
---
{% from 'status-macros' import severity_badge, status_icon %}

## Security Issues

| Status | Severity | Title |
|:------:|:---------|:------|
{% for issue in data -%}
| {{ status_icon(issue.status) }} | {{ severity_badge(issue.severity) }} | {{ issue.title }} |
{% endfor %}
---
[
  {"title": "SQL Injection vulnerability", "severity": "critical", "status": "resolved"},
  {"title": "XSS in user input", "severity": "high", "status": "investigating"},
  {"title": "Missing CSRF token", "severity": "medium", "status": "pending"},
  {"title": "Information disclosure", "severity": "low", "status": "resolved"}
]
```

## Multi-Parameter Macros

Macros can accept multiple parameters with default values:

```embedz
---
name: advanced-formatters
---
{% macro format_date(date, prefix="Date: ") -%}
{{ prefix }}{{ date }}
{%- endmacro %}

{% macro link(url, text="", title="") -%}
{% if text %}[{{ text }}]({{ url }}{% if title %} "{{ title }}"{% endif %})
{%- else %}[{{ url }}]({{ url }})
{%- endif %}
{%- endmacro %}

{% macro badge(text, color="blue") -%}
![{{ text }}](https://img.shields.io/badge/{{ text }}-{{ color }})
{%- endmacro %}
```

Use with different parameter combinations:

```embedz
---
format: json
---
{% from 'advanced-formatters' import format_date, link, badge %}

## Project Links

{% for project in data %}
### {{ project.name }} {{ badge(project.status) }}

{{ format_date(project.date, "Released: ") }}

{{ link(project.url, project.name, "Visit project homepage") }}

{% endfor %}
---
[
  {"name": "Project Alpha", "date": "2024-01-15", "url": "https://example.com/alpha", "status": "stable"},
  {"name": "Project Beta", "date": "2024-02-20", "url": "https://example.com/beta", "status": "beta"}
]
```

## Nested Macro Calls

Macros can call other macros:

```embedz
---
name: composite-macros
---
{% macro format_priority(priority) -%}
{% if priority == 1 %}⚡ Urgent
{%- elif priority == 2 %}🔥 High
{%- elif priority == 3 %}📌 Normal
{%- else %}📋 Low
{%- endif %}
{%- endmacro %}

{% macro format_task(title, priority, assignee) -%}
- {{ format_priority(priority) }} **{{ title }}** (assigned to: {{ assignee }})
{%- endmacro %}
```

Use the composite macro:

```embedz
---
format: json
---
{% from 'composite-macros' import format_task %}

## Task List

{% for task in data %}
{{ format_task(task.title, task.priority, task.assignee) }}
{% endfor %}
---
[
  {"title": "Fix critical bug", "priority": 1, "assignee": "Alice"},
  {"title": "Implement new feature", "priority": 2, "assignee": "Bob"},
  {"title": "Update documentation", "priority": 3, "assignee": "Charlie"},
  {"title": "Refactor old code", "priority": 4, "assignee": "David"}
]
```

## Macro vs Include Comparison

### Using Include (simpler, but less flexible)

```embedz
---
name: simple-item
---
- {{ item.name }}: {{ item.value }}
```

```embedz
---
format: json
---
{% for item in data %}
{% include 'simple-item' with context %}
{% endfor %}
---
[{"name": "A", "value": 1}, {"name": "B", "value": 2}]
```

### Using Macro (more flexible with parameters)

```embedz
---
name: macro-item
---
{% macro format_item(name, value, prefix="Item ") -%}
- {{ prefix }}{{ name }}: {{ value }}
{%- endmacro %}
```

```embedz
---
format: json
---
{% from 'macro-item' import format_item %}
{% for item in data %}
{{ format_item(item.name, item.value, "Entry ") }}
{% endfor %}
---
[{"name": "A", "value": 1}, {"name": "B", "value": 2}]
```

## When to Use Macros

**Use Macros when**:
- You need to pass different parameters each time
- You want default parameter values
- You need to call from multiple places with different arguments
- Logic is self-contained and reusable

**Use Include when**:
- You just need to reuse a template fragment
- All data comes from the current context
- Simplicity is preferred over flexibility

## Converting with Pandoc

```bash
pandoc macros.md --filter pandoc-embedz -o macros.pdf
pandoc macros.md --filter pandoc-embedz -o macros.html
```

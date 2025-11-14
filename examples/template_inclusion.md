# Template Inclusion Examples

This document demonstrates the template inclusion feature, which allows you to nest templates within other templates for more modular content generation.

## Basic Example

First, define some reusable format templates:

```embedz
---
name: date-format
---
{{ item.date }}
```

```embedz
---
name: title-format
---
**{{ item.title }}**
```

Now combine them to create formatted entries:

```embedz
---
format: json
---
## Incident Report
{% for item in data %}
- {% include 'date-format' with context %} - {% include 'title-format' with context %}
{% endfor %}
---
[
  {"date": "2024-01-15", "title": "Apache HTTP Server vulnerability"},
  {"date": "2024-01-20", "title": "OpenSSL certificate validation issue"},
  {"date": "2024-02-03", "title": "WordPress plugin XSS vulnerability"}
]
```

## Conditional Templates

Define a template that uses conditionals:

```embedz
---
name: severity-badge
---
{% if item.severity == "high" %}🔴 High{% elif item.severity == "medium" %}🟡 Medium{% else %}🟢 Low{% endif %}
```

Use it to show severity levels:

```embedz
---
format: json
---
### Vulnerability List
{% for item in data %}
- {% include 'severity-badge' with context %} - {{ item.title }}
{% endfor %}
---
[
  {"title": "Critical memory corruption", "severity": "high"},
  {"title": "Information disclosure", "severity": "medium"},
  {"title": "Minor configuration error", "severity": "low"}
]
```

## Nested Template Composition

Create multiple levels of template composition:

```embedz
---
name: status-icon
---
{% if item.status == "resolved" %}✅{% elif item.status == "investigating" %}🔍{% else %}⏳{% endif %}
```

```embedz
---
name: incident-entry
---
{% include 'status-icon' with context %} {{ item.date }} - {{ item.title }}
```

Use the composite template:

```embedz
---
format: json
---
## Incident Tracking
{% for item in data %}
- {% include 'incident-entry' with context %}
{% endfor %}
---
[
  {"date": "2024-01-10", "title": "Database performance issue", "status": "resolved"},
  {"date": "2024-01-15", "title": "API rate limiting", "status": "investigating"},
  {"date": "2024-01-20", "title": "Email delivery delay", "status": "pending"}
]
```

## Table Formatting

Define a template for table rows:

```embedz
---
name: table-row
---
{{ "| " }}{{ item.name }}{{ " | " }}{{ item.count }}{{ " | " }}{{ item.percentage }}{{ "% |" }}
```

Generate a table:

```embedz
---
format: json
---
| Category | Count | Percentage |
|:---------|------:|-----------:|
{% for item in data -%}
{% include 'table-row' with context %}
{% endfor -%}
---
[
  {"name": "Web Applications", "count": 45, "percentage": 35},
  {"name": "Network Services", "count": 32, "percentage": 25},
  {"name": "Operating Systems", "count": 28, "percentage": 22},
  {"name": "IoT Devices", "count": 23, "percentage": 18}
]
```

## Converting with Pandoc

To convert this document:

```bash
pandoc template_inclusion.md --filter pandoc-embedz -o template_inclusion.pdf
```

Or to HTML:

```bash
pandoc template_inclusion.md --filter pandoc-embedz -o template_inclusion.html
```

# Sample Document

## CSV Example

​```embedz
---
data: sample_data.csv
---
| Name | Value |
|:-----|------:|
{% for row in data %}
| {{ row.name }} | {{ row.value }} |
{% endfor %}
​```

## Inline JSON Example

​```embedz
---
format: json
---
### Products

{% for product in data %}
- **{{ product.name }}**: ${{ product.price }}
  {% if product.tags %}
  - Tags: {{ product.tags | join(', ') }}
  {% endif %}
{% endfor %}
---
[
  {"name": "Apple", "price": 1.50, "tags": ["fruit", "fresh"]},
  {"name": "Banana", "price": 0.80, "tags": ["fruit"]},
  {"name": "Carrot", "price": 1.20, "tags": ["vegetable", "fresh"]}
]
​```

## Conditional Example

​```embedz
---
data: sample_data.csv
local:
  threshold: 50
---
### High Values (> {{ threshold }})

{% for row in data %}
{% if row.value > threshold %}
- {{ row.name }}: {{ row.value }}
{% endif %}
{% endfor %}
​```

# JVN共有テンプレートの実装

## 要件

- リスト部分を共有したい
- トップレベル（インデントなし）でも使える
- ネストレベル（インデント付き）でも使える
- 件数も自動計算したい

## 方法1: include + indent変数（シンプル）

### テンプレート定義

```embedz
---
name: jvn-item
---
{{ indent }}- {{ item.date | replace('/', '-') }} {{ item.id }}:

{{ indent }}  {{ item.title }}

```

```embedz
---
name: jvn-list
---
{% for item in data -%}
{% include 'jvn-item' with context %}
{% endfor -%}
```

```embedz
---
name: jvn-section
---
#### {{ title }}（{{ data | length }}件） ^[<{{ url }}>]

{% include 'jvn-list' with context %}
```

### 使用例1: トップレベル（インデントなし）

```embedz
---
template: jvn-section
local:
  title: "JVN-JP"
  url: "https://jvn.jp/jp/"
  indent: ""
---
---
date,id,title
2024/01/15,JVNDB-001,Apache HTTP Server の脆弱性
2024/01/20,JVNDB-002,OpenSSL における問題
```

### 使用例2: ネストレベル（インデント2スペース）

```embedz
---
template: jvn-section
local:
  title: "JVN-VU"
  url: "https://jvn.jp/vu/"
  indent: "  "
---
---
date,id,title
2024/02/01,JVNVU#001,製品Aの脆弱性
2024/02/05,JVNVU#002,製品Bの問題
```

### 使用例3: リストだけを使う（見出しなし）

別の場所でリスト部分だけ使いたい場合：

```embedz
---
template: jvn-list
local:
  indent: "    "
---
---
date,id,title
2024/03/01,JVNTA#001,重要な告知
```

## 方法2: マクロ（より柔軟）

### マクロ定義

```embedz
---
name: jvn-macros
---
{% macro item(row, indent=0) -%}
{{ '  ' * indent }}- {{ row.date | replace('/', '-') }} {{ row.id }}:

{{ '  ' * indent }}  {{ row.title }}

{%- endmacro %}

{% macro list(data, indent=0) -%}
{% for row in data -%}
{{ item(row, indent) }}
{%- endfor %}
{%- endmacro %}

{% macro section(title, url, data, indent=0) -%}
#### {{ title }}（{{ data | length }}件） ^[<{{ url }}>]

{{ list(data, indent) }}
{%- endmacro %}
```

### 使用例1: マクロでトップレベル

```embedz
---
format: csv
---
{% from 'jvn-macros' import section %}
{{ section("JVN-JP", "https://jvn.jp/jp/", data, 0) }}
---
date,id,title
2024/01/15,JVNDB-101,WordPress の XSS
2024/01/20,JVNDB-102,PHP の脆弱性
```

### 使用例2: マクロでネストレベル

```embedz
---
format: csv
---
{% from 'jvn-macros' import section %}
{{ section("JVN-VU", "https://jvn.jp/vu/", data, 1) }}
---
date,id,title
2024/02/01,JVNVU#201,Cisco製品の問題
```

### 使用例3: リストだけ使う

```embedz
---
format: csv
---
{% from 'jvn-macros' import list %}
重要な更新:

{{ list(data, 2) }}
---
date,id,title
2024/03/01,JVNTA#301,緊急アップデート
```

## 比較

| 方法 | メリット | デメリット |
|:-----|:---------|:-----------|
| include + indent変数 | シンプル | indent を文字列で指定する必要 |
| マクロ | 柔軟、level を数値指定 | やや複雑 |

## 推奨

**方法1（include）を推奨**：
- indent を `""`, `"  "`, `"    "` と指定するだけ
- テンプレートの再利用が明確
- 理解しやすい

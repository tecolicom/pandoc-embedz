# JVN用途の実装例

## 現在の実装で可能な方法

### テンプレート定義（1回だけ）

```embedz
---
name: jvn-section
---
#### {{ title }}（{{ data | length }}件） ^[<{{ url }}>]

{% for row in data %}
- {{ row.date | replace('/', '-') }} {{ row.id }}:

  {{ row.title }}

{% endfor %}
```

### 使用例1: JVN-JP

```embedz
---
template: jvn-section
local:
  title: "JVN-JP"
  url: "https://jvn.jp/jp/"
---
---
date,id,title
2024/01/15,JVNDB-2024-001234,Apache HTTP Server の脆弱性
2024/01/20,JVNDB-2024-001235,OpenSSL における問題
2024/01/22,JVNDB-2024-001236,WordPress プラグインの XSS
```

### 使用例2: JVN-VU

```embedz
---
template: jvn-section
local:
  title: "JVN-VU"
  url: "https://jvn.jp/vu/"
---
---
date,id,title
2024/02/01,JVNVU#98765432,製品Aの脆弱性
2024/02/05,JVNVU#98765433,製品Bのバッファオーバーフロー
```

## メリット

1. **件数が自動計算**: `{{ data | length }}` で自動
2. **再利用可能**: 同じテンプレートを複数箇所で使える
3. **変更が容易**: テンプレート1箇所変更すれば全体に反映
4. **タイトルとURLを動的に指定**: `local` 変数で

## 元の書き方との比較

### Before（手動で件数を書く）

```markdown
#### JVN-JP（135件） ^[<https://jvn.jp/jp/>]

​```embedz
---
data: 03/data/jvn-jp.csv
---
{% for row in data %}
- {{ row.date | replace('/', '-') }} {{ row.id }}:
  {{ row.title }}
{% endfor %}
​```
```

問題点：
- 件数（135件）を手動で更新する必要がある
- 見出しとデータが別々で、テンプレート化できない

### After（自動計算）

```markdown
​```embedz
---
template: jvn-section
local:
  title: "JVN-JP"
  url: "https://jvn.jp/jp/"
---
---
（CSVデータ、または data: 03/data/jvn-jp.csv）
​```
```

メリット：
- ✅ 件数が自動計算される
- ✅ 1つのブロックで完結
- ✅ 再利用可能

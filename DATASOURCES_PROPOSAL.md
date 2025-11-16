# Pandoc Data Sources - 設計提案

## 背景

### 課題

ドキュメント作成時に外部データベースや参照情報を利用したいケースがある：

- **JVN脆弱性情報**: `JVNDB-2024-001234` → タイトル、深刻度、詳細
- **CVE情報**: `CVE-2024-12345` → 脆弱性詳細
- **RFC**: `RFC 8446` → タイトル、要約
- **DOI**: 学術論文の引用情報
- その他、任意のデータベース/API

### 現状の問題

- 毎回手動でコピペ
- 情報が古くなる
- メンテナンスコストが高い

### 理想

```markdown
## 脆弱性詳細

```embedz
---
data: jvn:JVNDB-2024-001234
---
- タイトル: {{ data.title }}
- 深刻度: {{ data.severity }}
- 詳細: {{ data.description }}
```
```

番号を指定するだけで最新情報を自動取得。

## 提案: 汎用データソースライブラリ

### コンセプト

**`pandoc-datasources`** - Pandoc エコシステム向けの汎用データ取得ライブラリ

- 様々なデータソースへの統一アクセス
- プラグイン可能なアーキテクチャ
- キャッシュ機能
- `pandoc-embedz` だけでなく、他のツールからも利用可能

### アーキテクチャ

```
pandoc-datasources (汎用ライブラリ)
├── Core
│   ├── Cache (ファイルベースキャッシュ)
│   ├── Config (設定管理)
│   └── DataSource (抽象基底クラス)
├── Plugins
│   ├── FileSource (ローカルファイル: CSV, JSON, etc.)
│   ├── HTTPSource (汎用HTTP/API)
│   ├── JVNSource (JVN脆弱性DB)
│   ├── CVESource (CVE/NVD)
│   ├── RFCSource (RFC データベース)
│   └── SQLiteSource (SQLite DB)
└── API (統一インターフェース)

pandoc-embedz
└── uses pandoc-datasources

その他のフィルタ/ツール
└── uses pandoc-datasources
```

## 設計詳細

### 統一インターフェース

```python
from pandoc_datasources import DataSource

# データソースの取得
ds = DataSource.get('jvn')
data = ds.fetch('JVNDB-2024-001234')
# → {'title': '...', 'severity': '...', ...}

# または URI スタイル
data = DataSource.fetch('jvn:JVNDB-2024-001234')
```

### 設定ファイル

```yaml
# .pandoc-datasources.yml (プロジェクトルート)
cache_dir: .cache/datasources/
default_timeout: 30

sources:
  jvn:
    type: api
    base_url: https://jvndb.jvn.jp/apis/
    cache_ttl: 86400  # 24時間
    format: json

  cve:
    type: api
    base_url: https://services.nvd.nist.gov/rest/json/cves/2.0
    cache_ttl: 86400
    api_key_env: NVD_API_KEY  # 環境変数から取得

  rfc:
    type: api
    base_url: https://www.rfc-editor.org/rfc/
    cache_ttl: 604800  # 7日間

  mydb:
    type: sqlite
    path: ./references.sqlite
    default_table: items
```

### プラグインインターフェース

```python
from pandoc_datasources.plugin import DataSourcePlugin

class JVNDataSource(DataSourcePlugin):
    """JVN脆弱性情報データソース"""

    def fetch(self, identifier: str) -> dict:
        """
        JVN IDから脆弱性情報を取得

        Args:
            identifier: JVNDB-YYYY-NNNNNN 形式のID

        Returns:
            正規化された脆弱性情報
        """
        # キャッシュチェック
        cached = self.cache.get(identifier)
        if cached:
            return cached

        # API呼び出し
        url = f"{self.config['base_url']}/getVulnDetailV3"
        response = requests.get(url, params={'vulnId': identifier})

        # パース・正規化
        data = self.parse_response(response.json())

        # キャッシュ保存
        self.cache.set(identifier, data, ttl=self.config['cache_ttl'])

        return data

    def parse_response(self, raw_data: dict) -> dict:
        """APIレスポンスを正規化"""
        return {
            'title': raw_data['vulninfo']['title'],
            'severity': raw_data['vulninfo']['severity'],
            'description': raw_data['vulninfo']['description'],
            'published': raw_data['vulninfo']['publishedDate'],
            # ...
        }
```

### pandoc-embedz からの利用

```yaml
# 方法1: URI スキーム
data: jvn:JVNDB-2024-001234
---
{{ data.title }}

# 方法2: 明示的な設定
data:
  source: jvn
  id: JVNDB-2024-001234
---
{{ data.title }}

# 方法3: 複数のデータソース
data:
  items:
    - source: jvn:JVNDB-2024-001234
    - source: cve:CVE-2024-12345
---
{% for item in data.items %}
- {{ item.title }}
{% endfor %}
```

## 実装フェーズ

### Phase 1: Core Infrastructure
- [ ] キャッシュ機構
- [ ] 設定管理（YAML/TOML）
- [ ] 基本的なDataSourceインターフェース
- [ ] エラーハンドリング
- [ ] ロギング

### Phase 2: Basic Plugins
- [ ] FileSource (既存のCSV/JSON等をラップ)
- [ ] HTTPSource (汎用HTTP/REST API)
- [ ] SQLiteSource

### Phase 3: Specialized Plugins
- [ ] JVNSource
- [ ] CVESource (NVD API)
- [ ] RFCSource
- [ ] DOISource

### Phase 4: Integration
- [ ] pandoc-embedz への統合
- [ ] CLIツール (`pandoc-datasources fetch jvn:...`)
- [ ] ドキュメント整備
- [ ] テスト

## 利点

### 1. 分離された責務
- **pandoc-datasources**: データ取得・キャッシュ
- **pandoc-embedz**: テンプレート処理
- 各コンポーネントが独立して進化可能

### 2. 再利用性
- 他のPandocフィルタから利用可能
- Pythonスクリプトから直接利用可能
- 共通のキャッシュを共有

### 3. 拡張性
- プラグインで新しいデータソース追加
- 設定ファイルでカスタマイズ
- 既存コードに影響なし

### 4. メンテナンス性
- データ取得ロジックが一箇所に集約
- キャッシュの一元管理
- テストが容易

## 技術スタック

- **Python 3.8+** (型ヒントを活用)
- **requests** (HTTP/API アクセス)
- **diskcache** or **shelve** (ファイルベースキャッシュ)
- **pyyaml** (設定ファイル)
- **pytest** (テスト)

## ファイル構成例

```
pandoc-datasources/
├── pyproject.toml
├── README.md
├── src/
│   └── pandoc_datasources/
│       ├── __init__.py
│       ├── core/
│       │   ├── cache.py
│       │   ├── config.py
│       │   └── datasource.py
│       ├── plugins/
│       │   ├── __init__.py
│       │   ├── file.py
│       │   ├── http.py
│       │   ├── jvn.py
│       │   ├── cve.py
│       │   └── sqlite.py
│       └── cli.py
├── tests/
└── examples/
    └── .pandoc-datasources.yml
```

## 将来的な拡張

- **認証サポート**: OAuth, API keys
- **レート制限**: API呼び出しの制御
- **バッチ取得**: 複数IDの効率的な取得
- **変換パイプライン**: データの前処理・変換
- **非同期サポート**: 大量データの並列取得
- **GUIツール**: キャッシュ管理、設定エディタ

## 関連プロジェクト

- **pandoc-citeproc**: 文献管理（類似のコンセプト）
- **requests-cache**: HTTPキャッシュライブラリ
- **dataset**: Pythonのデータベース抽象化

## 次のステップ

1. コミュニティからのフィードバック収集
2. 簡単なプロトタイプ実装
3. JVNプラグインでの実証
4. pandoc-embedzへの統合検証
5. 正式リリース

---

**作成日**: 2025-11-16
**ステータス**: 提案段階
**関連**: pandoc-embedz

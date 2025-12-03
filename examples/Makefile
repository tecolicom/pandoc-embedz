# pandoc-embedz examples Makefile
#
# 使い方:
#   make           - すべての例を Markdown として出力
#   make html      - すべての例を HTML に変換
#   make pdf       - すべての例を PDF に変換
#   make clean     - 生成されたファイルを削除
#   make simple    - simple.md のみを Markdown として出力
#   make simple.html - simple.md を HTML に変換

SOURCES = simple.md macros.md template_inclusion.md indent_control.md
FILTER = pandoc-embedz

# 出力ディレクトリ
OUTPUT_DIR = output

# Pandoc オプション
PANDOC_OPTS = --filter $(FILTER)
PDF_OPTS = $(PANDOC_OPTS) -V documentclass=ltjarticle --pdf-engine=lualatex
HTML_OPTS = $(PANDOC_OPTS) --standalone --metadata title="pandoc-embedz example"

# ターゲット
MARKDOWN_TARGETS = $(SOURCES:.md=.markdown)
HTML_TARGETS = $(SOURCES:.md=.html)
PDF_TARGETS = $(SOURCES:.md=.pdf)

.PHONY: all html pdf clean markdown check $(SOURCES:.md=)

# デフォルト: Markdown として出力を確認
all: markdown

# 各例を個別に実行
$(SOURCES:.md=): %: %.md
	@echo "=== $< ==="
	@pandoc $< $(PANDOC_OPTS) -t markdown
	@echo ""

# Markdown として出力（確認用）
markdown: $(SOURCES)
	@for f in $(SOURCES); do \
		echo "=== $$f ==="; \
		pandoc $$f $(PANDOC_OPTS) -t markdown; \
		echo ""; \
	done

# HTML に変換
html: $(OUTPUT_DIR) $(addprefix $(OUTPUT_DIR)/,$(HTML_TARGETS))

$(OUTPUT_DIR)/%.html: %.md
	pandoc $< $(HTML_OPTS) -o $@
	@echo "Created $@"

# PDF に変換（日本語対応には LuaLaTeX が必要）
pdf: $(OUTPUT_DIR) $(addprefix $(OUTPUT_DIR)/,$(PDF_TARGETS))

$(OUTPUT_DIR)/%.pdf: %.md
	pandoc $< $(PDF_OPTS) -o $@
	@echo "Created $@"

# 出力ディレクトリを作成
$(OUTPUT_DIR):
	mkdir -p $(OUTPUT_DIR)

# フィルターが動作するか確認
check:
	@echo "Checking pandoc-embedz filter..."
	@which $(FILTER) > /dev/null 2>&1 || (echo "Error: $(FILTER) not found"; exit 1)
	@echo "pandoc-embedz is available at: $$(which $(FILTER))"
	@echo ""
	@echo "Running simple test..."
	@echo '```embedz' > /tmp/test.md
	@echo '---' >> /tmp/test.md
	@echo 'format: json' >> /tmp/test.md
	@echo '---' >> /tmp/test.md
	@echo '{% for item in data %}- {{ item.name }}' >> /tmp/test.md
	@echo '{% endfor %}' >> /tmp/test.md
	@echo '---' >> /tmp/test.md
	@echo '[{"name": "Test"}]' >> /tmp/test.md
	@echo '```' >> /tmp/test.md
	@pandoc /tmp/test.md $(PANDOC_OPTS) -t markdown
	@rm /tmp/test.md
	@echo ""
	@echo "Filter is working correctly!"

# 生成されたファイルを削除
clean:
	rm -rf $(OUTPUT_DIR)
	@echo "Cleaned output directory"

# ヘルプ
help:
	@echo "pandoc-embedz examples Makefile"
	@echo ""
	@echo "ターゲット:"
	@echo "  all (default) - すべての例を Markdown として出力"
	@echo "  html          - すべての例を HTML に変換 (output/ に保存)"
	@echo "  pdf           - すべての例を PDF に変換 (output/ に保存)"
	@echo "  clean         - 生成されたファイルを削除"
	@echo "  check         - フィルターが動作するか確認"
	@echo ""
	@echo "個別の例を実行:"
	@echo "  make simple           - simple.md を Markdown として出力"
	@echo "  make macros           - macros.md を Markdown として出力"
	@echo "  make template_inclusion"
	@echo "  make indent_control"
	@echo ""
	@echo "ソースファイル:"
	@for f in $(SOURCES); do echo "  $$f"; done

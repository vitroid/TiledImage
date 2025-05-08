# 変数定義
PKGNAME = tiledimage
PYTHON = python3
POETRY = poetry

# デフォルトターゲット
.PHONY: all
all: build

# テスト関連
.PHONY: test test-deploy test-install
test:
	$(PYTHON) 2pngs.py sample.png sample.pngs 39
	$(PYTHON) pngs2.py sample.pngs sample.jpg

test-deploy:
	$(POETRY) publish --build -r testpypi

test-install:
	pip install --index-url https://test.pypi.org/simple/ $(PKGNAME)

# インストール関連
.PHONY: uninstall
uninstall:
	-pip uninstall -y $(PKGNAME)

# ビルド関連
.PHONY: build deploy check
build: README.md
	$(POETRY) build

deploy: clean
	$(POETRY) publish --build

check:
	$(POETRY) check

# クリーンアップ
.PHONY: clean distclean
clean:
	-rm -rf build dist
	-rm -rf *.egg-info
	-rm -rf __pycache__
	-rm -rf .pytest_cache
	-rm -rf .coverage
	-rm -rf htmlcov

distclean: clean
	-rm -rf .venv
	-rm -rf .poetry
	-rm -f poetry.lock

# ヘルプ
.PHONY: help
help:
	@echo "利用可能なターゲット:"
	@echo "  all          - デフォルトターゲット（buildと同じ）"
	@echo "  test         - テストの実行"
	@echo "  test-deploy  - TestPyPIへのデプロイ"
	@echo "  test-install - TestPyPIからのインストール"
	@echo "  uninstall    - パッケージのアンインストール"
	@echo "  build        - パッケージのビルド"
	@echo "  deploy       - PyPIへのデプロイ"
	@echo "  check        - パッケージのチェック"
	@echo "  clean        - ビルドファイルの削除"
	@echo "  distclean    - すべての生成ファイルの削除"
	@echo "  help         - このヘルプメッセージの表示"

.PHONY: check test-api test-mcp lint-api lint-mcp web-typecheck web-build ingest-validate ingest-import ingest-rebuild

API_DIR := apps/api
MCP_DIR := apps/mcp_servers/course_search
WEB_DIR := apps/web

check: test-api test-mcp web-typecheck

test-api:
	PYTHONPATH=$(API_DIR) python3 -m pytest $(API_DIR)/tests

test-mcp:
	PYTHONPATH=$(MCP_DIR) python3 -m pytest $(MCP_DIR)/tests

lint-api:
	cd $(API_DIR) && python3 -m ruff check app tests && python3 -m mypy app tests

lint-mcp:
	cd $(MCP_DIR) && python3 -m ruff check . && python3 -m mypy .

web-typecheck:
	cd $(WEB_DIR) && pnpm typecheck

web-build:
	cd $(WEB_DIR) && pnpm build

ingest-validate:
	PYTHONPATH=$(API_DIR) python3 -m app.ingestion.cli validate --materials-dir data/course_materials

ingest-import:
	PYTHONPATH=$(API_DIR) python3 -m app.ingestion.cli import --materials-dir data/course_materials --database-url sqlite:///data/app.sqlite

ingest-rebuild:
	PYTHONPATH=$(API_DIR) python3 -m app.ingestion.cli import --materials-dir data/course_materials --database-url sqlite:///data/app.sqlite --rebuild

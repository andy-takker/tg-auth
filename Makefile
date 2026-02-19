develop:
	rm -rf .venv/
	python3.13 -m venv .venv
	.venv/bin/pip install -U pip uv
	.venv/bin/uv sync
	@echo "Dependencies successfully installed"

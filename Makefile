PROJECT_NAME = tg_auth
TEST_FOLDER_NAME = tests
PYTHON_VERSION = 3.13


# ---------- Local development ----------

develop: clean_dev ##@Develop Create virtualenv and install deps + pre-commit
	python$(PYTHON_VERSION) -m venv .venv
	.venv/bin/pip install -U pip uv
	.venv/bin/uv sync --all-groups
	.venv/bin/pre-commit install
	@echo "Dependencies successfully installed"

clean_dev: ##@Develop Remove virtualenv
	rm -rf .venv

run: ##@Develop Run the app locally
	.venv/bin/python -m $(PROJECT_NAME)

migrate: ##@Database Apply migrations to head
	.venv/bin/python -m $(PROJECT_NAME).adapters.database upgrade head

revision: ##@Database Autogenerate a new alembic revision (override MSG="...")
	.venv/bin/python -m $(PROJECT_NAME).adapters.database revision --autogenerate -m "$(MSG)"


# ---------- Tests / lint (CI mirrors these) ----------

develop-ci: ##@Develop Install deps without venv (CI)
	python -m pip install -U pip uv
	uv sync --all-groups --all-extras

test: ##@Test Run tests locally
	.venv/bin/pytest -v ./$(TEST_FOLDER_NAME)

test-ci: ##@Test Run tests with coverage (CI)
	.venv/bin/pytest -v ./$(TEST_FOLDER_NAME) --junitxml=./junit.xml --cov=./$(PROJECT_NAME) --cov-report=xml --cov-report=term

lint-ci: ruff ruff-format mypy ##@Linting Run all linters in CI

ruff: ##@Linting Run ruff check
	.venv/bin/ruff check ./$(PROJECT_NAME) ./$(TEST_FOLDER_NAME)

ruff-format: ##@Linting Run ruff format check
	.venv/bin/ruff format --check ./$(PROJECT_NAME) ./$(TEST_FOLDER_NAME)

mypy: ##@Linting Run mypy
	.venv/bin/mypy --config-file ./pyproject.toml ./$(PROJECT_NAME)


# ---------- Docker ----------

docker-build: ##@Docker Build the image
	docker compose build

docker-up: ##@Docker Run via docker-compose (foreground)
	docker compose up

docker-down: ##@Docker Stop and remove containers (volumes preserved)
	docker compose down

docker-down-volumes: ##@Docker Stop and wipe volumes (resets DB)
	docker compose down -v


# ---------- Help ----------

HELP_FUN = \
	%help; while(<>){push@{$$help{$$2//'options'}},[$$1,$$3] \
	if/^([\w-_]+)\s*:.*\#\#(?:@(\w+))?\s(.*)$$/}; \
	print"$$_:\n", map"  $$_->[0]".(" "x(22-length($$_->[0])))."$$_->[1]\n",\
	@{$$help{$$_}},"\n" for keys %help; \

help: ##@Help Show this help
	@echo -e "Usage: make [target] ... \n"
	@perl -e '$(HELP_FUN)' $(MAKEFILE_LIST)

.PHONY: develop clean_dev run migrate revision develop-ci test test-ci \
	lint-ci ruff ruff-format mypy docker-build docker-up docker-down \
	docker-down-volumes help

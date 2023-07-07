SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: help

help:
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| sed -n 's/^\(.*\): \(.*\)##\(.*\)/\1##\3/p' \
	| column -t -s '##'


install: ## Install and update python dependencies
	@poetry install --with test,docs,dev

lint: ## Check code with ruff linter
	@ruff . --fix

format: ## Format code with black
	@black .
tests:
	cd ./example && python ./manage.py test
coverage: ## Run coverage 
	cd ./example &&  coverage run --source=../ --rcfile=../pyproject.toml ./manage.py test && coverage report -m

deploy_docs: ## Deploy documentation to github pages
	mkdocs gh-deploy
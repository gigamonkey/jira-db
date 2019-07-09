all: fmt

lint:
	flake8
	isort --recursive . --check-only
	black . --check

fmt:
	isort --recursive .
	autoflake --recursive --in-place --remove-all-unused-imports --remove-unused-variables .
	black .

all: fmt

db:
	./build_db.py TECH

check:
	./qc.sh

lint:
	flake8
	isort --recursive . --check-only
	black . --check

fmt:
	isort --recursive .
	autoflake --recursive --in-place --remove-all-unused-imports --remove-unused-variables .
	black .

clean:
	rm -f jira.db

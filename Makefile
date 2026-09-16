.PHONY: help setup-docker api pipeline reports demo report-local clean

help:
	@echo "E-Commerce ELT Pipeline"
	@echo ""
	@echo "  make setup-docker   Ensure Docker/Colima is running"
	@echo "  make api            Start mock API (http://localhost:8000)"
	@echo "  make pipeline       Run extract -> load -> dbt inside Docker"
	@echo "  make reports        Generate analytics report from DuckDB"
	@echo "  make demo           Run full pipeline + report in one container"
	@echo "  make report-local   Generate report using local Python venv"
	@echo "  make clean          Remove dbt target artifacts"

setup-docker:
	@chmod +x scripts/setup-docker.sh
	@./scripts/setup-docker.sh

api:
	docker compose up --build api

pipeline: setup-docker
	docker compose --profile pipeline up --build pipeline

reports: setup-docker
	docker compose --profile reports run --rm reports

demo: setup-docker
	docker compose --profile demo up --build full-stack

report-local:
	./venv/bin/python -m reports.generate_report

clean:
	rm -rf dbt_project/target dbt_project/logs

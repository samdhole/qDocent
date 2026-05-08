.PHONY: setup r2r api web smoke ingest eval clean

setup:
	uv venv .venv
	uv pip install -r requirements.txt

r2r:
	uv run python -m r2r.serve

api:
	uv run uvicorn apps.api.main:app --reload --port 8000

web:
	cd apps/web && npm install && npm run dev

smoke:
	uv run python scripts/smoke_r2r.py

ingest:
	uv run python scripts/ingest_sample_docs.py

eval:
	mkdir -p reports/evals
	uv run python scripts/eval_ragas.py

clean:
	rm -rf .pytest_cache
	rm -rf reports/evals/*.csv
	rm -rf reports/evals/*.json

.PHONY: setup r2r api web smoke ingest eval demo-check clean test

setup:
	uv venv .venv
	uv pip install -r requirements.txt

r2r:
	R2R_CONFIG_PATH=r2r_gemini.toml uv run python -m r2r.serve

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

demo-check:
	uv run python scripts/demo_readiness.py

clean:
	rm -rf .pytest_cache
	rm -rf reports/evals/*.csv
	rm -rf reports/evals/*.json
	rm -rf reports/evals/*.md

test:
	uv run python -m pytest tests/ -v
	cd apps/web && npm test

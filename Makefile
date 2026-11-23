.PHONY: validate privacy-gate test sync help paper paper-tables

help:
	@echo "make validate  - all repository gates. A nonzero exit code is the product."
	@echo "make test      - unit and claim gates (W1 onward)"

validate:
	@python3 scripts/validate.py

privacy-gate:
	@python3 -c "import scripts.validate as v; v.gate_privacy(); print('privacy:', v.FAILURES or 'green')"

test:
	@if [ -d tests ] && [ -n "$$(ls -A tests 2>/dev/null)" ]; then uv run pytest tests; \
	else echo "no tests yet (W0: src/ is empty by design)"; fi

paper-tables:  ## Regenerate paper/generated/ from results/*.json (D046)
	python3 scripts/export_paper_tables.py

paper: paper-tables  ## Build paper/titer.pdf with tectonic (not part of validate)
	cd paper && SOURCE_DATE_EPOCH=1795392000 tectonic -X compile titer.tex

sync: validate

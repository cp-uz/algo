.DEFAULT_GOAL := check

PYTHON ?= python
HOST ?= 127.0.0.1
PORT ?= 8000
ACTION ?= approve
TYPE ?= technical
STATUS ?= pending

.PHONY: help setup build derive validate test check serve dev review review-status fetch upstream-check backup-proposals qa-algebra qa-algebra-smoke qa-algebra-full clean-generated

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "; printf "CP.UZ Algorithms commands:\n\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Create .venv and install Python dependencies
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -r requirements.txt

build: ## Generate JSON, CSV, static HTML and checksums from canonical inputs
	$(PYTHON) scripts/build_static.py

derive: ## Regenerate only derived metadata and checksums
	$(PYTHON) scripts/generate_derived.py

validate: ## Strictly verify schema, generated state, links, safety and checksums
	$(PYTHON) scripts/validate.py

test: ## Run the Python test suite
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 $(PYTHON) -m pytest -q

check: ## Build, test and validate exactly as CI does
	$(PYTHON) scripts/build_static.py
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 $(PYTHON) -m pytest -q
	$(PYTHON) scripts/validate.py

serve: build ## Serve the read-only static site at http://HOST:PORT/
	$(PYTHON) -m http.server $(PORT) --bind $(HOST) --directory site

dev: build ## Run the public site plus editor/moderation backend on one local server
	$(PYTHON) scripts/dev_server.py --host $(HOST) --port $(PORT) --skip-build

review: ## Review ARTICLE using ACTION=approve|request-changes|pending TYPE=technical|language REVIEWER='Name'
	@test -n "$(ARTICLE)" || (echo "ARTICLE is required" >&2; exit 2)
	@test -n "$(REVIEWER)" || (echo "REVIEWER is required" >&2; exit 2)
	$(PYTHON) scripts/review.py $(ACTION) "$(ARTICLE)" --type "$(TYPE)" --reviewer "$(REVIEWER)" $(if $(NOTES),--notes "$(NOTES)",)

review-status: ## Print the review queue; optionally ARTICLE=path.md
	$(PYTHON) scripts/review.py status $(ARTICLE)

fetch: ## Fetch exact Markdown at UPSTREAM_PIN into upstream/src without touching Uzbek docs
	$(PYTHON) scripts/fetch_upstream.py

upstream-check: ## Compare the pinned upstream commit with TO_COMMIT; add APPLY=1 to record flags
	@test -n "$(TO_COMMIT)" || (echo "TO_COMMIT is required" >&2; exit 2)
	$(PYTHON) scripts/sync_upstream.py --to-commit "$(TO_COMMIT)" $(if $(APPLY),--apply,)

backup-proposals: ## Back up the moderation database and a JSON export
	$(PYTHON) scripts/backup_proposals.py

qa-algebra: qa-algebra-smoke ## Run the fast deterministic Algebra QA used by CI

qa-algebra-smoke: ## Compile and run fast deterministic C++ Algebra checks
	@set -eu; trap 'rm -rf qa-bin' EXIT; mkdir -p qa-bin; \
	$${CXX:-g++} -std=gnu++20 -O2 -pipe tests/algebra_smoke_qa.cpp -o qa-bin/algebra_smoke_qa; \
	qa-bin/algebra_smoke_qa

qa-algebra-full: ## Run the slower exhaustive/randomized Algebra QA locally
	@set -eu; trap 'rm -rf qa-bin' EXIT; mkdir -p qa-bin; \
	$${CXX:-g++} -std=gnu++20 -O2 -pipe tests/algebra_randomized_qa.cpp -o qa-bin/algebra_randomized_qa; \
	qa-bin/algebra_randomized_qa; \
	$${CXX:-g++} -std=gnu++20 -O2 -pipe tests/algebra_randomized_qa_extended.cpp -o qa-bin/algebra_randomized_qa_extended; \
	qa-bin/algebra_randomized_qa_extended

clean-generated: ## Remove disposable generated output
	rm -rf site .pytest_cache qa-bin var/*.sqlite3 var/*.sqlite3-* __pycache__ cpuz/__pycache__ web/__pycache__ scripts/__pycache__ tests/__pycache__
	rm -f data/articles.json data/review_queue.csv MANIFEST.sha256

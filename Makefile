# One-command reproducible runs for the Figma -> Flutter pipeline.
#
#   make demo      generate a screen from a fixture, analyze it, smoke-test it
#                  (the same sequence CI runs — the project's Definition of Done)
#   make test      Python test suite only (no Flutter needed)
#
# Demo artifacts land in a gitignored scratch dir (flutter_app/lib/generated/),
# so nothing you've committed is clobbered. `make clean` removes them.

PYTHON       ?= python3
FLUTTER_ROOT ?= flutter_app
SAMPLE       ?= examples/figma_sample.json
GEN_DIR      ?= $(FLUTTER_ROOT)/lib/generated
DEMO_OUT     ?= $(GEN_DIR)/demo_screen.dart

# Benchmark fixture for `make eval` (committed so it runs on a fresh clone).
EVAL_INPUT   ?= examples/profile_posts_raw.json
EVAL_REF     ?= docs/figma_reference.png
EVAL_OUT     ?= $(GEN_DIR)/eval_screen.dart

.DEFAULT_GOAL := help

.PHONY: help setup test generate analyze smoke demo demos eval clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## Install Python dependencies (pipeline + tests)
	$(PYTHON) -m pip install pillow numpy pytest

test: ## Run the Python test suite (no Flutter required)
	$(PYTHON) -m pytest -q

generate: ## Generate a Flutter screen from $(SAMPLE)
	@mkdir -p $(GEN_DIR)
	$(PYTHON) -m agent.cli --input $(SAMPLE) --output $(DEMO_OUT)

analyze: ## Run `flutter analyze` on the generated app
	cd $(FLUTTER_ROOT) && flutter analyze

smoke: ## Run the golden smoke test (every screen builds & renders)
	cd $(FLUTTER_ROOT) && flutter test

demo: generate analyze smoke ## One-command proof: generate -> analyze -> smoke
	@echo ""
	@echo "OK  generated $(DEMO_OUT), flutter analyze clean, smoke tests passed."

eval: ## Reproduce the Case 1 visual + geometry scores offline (no token)
	@mkdir -p $(GEN_DIR)
	$(PYTHON) -m agent.cli \
	  --input $(EVAL_INPUT) \
	  --output $(EVAL_OUT) \
	  --visual-validate --reference-image $(EVAL_REF) \
	  --geometry-validate
	@rm -f $(FLUTTER_ROOT)/test/visual_golden_test.dart
	@rm -rf $(FLUTTER_ROOT)/test/visual_golden $(FLUTTER_ROOT)/test/visual_rects

demos: ## Generate every example screen (Python only, no Flutter)
	@mkdir -p $(GEN_DIR)
	$(PYTHON) -m agent.cli --input examples/figma_sample.json       --output $(GEN_DIR)/sample.dart
	$(PYTHON) -m agent.cli --input examples/figma_login.json        --output $(GEN_DIR)/login.dart
	$(PYTHON) -m agent.cli --input examples/figma_product_grid.json --output $(GEN_DIR)/shop.dart
	$(PYTHON) -m agent.cli --input examples/figma_settings.json     --output $(GEN_DIR)/settings.dart
	@echo "OK  generated 4 screens in $(GEN_DIR)/"

clean: ## Remove generated demo artifacts
	rm -rf $(GEN_DIR)

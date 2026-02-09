# Makefile for Apigee Migration Assessment Tool
#
# This Makefile provides a simple interface for setting up, testing, and running
# the assessment tool.

# Use bash for all shell commands
SHELL := /bin/bash
IMAGE_NAME := apigee-migration-assessment-tool
PYTHON_EXEC := venv/bin/python
COMMIT_ID := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
IMAGE_TAG := $(IMAGE_NAME):$(COMMIT_ID)
LATEST_TAG := $(IMAGE_NAME):latest

# Define variables that can be overridden from the command line.
APIGEE_USERNAME ?=
APIGEE_PASSWORD ?=
MFA ?=
SOURCE_ORG ?=
TESTS ?=

# Load .env file if it exists
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Default command, runs if you just type "make"
.DEFAULT_GOAL := help

# Phony targets don't represent files
.PHONY: setup install test build token command run clean help

# Creates the necessary configuration files.
setup:
	@python3 scripts/setup.py -o "$(SOURCE_ORG)"

# Installs dependencies into a venv for local testing/development, mirroring the CI workflow.
install:
	@echo "--- Installing local dependencies for testing ---"
	@if ! command -v python3.12 &> /dev/null; then \
		echo "Error: python3.12 not found in PATH. Please install it to continue."; \
		exit 1; \
	fi
	@if [ ! -d "venv" ]; then \
		echo "Creating Python 3.12 virtual environment..."; \
		python3.12 -m venv venv; \
	fi
	@echo "Installing dependencies from requirements.txt and test-requirements.txt..."
	@$(PYTHON_EXEC) -m pip install --upgrade pip
	@$(PYTHON_EXEC) -m pip install -r requirements.txt -r test-requirements.txt
	@echo "Installation complete."

# Runs unit tests, mirroring the CI workflow.
test: install
	@echo "--- Running unit tests ---"
	@$(PYTHON_EXEC) -m unittest -v $(TESTS)

# Builds the Docker image with commit-based tag.
build:
	@echo "--- Building Docker image: $(IMAGE_TAG) ---"
	@docker build -t $(IMAGE_TAG) .
	@docker tag $(IMAGE_TAG) $(LATEST_TAG)

# Generates a new auth token and prints it to stdout.
token:
	@APIGEE_USERNAME=$(APIGEE_USERNAME) APIGEE_PASSWORD=$(APIGEE_PASSWORD) MFA_CODE=$(MFA) bash scripts/get_token.sh 

# Displays the docker run command.
command:
	@if [ -z "$$SOURCE_AUTH_TOKEN" ]; then \
		echo "Error: SOURCE_AUTH_TOKEN is not set. Please run 'export SOURCE_AUTH_TOKEN=$(make token)' first."; \
		exit 1; \
	fi
	@echo ""
	@echo "--- Docker command for execution ---"
	@echo ""
	@echo "Copy and paste the following command to run the assessment:"
	@echo "----------------------------------------------------------------------"
	@echo 'docker run --rm -v "$$(pwd)/output:/app/target" -v "$$(pwd)/input.properties:/app/input.properties" -e SOURCE_AUTH_TOKEN="$$SOURCE_AUTH_TOKEN" "$(IMAGE_TAG)" --resources all --skip-target-validation'
	@echo "----------------------------------------------------------------------"
	@echo ""

# Generates token first, then builds image if needed, then runs the tool.
run:
	@echo "--- Checking for authentication token ---"
	@if [ -z "$$SOURCE_AUTH_TOKEN" ]; then \
		echo "SOURCE_AUTH_TOKEN not set. Generating token automatically..."; \
		SOURCE_AUTH_TOKEN=$$(make token MFA="$(MFA)"); \
		export SOURCE_AUTH_TOKEN; \
		echo "Token generated successfully."; \
	else \
		echo "Using existing SOURCE_AUTH_TOKEN."; \
	fi
	@echo "--- Checking if Docker image needs to be built ---"
	@if ! docker image inspect $(IMAGE_TAG) >/dev/null 2>&1; then \
		echo "Image $(IMAGE_TAG) not found. Building..."; \
		$(MAKE) build; \
	else \
		echo "Image $(IMAGE_TAG) already exists. Skipping build."; \
	fi
	@echo "--- Checking output directory ---"
	@if [ -d "output" ] && [ "$$(ls -A output 2>/dev/null)" ]; then \
		echo ""; \
		echo "⚠️  WARNING: Output directory contains files from previous runs!"; \
		echo ""; \
		echo "To avoid mixing old and new results, please choose one:"; \
		echo "  1. Clean run:  make clean-run"; \
		echo "  2. Keep existing:  make run-force"; \
		echo "  3. Manual cleanup:  rm -rf output && make run"; \
		echo ""; \
		echo "Current output contents:"; \
		ls -la output/ | head -10; \
		echo ""; \
		exit 1; \
	fi
	@mkdir -p output
	@docker run --rm \
		--user $(shell id -u):$(shell id -g) \
		-v "$(pwd)/output:/app/target" \
		-v "$(pwd)/input.properties:/app/input.properties" \
		-e SOURCE_AUTH_TOKEN="$$SOURCE_AUTH_TOKEN" \
		"$(IMAGE_TAG)" --resources all --skip-target-validation

# Runs the assessment with automatic cleanup of output directory.
clean-run:
	@echo "--- Running assessment with clean output directory ---"
	@rm -rf output
	@mkdir -p output
	@$(MAKE) run-force

# Runs the assessment without checking for existing output (force mode).
run-force:
	@echo "--- Running assessment tool (force mode) ---"
	@mkdir -p output
	@docker run --rm \
		--user $(shell id -u):$(shell id -g) \
		-v "$(pwd)/output:/app/target" \
		-v "$(pwd)/input.properties:/app/input.properties" \
		-e SOURCE_AUTH_TOKEN="$$SOURCE_AUTH_TOKEN" \
		"$(IMAGE_TAG)" --resources all --skip-target-validation

# Resets the workspace to a fresh-clone state.
clean:
	@echo "--- Cleaning workspace ---"
	@git clean -dfx

help:
	@echo ""
	@echo "Apigee Migration Assessment Tool - Helper Scripts"
	@echo "-------------------------------------------------"
	@echo ""
	@echo "Interactive Workflow:"
	@echo "  1. make setup"
	@echo "  2. make build"
	@echo "  3. export SOURCE_AUTH_TOKEN=\$$(make token)" 
	@echo "  4. make command"
	@echo "  5. Copy, paste, and execute the command from the previous step."
	@echo ""
	@echo "Non-Interactive Workflow:"
	@echo "  1. make setup SOURCE_ORG=\"<org>\""
	@echo "  2. make build"
	@echo "  3. make run MFA=\"<mfa_code>\""
	@echo "  4. Or: export SOURCE_AUTH_TOKEN=\$$(make token APIGEE_USERNAME=\"<user>\" APIGEE_PASSWORD=\"<pass>\" MFA=\"<mfa>\")"
	@echo "  5. Then: make run"
	@echo ""
	@echo "Unit Testing:"
	@echo "  make install       - Creates a Python 3.12 venv and installs dependencies for local testing."
	@echo "  make test          - Runs all unit tests."
	@echo "  make test TESTS=tests/test_scripts.py - Runs tests only for a specific module."
	@echo ""
	@echo "Other Commands:"
	@echo "  make clean-run  - Runs assessment with automatic output cleanup."
	@echo "  make run-force  - Runs assessment without checking for existing output."
	@echo "  make clean      - Resets the workspace to a fresh-clone state."
	@echo ""
	@echo "Prerequisites:"
	@echo "  - Docker installed and user added to docker group"
	@echo "  - If 'make build' fails with permission denied, run:"
	@echo "    sudo usermod -aG docker \$$USER && newgrp docker"
	@echo ""
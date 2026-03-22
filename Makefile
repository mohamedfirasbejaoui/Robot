.PHONY: help install launch clean check setup

# Colors
GREEN=\033[0;32m
YELLOW=\033[0;33m
RED=\033[0;31m
NC=\033[0m # No Color

help:
	@echo "================================="
	@echo "🤖 Robot Navigation System"
	@echo "================================="
	@echo ""
	@echo "Available targets:"
	@echo "  make check     - Check dependencies"
	@echo "  make setup     - Setup Webots paths"
	@echo "  make launch    - Launch simulation"
	@echo "  make install   - Install optional dependencies"
	@echo "  make clean     - Clean temporary files"
	@echo ""

check:
	@echo "$(YELLOW)Checking dependencies...$(NC)"
	@echo ""
	@python3 --version
	@echo ""
	@which webots || echo "$(RED)❌ Webots not found$(NC)"
	@echo ""
	@echo "$(GREEN)✅ Checks complete$(NC)"

setup:
	@echo "$(YELLOW)Setting up Webots paths...$(NC)"
	@echo ""
	@WEBOTS_HOME=$$(which webots | sed 's/\/bin\/webots//') ;\
	 if [ -z "$$WEBOTS_HOME" ]; then \
		WEBOTS_HOME="/snap/webots/current" ;\
	 fi ;\
	 echo "WEBOTS_HOME=$$WEBOTS_HOME" ;\
	 export WEBOTS_HOME ;\
	 echo "$(GREEN)✅ Setup complete$(NC)"

launch:
	@echo "$(YELLOW)Launching simulation...$(NC)"
	@echo ""
	@python3 scripts/launch_simulation.py

install:
	@echo "$(YELLOW)Installing optional dependencies...$(NC)"
	@pip3 install matplotlib numpy scipy
	@echo "$(GREEN)✅ Installation complete$(NC)"

clean:
	@echo "$(YELLOW)Cleaning temporary files...$(NC)"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type f -name "map.pkl" -delete
	@find . -type f -name "*.log" -delete
	@echo "$(GREEN)✅ Clean complete$(NC)"

.DEFAULT_GOAL := help

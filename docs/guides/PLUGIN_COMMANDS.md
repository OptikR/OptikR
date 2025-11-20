# OptikR Plugin Management Commands
# ==================================
# This file documents all plugin-related commands for OptikR

# Interactive Plugin Generator
# Creates a new plugin interactively (prompts for all settings)
create-plugin:
	python run.py --create-plugin

# Generate Plugin from Template Path
# Use this to generate a plugin from a specific template directory
# Example: make generate-plugin PATH=./my_plugin_template
generate-plugin:
	python run.py --plugin-generator "$(PATH)"

# Auto-Generate Missing Plugins
# Automatically creates plugins for installed packages that don't have plugins yet
# Works for: OCR engines, Translation engines, Capture libraries, Optimizers, Text Processors
auto-generate:
	python run.py --auto-generate-missing

# Run Application (Normal Mode)
# Starts OptikR with GUI
run:
	python run.py

# Run in Headless Mode
# Runs without UI (for testing/automation)
headless:
	python run.py --headless

# Plugin Discovery Information
# ==================================
# Plugins are automatically discovered and generated during startup:
#
# 1. OCR Plugins (plugins/ocr/)
#    - Auto-generates plugins for: easyocr, paddleocr, tesseract, manga_ocr
#    - Triggered during: OCR layer initialization
#
# 2. Translation Plugins (plugins/translation/)
#    - Auto-generates plugins when downloading translation models
#    - Triggered during: Model download
#
# 3. Capture Plugins (plugins/capture/)
#    - Auto-generates plugins for: mss, pyautogui, pyscreenshot
#    - Triggered during: Capture plugin discovery
#
# 4. Optimizer Plugins (plugins/optimizers/)
#    - Auto-generates plugins for: numba, cython
#    - Triggered during: Optimizer plugin discovery
#
# 5. Text Processor Plugins (plugins/text_processors/)
#    - Auto-generates plugins for: nltk, spacy, textblob, regex
#    - Triggered during: Text processor plugin discovery

# EXE Compatibility
# ==================================
# All command-line features work in EXE builds:
# - Plugin generation: YES (creates plugins in user directory)
# - Auto-generation: YES (discovers installed packages)
# - Headless mode: YES (runs without UI)
#
# When building EXE:
# - Plugins are bundled in the EXE
# - User can still create custom plugins in: %USERPROFILE%/.translation_system/plugins/
# - Auto-generation works for user-installed packages

# Development Commands
# ==================================

# List all discovered plugins
list-plugins:
	@echo "Scanning for plugins..."
	@python -c "from pathlib import Path; import json; \
	for ptype in ['ocr', 'translation', 'capture', 'optimizers', 'text_processors']: \
		pdir = Path('plugins') / ptype; \
		if pdir.exists(): \
			print(f'\n{ptype.upper()} Plugins:'); \
			for p in pdir.iterdir(): \
				if p.is_dir() and (p / 'plugin.json').exists(): \
					with open(p / 'plugin.json') as f: \
						data = json.load(f); \
						print(f'  - {data.get(\"display_name\", p.name)} (v{data.get(\"version\", \"?\")})'); \
	"

# Clean auto-generated plugins (keeps manual ones)
clean-auto-plugins:
	@echo "Cleaning auto-generated plugins..."
	@python -c "from pathlib import Path; import json; \
	for ptype in ['ocr', 'translation', 'capture', 'optimizers', 'text_processors']: \
		pdir = Path('plugins') / ptype; \
		if pdir.exists(): \
			for p in pdir.iterdir(): \
				if p.is_dir() and (p / 'plugin.json').exists(): \
					with open(p / 'plugin.json') as f: \
						data = json.load(f); \
						if data.get('author') == 'OptikR Auto-Generator': \
							print(f'Removing {p.name}...'); \
							import shutil; shutil.rmtree(p); \
	"

# Help
help:
	@echo "OptikR Plugin Commands"
	@echo "======================"
	@echo ""
	@echo "Plugin Creation:"
	@echo "  make create-plugin              - Interactive plugin generator"
	@echo "  make generate-plugin PATH=...   - Generate from template path"
	@echo "  make auto-generate              - Auto-generate missing plugins"
	@echo ""
	@echo "Application:"
	@echo "  make run                        - Start OptikR (GUI)"
	@echo "  make headless                   - Run without UI"
	@echo ""
	@echo "Development:"
	@echo "  make list-plugins               - List all discovered plugins"
	@echo "  make clean-auto-plugins         - Remove auto-generated plugins"
	@echo "  make help                       - Show this help"

.PHONY: create-plugin generate-plugin auto-generate run headless list-plugins clean-auto-plugins help

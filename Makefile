# mercury-qt Makefile
#
# On Linux:   make                  (source bundle)
# On Linux:   make install          (install to prefix)
# On Windows: make windows          (Nuitka standalone bundle, from MSYS2/MinGW64)
# On Windows: make windows-zip      (build + zip)
#
# Copyright (C) 2025 Rhizomatica
# Author: Rafael Diniz <rafael@riseup.net>
# SPDX-License-Identifier: GPL-3.0-or-later

APP_TITLE   ?= mercury-qt
PYTHON      ?= python3
MERCURY_DIR ?= ../mercury

prefix ?= /usr
bindir ?= $(prefix)/bin
datadir ?= $(prefix)/share

QT_VERSION := $(shell head -1 debian/changelog | sed 's/.*(\(.*\)).*/\1/')
MERCURY_VERSION := $(shell grep 'define VERSION__' $(MERCURY_DIR)/main.c 2>/dev/null | head -1 | sed 's/.*"\(.*\)".*/\1/')

# Directories
BUNDLE_DIR     ?= deployment
BUNDLE_NAME    := $(APP_TITLE)-$(QT_VERSION)
BUNDLE_RUNTIME := $(BUNDLE_DIR)/$(BUNDLE_NAME)

# Nuitka output lands here before we rename it
NUITKA_DIST := $(BUNDLE_DIR)/windows_bundle_entry.dist

.PHONY: all install clean linux-bundle windows windows-zip help

all: linux-bundle

help:
	@echo "Targets:"
	@echo "  linux-bundle   Build a source bundle for Linux (default)"
	@echo "  install        Install to prefix (Linux)"
	@echo "  windows        Nuitka standalone bundle (run from MSYS2/MinGW64)"
	@echo "  windows-zip    Build + zip the Windows bundle"
	@echo "  clean          Remove build artifacts"
	@echo ""
	@echo "Variables:"
	@echo "  PYTHON=$(PYTHON)  MERCURY_DIR=$(MERCURY_DIR)  prefix=$(prefix)"

# ---- Linux source bundle ----
linux-bundle:
	@echo "Building Linux source bundle: $(BUNDLE_RUNTIME)"
	rm -rf "$(BUNDLE_RUNTIME)"
	mkdir -p "$(BUNDLE_RUNTIME)"
	cp -a app.py requirements.txt apps assets core modules "$(BUNDLE_RUNTIME)/"
	find "$(BUNDLE_RUNTIME)" -type d -name '__pycache__' -prune -exec rm -rf {} +
	printf '#!/usr/bin/env bash\nset -euo pipefail\nscript_dir="$$(cd -- "$$(dirname -- "$${BASH_SOURCE[0]}")" && pwd)"\npython_bin="$${MERCURY_QT_PYTHON:-$(PYTHON)}"\nexport PYTHONPATH="$${script_dir}"\nexec "$${python_bin}" "$${script_dir}/app.py" mercury "$$@"\n' > "$(BUNDLE_RUNTIME)/$(APP_TITLE)"
	chmod +x "$(BUNDLE_RUNTIME)/$(APP_TITLE)"
	@echo "Done: $(BUNDLE_RUNTIME)/$(APP_TITLE)"

install: linux-bundle
	install -d $(DESTDIR)$(datadir)/$(APP_TITLE)
	cp -a $(BUNDLE_RUNTIME)/* $(DESTDIR)$(datadir)/$(APP_TITLE)/
	install -D -m 755 $(BUNDLE_RUNTIME)/$(APP_TITLE) $(DESTDIR)$(bindir)/$(APP_TITLE)

# ---- Windows Nuitka standalone bundle (run from MSYS2/MinGW64 shell) ----
windows:
	@echo "=== Building Nuitka standalone bundle ==="
	$(PYTHON) -m nuitka \
		windows_bundle_entry.py \
		--follow-imports \
		--enable-plugin=pyside6 \
		--standalone \
		--output-dir=$(BUNDLE_DIR) \
		--include-data-dir=assets=assets \
		--include-data-dir=apps/mercury_qt/assets=apps/mercury_qt/assets \
		--include-qt-plugins=networkinformation,platforminputcontexts \
		--noinclude-qt-translations \
		--noinclude-dlls="*.cpp.o" \
		--noinclude-dlls="*.qsb" \
		--mingw64 \
		--assume-yes-for-downloads \
		--quiet
	@# Rename Nuitka output to versioned directory
	rm -rf "$(BUNDLE_RUNTIME)"
	mv "$(NUITKA_DIST)" "$(BUNDLE_RUNTIME)"
	@# Rename the executable
	@if [ -f "$(BUNDLE_RUNTIME)/windows_bundle_entry.exe" ]; then \
		mv "$(BUNDLE_RUNTIME)/windows_bundle_entry.exe" "$(BUNDLE_RUNTIME)/$(APP_TITLE).exe"; \
	fi
	@# Stage mercury.exe
	@if [ -f "$(MERCURY_DIR)/mercury.exe" ]; then \
		cp "$(MERCURY_DIR)/mercury.exe" "$(BUNDLE_RUNTIME)/"; \
		echo "Staged mercury.exe"; \
	else \
		echo "Warning: mercury.exe not found at $(MERCURY_DIR)/mercury.exe"; \
		echo "Build mercury first: make -C $(MERCURY_DIR) windows"; \
	fi
	@# Stage hamlib DLLs (skip if already present to avoid clobbering Nuitka's copies)
	@if ls $(MERCURY_DIR)/radio_io/hamlib-w64/bin/*.dll >/dev/null 2>&1; then \
		for dll in $(MERCURY_DIR)/radio_io/hamlib-w64/bin/*.dll; do \
			name=$$(basename "$$dll"); \
			if [ ! -f "$(BUNDLE_RUNTIME)/$$name" ]; then \
				cp "$$dll" "$(BUNDLE_RUNTIME)/"; \
			fi; \
		done; \
		echo "Staged hamlib DLLs"; \
	fi
	@echo "Done: $(BUNDLE_RUNTIME)/$(APP_TITLE).exe"

WINDOWS_ZIP := $(APP_TITLE)-$(QT_VERSION)-mercury-$(MERCURY_VERSION).zip

windows-zip: windows
	rm -f "$(BUNDLE_DIR)/$(WINDOWS_ZIP)"
	cd "$(BUNDLE_DIR)" && zip -qr "$(WINDOWS_ZIP)" "$(BUNDLE_NAME)"
	@echo "Created: $(BUNDLE_DIR)/$(WINDOWS_ZIP)"

clean:
	rm -rf $(BUNDLE_DIR)/$(APP_TITLE)-* $(NUITKA_DIST)
	rm -rf $(BUNDLE_DIR)/windows_bundle_entry.build
	rm -f $(BUNDLE_DIR)/*.zip

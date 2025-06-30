#Einfach in der Komsole "make html" eingeben, um die HTML-Dokumentation zu erstellen.

# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build_docs
DOCSBUILDER   = makros/docs_build.sh
APPCOMPILER   = makros/CompileApplication.sh
LAUNCHER      = makros/LaunchCompiled.sh  # Use the script directly from makros. ENSURE NO TRAILING SPACES HERE.
TESTRUNNER    = makros/run_all_tests.sh   # Script to run all tests

# Attempt to trim whitespace from LAUNCHER as a defensive measure
TRIMMED_LAUNCHER := $(strip $(LAUNCHER))
# Also trim whitespace from TESTRUNNER for consistency
TRIMMED_TESTRUNNER := $(strip $(TESTRUNNER))

.PHONY: all help Makefile clean run-docs-build compile-app run-only build-only build-and-run test

# Default target: builds and then asks the user if they want to launch.
all: compile-app
	@echo "---------------------------------------------------------------------"
	@echo "Application built successfully!"
	@echo "---------------------------------------------------------------------"
	@echo "DEBUG: Using launcher at: $(TRIMMED_LAUNCHER)"
	@if [ -f "makros/prompt_and_launch.sh" ]; then \
		chmod +x makros/prompt_and_launch.sh; \
		makros/prompt_and_launch.sh "$(TRIMMED_LAUNCHER)"; \
	else \
		echo "ERROR: prompt_and_launch.sh script not found."; \
		echo "Please ensure this file is present in the makros directory."; \
		exit 1; \
	fi

# Build the application without launching it and without a prompt
build-only: compile-app
	@echo "---------------------------------------------------------------------"
	@echo "Application built successfully!"
	@echo "You can run it with: make run-only"
	@echo "---------------------------------------------------------------------"

# Target to build and immediately launch (unconditionally)
build-and-run: compile-app
	@echo "---------------------------------------------------------------------"
	@echo "Launching the compiled application..."
	@echo "---------------------------------------------------------------------"
	@if [ -f "$(TRIMMED_LAUNCHER)" ] && [ -x "$(TRIMMED_LAUNCHER)" ]; then \
		sudo "$(TRIMMED_LAUNCHER)"; \
	elif [ -f "$(TRIMMED_LAUNCHER)" ]; then \
		echo "ERROR: Launcher script $(TRIMMED_LAUNCHER) found but is not executable. Please run: chmod +x $(TRIMMED_LAUNCHER)"; \
		exit 1; \
	else \
		echo "ERROR: Launcher script $(TRIMMED_LAUNCHER) not found. Cannot launch."; \
		exit 1; \
	fi

# Just launch the application without rebuilding (faster)
run-only:
	@echo "---------------------------------------------------------------------"
	@echo "Launching the previously compiled application..."
	@echo "---------------------------------------------------------------------"
	@if [ -f "$(TRIMMED_LAUNCHER)" ] && [ -x "$(TRIMMED_LAUNCHER)" ]; then \
		sudo "$(TRIMMED_LAUNCHER)"; \
	elif [ -f "$(TRIMMED_LAUNCHER)" ]; then \
		echo "ERROR: Launcher script $(TRIMMED_LAUNCHER) found but is not executable. Please run: chmod +x $(TRIMMED_LAUNCHER)"; \
		exit 1; \
	else \
		echo "ERROR: Launcher script $(TRIMMED_LAUNCHER) not found. Cannot launch."; \
		exit 1; \
	fi

# Run all tests using the test runner script
test:
	@if [ -f "$(TRIMMED_TESTRUNNER)" ]; then \
		chmod +x "$(TRIMMED_TESTRUNNER)"; \
		"$(TRIMMED_TESTRUNNER)"; \
		TEST_EXIT_CODE=$$?; \
		if [ $$TEST_EXIT_CODE -ne 0 ]; then \
			echo "Tests failed with exit code $$TEST_EXIT_CODE."; \
			exit $$TEST_EXIT_CODE; \
		fi; \
	else \
		echo "ERROR: Test runner script $(TRIMMED_TESTRUNNER) not found."; \
		echo "Please ensure this file is present in the makros directory."; \
		exit 1; \
	fi

# Common Sphinx build targets as dependencies for run-docs-build
html: run-docs-build
	@echo "Sphinx documentation already built by docs_build.sh"
	@echo "Skipping duplicate sphinx-build command"

dirhtml latex epub xml texinfo man changes linkcheck doctest gettext: run-docs-build
	@echo "For additional formats, please modify docs_build.sh"
	@echo "Skipping extra sphinx-build commands"

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Target for cleaning build files
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILDDIR)
	rm -rf ./dist
	rm -rf ./build_pyinstaller
	rm -f ResearchGuideApp.spec
	rm -f researchguide.def
	rm -f researchguide.sif
	@echo "Clean complete."

# New target to build Apptainer container
build-apptainer:
	@echo "Building Apptainer container..."
	@if [ -f "makros/BuildApptainer.sh" ]; then \
		chmod +x makros/BuildApptainer.sh; \
		makros/BuildApptainer.sh; \
	else \
		echo "ERROR: BuildApptainer.sh script not found."; \
		echo "Please ensure this file is present in the makros directory."; \
		exit 1; \
	fi

# Simplify docs generation - just call the existing script directly
run-docs-build:
	@echo "Running docs_build.sh script to build documentation..."
	@chmod +x $(DOCSBUILDER)
	@cd $(shell dirname $(DOCSBUILDER)) && cd .. && ./$(DOCSBUILDER)
	@echo "Documentation build completed."
	@if [ ! -d "$(BUILDDIR)/html" ]; then \
		echo "WARNING: Documentation build directory not found at $(BUILDDIR)/html"; \
		echo "Check for errors in the documentation build process."; \
	else \
		echo "Documentation available at: $(BUILDDIR)/html/index.html"; \
	fi

# Compile the application after docs are built
compile-app: html
	chmod 777 makros
	@echo "Running CompileApplication.sh script to compile the application..."
	@if [ -x "$(APPCOMPILER)" ]; then \
		$(APPCOMPILER); \
		COMPILE_EXIT_CODE=$$?; \
		if [ $$COMPILE_EXIT_CODE -ne 0 ]; then \
			echo "ERROR: CompileApplication.sh failed with exit code $$COMPILE_EXIT_CODE."; \
			exit $$COMPILE_EXIT_CODE; \
		fi; \
		if [ -f "ResearchGuideApp.spec" ]; then \
			echo "Removing ResearchGuideApp.spec file..."; \
			rm -f ResearchGuideApp.spec; \
		fi; \
	else \
		echo "ERROR: $(APPCOMPILER) not found or not executable."; \
		exit 1; \
	fi

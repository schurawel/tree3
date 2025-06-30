# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from unittest.mock import MagicMock

# Ensure that Python can find the project root and packages
DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DOCS_DIR)  # Fix: PROJECT_ROOT is one level up from source
sys.path.insert(0, PROJECT_ROOT)

# Debug info to help with troubleshooting
print(f"Documentation directory: {DOCS_DIR}")
print(f"Project root: {PROJECT_ROOT}")
print(f"Python path: {sys.path}")

# Check if main.py is accessible
try:
    import main
    print("main.py module found!")
except ImportError as e:
    print(f"Warning: Could not import main.py: {e}")

# Mock classes to handle external dependencies
class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

# List of modules to mock
MOCK_MODULES = [
    'qasync', 
    'PyQt6', 
    'PyQt6.QtWidgets', 
    'PyQt6.QtCore'
]
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

# -- Project information -----------------------------------------------------
project = 'ResearchGuideUnearth'
copyright = '2025, Jason A. Schurawel'
author = 'Jason A. Schurawel'
# The full version, including alpha/beta/rc tags
release = '1.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx_rtd_theme',
    'sphinx.ext.graphviz',
    'sphinx.ext.autosummary',
    'sphinx.ext.coverage',
    'sphinx.ext.todo',
]

# Templates to use - make sure this is a list
templates_path = ['_templates']

# Files to exclude from source
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Options for autodoc ----------------------------------------------------
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'special-members': '__init__',
    'imported-members': True,
    'private-members': True,
    'ignore-module-all': True,
    'member-order': 'bysource',
}

# Generate autodoc stubs for modules
autosummary_generate = True
autosummary_imported_members = True

# Add any paths that contain templates here, relative to this directory.
# This is particularly important for autosummary to work correctly
templates_path = ['_templates']

# -- Napoleon settings ------------------------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_attr_annotations = True

# -- Intersphinx mapping ----------------------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

# -- Documentation warnings ------------------------------------------------
nitpicky = False  # Disable nitpicky to reduce warnings during initial setup
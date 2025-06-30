.. filepath: /home/client1/Documents/researchguide/source/contributing.rst

Contributing to ResearchGuideUnearth
===================================

Thank you for your interest in contributing to ResearchGuideUnearth! This guide will help you get started.

Setting Up Your Development Environment
-------------------------------------

1. **Clone the repository**:

   .. code-block:: bash

      git clone https://github.com/username/ResearchGuideUnearth.git
      cd ResearchGuideUnearth

2. **Create a virtual environment**:

   .. code-block:: bash

      python -m venv .venv
      source .venv/bin/activate  # On Windows: .venv\Scripts\activate

3. **Install development dependencies**:

   .. code-block:: bash

      pip install -e ".[dev]"

Project Structure
---------------

.. code-block:: text

    ResearchGuideUnearth/
    ├── ResearchGuideUnearth/      # Main package
    │   ├── frontend/              # Frontend components
    │   ├── backend/               # Backend components
    │   ├── shared/                # Shared utilities
    │   ├── config/                # Configuration management
    │   └── tests/                 # Unit and integration tests
    ├── docs/                      # Documentation
    ├── source/                    # Documentation source files
    ├── build_docs/                # Built documentation (generated)
    ├── makros/                    # Build scripts
    └── main.py                    # Application entry point

Development Workflow
------------------

1. **Fork the repository** on GitHub
2. **Create a feature branch**:

   .. code-block:: bash

      git checkout -b feature/your-feature-name

3. **Make your changes**, following our code standards
4. **Write or update tests** for your changes
5. **Run the test suite** to ensure everything passes:

   .. code-block:: bash

      pytest

6. **Update documentation** for any new features:

   .. code-block:: bash

      make run-docs-build

7. **Commit your changes** with clear, descriptive commit messages:

   .. code-block:: bash

      git commit -m "Add feature: short description
      
      Longer description explaining the feature and its benefits.
      Closes #123."

8. **Push your branch** to your fork:

   .. code-block:: bash

      git push origin feature/your-feature-name

9. **Submit a pull request** through GitHub

Code Standards
------------

* Follow `PEP 8 <https://peps.python.org/pep-0008/>`_ style guidelines
* Use type hints for all function parameters and return values
* Include docstrings for all functions, classes, and modules
* Maintain test coverage above 80%
* Use meaningful variable and function names
* Keep functions focused on a single responsibility

Code Review Process
-----------------

All contributions go through a code review process:

1. A maintainer will review your pull request
2. CI tests will run automatically
3. You may receive feedback requesting changes
4. Once approved, your code will be merged

Documentation
------------

All new features should include documentation:

* API documentation in docstrings (Google style format)
* Update user guides if necessary
* Example code demonstrating usage

We use Sphinx for documentation generation. To build the docs locally:

.. code-block:: bash

   make run-docs-build

Questions?
---------

If you have any questions or need help, you can:

* Open an issue on GitHub
* Join our community chat
* Email the maintainers at: maintainers@example.com

Thank you for contributing to ResearchGuideUnearth!
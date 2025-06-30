.. filepath: /home/client1/Documents/researchguide/source/installation.rst

Installation Guide
================

This guide helps you install ResearchGuideUnearth on your system.

System Requirements
-----------------

* Python 3.8 or higher
* Git
* Make (for build process)
* Qt6 libraries (automatically installed in virtual environment)

Quick Installation
----------------

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/username/ResearchGuideUnearth.git
      cd ResearchGuideUnearth

2. Create and activate a virtual environment:

   .. code-block:: bash

      python -m venv .venv
      source .venv/bin/activate  # On Windows: .venv\Scripts\activate

3. Install requirements:

   .. code-block:: bash

      pip install -r requirements.txt

4. Build the application:

   .. code-block:: bash

      make build-only

Detailed Build Options
--------------------

ResearchGuideUnearth provides several make commands for different build scenarios:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Command
     - Description
   * - ``make html``
     - Builds the Sphinx HTML documentation only
   * - ``make run-docs-build``
     - Runs the docs_build.sh script to generate documentation
   * - ``make compile-app``
     - Builds documentation and compiles the application
   * - ``make build-only``
     - Builds the application without launching it
   * - ``make build-and-run``
     - Builds the application and immediately launches it
   * - ``make run-only``
     - Launches a previously built application without rebuilding
   * - ``make clean``
     - Removes all build artifacts and generated files

Installation Troubleshooting
--------------------------

Virtual Environment Issues
^^^^^^^^^^^^^^^^^^^^^^^^^

If you encounter issues with the virtual environment:

.. code-block:: bash

   # Remove the existing virtual environment
   rm -rf .venv
   
   # Create a new one
   python -m venv .venv
   source .venv/bin/activate
   
   # Reinstall requirements
   pip install -r requirements.txt

Build Process Failures
^^^^^^^^^^^^^^^^^^^^

If the build process fails:

1. Check the log output for specific errors
2. Ensure all dependencies are installed
3. Try cleaning and rebuilding:

   .. code-block:: bash
      
      make clean
      make build-only

Advanced Installation
-------------------

For system administrators or advanced users who need to deploy the application across multiple systems, please consult the Apptainer container option:

.. code-block:: bash

   make build-apptainer
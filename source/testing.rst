.. filepath: /home/client1/Documents/researchguide/source/testing.rst

Testing
=======

This section provides information on testing the ResearchGuideUnearth application.

Running Tests
------------

The ResearchGuideUnearth project uses pytest for unit and integration testing.

To run all tests:

.. code-block:: bash

   cd /home/client1/Documents/researchguide
   pytest

To run tests for a specific module:

.. code-block:: bash

   pytest tests/test_temp_operations.py

To run tests with verbose output:

.. code-block:: bash

   pytest -v

To run tests with coverage reporting:

.. code-block:: bash

   pytest --cov=ResearchGuideUnearth tests/

Test Module Documentation
------------------------

.. automodule:: tests.test_temp_operations
   :members:
   :undoc-members:
   :show-inheritance:
   :private-members:

Test Structure
-------------

The test suite is organized as follows:

- ``tests/`` - Top-level directory containing all tests
  - ``test_temp_operations.py`` - Tests for temporary file operations
  - Additional test files for other modules

Writing Tests
-----------

When writing tests for ResearchGuideUnearth, follow these guidelines:

1. Create test files in the ``tests/`` directory
2. Use meaningful test names that describe what's being tested
3. Add appropriate docstrings to test functions
4. Use pytest fixtures for common setup and teardown operations
5. Test both normal operation and error handling
6. Mock external dependencies when appropriate

Example Test
-----------

.. code-block:: python

   def test_create_channel(temp_dir):
       """
       Test creating a new channel.
       
       Args:
           temp_dir: Temporary directory fixture
       """
       channel_name = "test_channel"
       pipe_path = create_channel(temp_dir, channel_name)
       
       # Check that file was created
       assert os.path.exists(pipe_path)
       assert pipe_path == os.path.join(temp_dir, channel_name)
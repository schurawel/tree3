.. filepath: /home/client1/Documents/researchguide/source/temp_operations.rst

Temporary Operations Module
==========================

This module provides functions for handling temporary file operations used for inter-process communication.

Module Documentation
------------------

.. automodule:: ResearchGuideUnearth.shared.temp_operations
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
   :private-members:

Functions
--------

.. currentmodule:: ResearchGuideUnearth.shared.temp_operations

.. autosummary::
   :nosignatures:
   
   check_if_channel_exists
   create_channel
   set_channel
   remove_channel
   flush_channel
   _read_line_from_pipe
   _write_ticket_to_pipe
   _prepare_ticket_for_json
   _read_line_without_deleting
   _read_and_find_response
   _read_pipe_content
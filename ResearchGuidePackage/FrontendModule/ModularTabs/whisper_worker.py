"""
Whisper Worker Process
=====================
A separate process that handles transcription using Whisper,
isolated from the main application to prevent crashes.
"""

import os
import sys
import json
import tempfile

def transcribe_audio(file_path, model_size="base"):
    """
    Transcribe audio using Whisper in an isolated process.
    
    Args:
        file_path: Path to audio file
        model_size: Whisper model size to use
        
    Returns:
        dict: Transcription result or error
    """
    try:
        # Import whisper here to keep it isolated to this process
        import whisper
        
        # Load model
        model = whisper.load_model(model_size)
        
        # Perform transcription
        result = model.transcribe(file_path)
        
        # Return success with text
        return {
            "success": True, 
            "text": result["text"],
            "error": None
        }
    except Exception as e:
        # Return error
        return {
            "success": False,
            "text": None,
            "error": str(e)
        }

if __name__ == "__main__":
    """
    Main entry point for the worker process.
    Expected arguments: file_path model_size
    Writes result to stdout as JSON
    """
    if len(sys.argv) < 3:
        result = {"success": False, "text": None, "error": "Invalid arguments"}
    else:
        file_path = sys.argv[1]
        model_size = sys.argv[2]
        
        if not os.path.exists(file_path):
            result = {"success": False, "text": None, "error": f"File not found: {file_path}"}
        else:
            result = transcribe_audio(file_path, model_size)
    
    # Output result as JSON for the parent process to read
    print(json.dumps(result))
    sys.stdout.flush()
    
    # Exit successfully to avoid ResourceWarning
    sys.exit(0)

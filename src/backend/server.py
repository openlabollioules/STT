from flask import Flask, request, jsonify
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services import logger
from core import load_model
from diarization import start_transcription_n_diarization

def create_app():
    """Create Flask application"""
    app = Flask(__name__)
    
    # Load model when app starts
    # @app.before_first_request
    # def initialize():
    #     load_model()
    
    @app.route('/transcribe', methods=['POST'])
    def transcribe():
        """Handle transcription requests"""
        try:
            # Check if file is present
            if 'file' not in request.files:
                return jsonify({"error": "No file provided"}), 400
            
            file = request.files['file']
            
            # Save temporary file
            temp_path = f"/tmp/{file.filename}"
            file.save(temp_path)
            
            # Get optional parameters
            language = request.form.get('language')
            
            # Perform transcription
            transcription = start_transcription_n_diarization(temp_path)
            
            
            return jsonify({
                "transcription": transcription,
                "language": language
            }), 200
            
        except Exception as e:
            logger.error(f"Error in transcription endpoint: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    return app

if __name__ == "__main__":
    # Create and run the server
    app = create_app()
    app.run(host="0.0.0.0", port=8080)

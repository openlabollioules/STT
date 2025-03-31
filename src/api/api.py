from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging

# Import blueprints (will be created later)
from routes import  file_bp, post_process_bp

# Initialize logger
from services import logger

def create_app(test_config=None):
    """Application factory for Flask app"""
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Enable CORS
    CORS(app)
    
    # Configure app
    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Register blueprints
    # app.register_blueprint(transcription_bp, url_prefix='/api/transcription')
    # app.register_blueprint(diarization_bp, url_prefix='/api/diarization')
    app.register_blueprint(file_bp, url_prefix='/api/file')
    app.register_blueprint(post_process_bp, url_prefix='/api/post_process')
    # Root route for health check
    @app.route('/')
    def health_check():
        return jsonify({
            "status": "ok",
            "message": "STT API is running"
        })
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5050)

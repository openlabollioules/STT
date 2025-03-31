from flask import Blueprint, request, jsonify
import traceback

from src.core.translate import translate_text
from src.services.logger_service import get_logger

# Initialize logger
logger = get_logger("translation_api")

# Create blueprint
translation_bp = Blueprint('translation', __name__)

@translation_bp.route('/', methods=['POST'])
def translate():
    """
    Translate text
    ---
    parameters:
      - name: text
        in: body
        type: string
        required: true
        description: Text to translate
      - name: source_language
        in: body
        type: string
        required: false
        description: Source language code (auto-detect if not provided)
      - name: target_language
        in: body
        type: string
        required: true
        description: Target language code
    responses:
      200:
        description: Translation result
      400:
        description: Bad request
      500:
        description: Server error
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Check required fields
        if 'text' not in data:
            return jsonify({"error": "Missing required field: text"}), 400
            
        if 'target_language' not in data:
            return jsonify({"error": "Missing required field: target_language"}), 400
        
        # Get parameters
        text = data['text']
        source_language = data.get('source_language', None)
        target_language = data['target_language']
        
        # TODO: Implement the actual translation logic
        # For now, just showing the blueprint structure
        result = {"message": "This is a placeholder for translation results"}
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error during translation: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500 
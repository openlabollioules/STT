from flask import Blueprint, request, jsonify
import os, sys 
import traceback
import uuid
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..","..","..")))
from services import logger
from graph import post_process_graph
from werkzeug.utils import secure_filename
# Create blueprint
post_process_bp = Blueprint('post_process', __name__)

@post_process_bp.route('/', methods=['POST'])
def post_process():
    """
    Post process transcription result
    ---
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: Audio file to transcribe
      - name: model
        in: formData
        type: string
        required: false
        description: Model to use for transcription (default is base)
      - name: language
        in: formData
        type: string
        required: false
        description: Language code (optional)
    responses:
      200:
        description: Transcription result
      400:
        description: Bad request
      500:
        description: Server error
    """
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        file_id = str(uuid.uuid4())
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','..','output', 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        file_path = os.path.join(temp_dir, f"{file_id}_{filename}")
        file.save(file_path)

        file_name = filename.split(".")[0]
        result = post_process_graph.process_transcription(file_path)
        

        # If user does not select file, browser also
        # submits an empty part without filename
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        
        # TODO: Implement the actual transcription logic
        # For now, just showing the blueprint structure
        result = {"message": "This is a placeholder for transcription results"}
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500 
from flask import Blueprint, request, jsonify, send_file
import traceback
import os,sys
import uuid
from werkzeug.utils import secure_filename

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..","..")))
from diarization import start_transcription_n_diarization
from services import logger

# Create blueprint
file_bp = Blueprint('file', __name__)

# curl -X POST -F "file=@/Users/openlab/IA/STT/output/debat_IA.wav" http://localhost:5050/api/file/upload
@file_bp.route('/upload', methods=['POST'])
def upload_file(): # passer le lang code dans le upload file 
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            print(request.files)
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        
        # if the file is not an audio file 
        if not file.filename.lower().endswith(('.wav', '.mp3', '.flac', '.aac', '.ogg', '.wma', '.m4a')):
            return jsonify({"error": "The uploaded file is not an audio file"}), 400
        
        # submits an empty part without filename
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        # Get optional parameters
        file_type = request.form.get('file_type', 'audio')
        
        # Generate a unique filename
        file_id = str(uuid.uuid4())
        
        # Secure the original filename
        filename = secure_filename(file.filename)
        
        # Create temp directory if it doesn't exist
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','..','output', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Full path for saving the file
        file_path = os.path.join(temp_dir, f"{file_id}_{filename}")
    
        # Save the file
        file.save(file_path)

        file_name = filename.split(".")[0]
        result = start_transcription_n_diarization(f"./output/{file_name}.txt",file_path, "fr")
        
        # Read result path
        with open(result, 'r') as file:
            result = file.read()
        
        os.remove(file_path)

        # Prepare result
        result = {
            "file_id": file_id,
            "filename": filename,
            "file_type": file_type,
            "transcription" :result ,
            "message": "File uploaded successfully"
        }
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


# @file_bp.route('/download/<file_id>', methods=['GET'])
# def download_file(file_id):
#     """
#     Download a file
#     ---
#     parameters:
#       - name: file_id
#         in: path
#         type: string
#         required: true
#         description: ID of the file to download
#     responses:
#       200:
#         description: File content
#       404:
#         description: File not found
#       500:
#         description: Server error
#     """
#     try:
#         if file_id == "nonexistent":
#             return jsonify({"error": "File not found"}), 404
            
        
#         return jsonify({"message": "File download placeholder"}), 200
    
#     except Exception as e:
#         logger.error(f"Error during file download: {str(e)}")
#         logger.error(traceback.format_exc())
#         return jsonify({"error": str(e)}), 500 
    

# """
#     Upload a file
#     ---
#     parameters:
#       - name: file
#         in: formData
#         type: file
#         required: true
#         description: File to upload
#       - name: file_type
#         in: formData
#         type: string
#         required: false
#         description: Type of file (audio, text, etc.)
#     responses:
#       200:
#         description: Upload result
#       400:
#         description: Bad request
#       500:
#         description: Server error
#     """
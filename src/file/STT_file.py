import os
import sys
import time

from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import config
from core import do_transcription, load_model
from services import create_output_file, load_audio, start_post_process, logger

# # stockage des models dans le ./models/
# os.environ["HF_HOME"] =  os.getenv("MODEL_DIR")
load_dotenv()

# Définition du fichier
file_name = config.get("file_name")
audio_dir = config.get("audio_dir")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

file_path = audio_dir + file_name
start_time = time.time()


def transcribe_file(audio_file_path, write_auto_correction=True):
    """
    This function is used to transcribe audio files
    ___args___
        file_path : the audio file path
        write_auto_correction : if you want to have the auto-correction prompt to be writted inside the outputfile 
    ___return___
        Write the transcription inside the output_file.txt
    """
    try:
        logger.info(f"Starting transcription for file: {audio_file_path}")

        start_time = time.time()

        # Loading the Whisper Model
        model, processor, torch_dtype, device = load_model()

        charging_time = time.time()
        logger.info(f"Model loaded in {charging_time - start_time:.2f} seconds")

        # Load audio
        audio, duration = load_audio(audio_file_path)
        logger.info(f"Audio file {audio_file_path} loaded successfully. Duration: {duration:.2f} seconds")

        # Define output file
        file_name = audio_file_path.split("/")[-1].split(".")[0]  # Extract file name
        file_path = create_output_file(file_name, file_name)
        logger.info(f"Output file created: {file_path}")

        # Perform transcription
        do_transcription(audio, model, processor, torch_dtype, device, file_path)

        end_time = time.time()
        elapsed_time = end_time - charging_time
        logger.info(f"Transcription completed in {elapsed_time:.2f} seconds for a {duration:.2f}-second file")
        logger.info("Starting post-processing...")

        # starting post process
        start_post_process(write_auto_correction, file_path, file_name, deepseek=True)
        logger.info("Post-processing completed successfully.")
    except FileNotFoundError as e:
        logger.error(f"File not found: {audio_file_path}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error during transcription: {e}", exc_info=True)


if __name__ == "__main__":
    transcribe_file(file_path)

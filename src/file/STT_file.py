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
    Transcribes the given audio file and writes the transcription output to a file.
    This function performs several steps:
        - Loads the necessary Whisper model along with its processor and settings.
        - Loads the audio file and computes its duration.
        - Creates an output file based on the audio file's name.
        - Performs transcription using the loaded model and writes the results.
        - Executes a post-processing step (including optional auto-correction and deepseek enhancements).

    Parameters:
            audio_file_path (str): The path to the audio file to be transcribed.
            write_auto_correction (bool, optional): Flag to determine whether to apply auto-correction 
                                                                                                during the post-processing phase. Defaults to True.

    Exceptions:
            FileNotFoundError: Raised when the audio file cannot be found.
            Exception: Catches any unexpected errors that occur during processing.

    Returns:
            None

    Side Effects:
            - Logs progress and errors at various steps of the transcription workflow.
            - Creates output files for storing the transcription results.
            - Initiates post-processing routines on the generated transcription.
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

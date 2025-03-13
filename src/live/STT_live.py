### --- This file is the entry point of the live Speech to Text application--- ###

import os
import re
import sys
from datetime import datetime
from io import BytesIO

import numpy as np
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import config
from core import do_transcription, load_model
from services import create_output_file, start_post_process,logger

# Loads .env
load_dotenv()

# init
OUTPUT_DIR = os.getenv("OUTPUT_DIR")
reunion_name = config.get("REUNION_NAME")
date = datetime.today().strftime("_%Y-%m-%d_%H:%M:%S")
file_name = reunion_name + date

def send_text(text):
    """Function to send text to the interface"""
    print(text)
    sys.stdout.flush()


def cleanup_text(previous_text, new_text):
    """
    Cleans up transcribed text by removing repetitions between consecutive transcriptions and within the same text.

    This function performs the following cleanup operations:
    1. Removes overlapping text between consecutive transcriptions
    2. Removes repeated single words
    3. Removes repeated word pairs
    4. Normalizes spacing

    Parameters
    ----------
    previous_text : str
        The previously transcribed text segment
    new_text : str
        The newly transcribed text segment

    Returns
    -------
    str : The cleaned text with repetitions removed and proper spacing
    """
    if not previous_text:
        return new_text  # First pass, nothing to clean.

    # Temporarily removes punctuation to compare repetitions
    prev_clean = re.sub(r"[^\w\s]", "", previous_text).lower().split()
    new_clean = re.sub(r"[^\w\s]", "", new_text).lower().split()

    # Searches for the longest repeated sequence
    overlap = 0
    max_overlap = min(len(prev_clean), len(new_clean))

    for i in range(1, max_overlap + 1):
        if (
            prev_clean[-i:] == new_clean[:i]
        ):  # Checks if the end of previous_text == start of new_text
            overlap = i

    # Keeps the original form of new_text but removes the repetition
    words_new = new_text.split()
    cleaned_text = " ".join(
        words_new[overlap:]
    )  # Preserves the original punctuation of new_text

    # Removes internal repetitions ("I call I call" → "I call")
    cleaned_text = re.sub(r"\b(\w+)\s+\1\b", r"\1", cleaned_text, flags=re.IGNORECASE)

    # Removes repetitions of word groups ("success story success story" → "success story")
    cleaned_text = re.sub(
        r"(\b\w+\s+\w+\b)\s+\1", r"\1", cleaned_text, flags=re.IGNORECASE
    )

    # Removes unnecessary spaces
    cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

    return cleaned_text

file_path = create_output_file(file_name, reunion_name, date)

def transcribe_stream( language,write_auto_correction=True):
    """
    Process a continuous audio stream and perform real-time speech-to-text transcription.
    This function reads audio data from standard input in chunks, processes it using a pre-loaded
    speech recognition model, and performs transcription with overlap handling to ensure smooth
    continuous transcription across audio segments.
    Args:
        language (str): The language code for transcription (e.g., 'en' for English, 'fr' for French)
        write_auto_correction (bool, optional): Flag to enable auto-correction in post-processing. 
            Defaults to True.
    Returns:
        None
    Raises:
        Exception: Any exception that occurs during the transcription process is caught and logged.
    Notes:
        - The function expects 16-bit PCM audio input at 16kHz sampling rate
        - Uses a 0.5 second overlap between segments to maintain continuity
        - Processes audio in chunks when buffer reaches 3 seconds of data
        - Previous text segments are used for context and cleanup
    """
    buffer = BytesIO()
    model, processor, torch_dtype, device = load_model()

    overlap_duration = 0.5  # 0.30 seconde d'overlapping
    sample_rate = 16000  # Whisper travaille à 16kHz
    overlap_samples = int(
        overlap_duration * sample_rate * 2
    )  # Nombre d'échantillons à conserver pour l'overlap
    previous_audio = b""  # Stocke les données de l'overlap
    previous_text = ""
    send_text("Ready to transcribe...")
    send_text("\n")
    try:
        while True:
            data = sys.stdin.buffer.read(4096)  # Lire des blocs de 4096 octets
            if not data:
                break

            buffer.write(data)
            buffer_size = buffer.tell()
            
            # calcul du temps : taille du buffer / (echantillonnage * nombre de channels * taille d'un échantillon)
            # elapsed_time = buffer_size / (16000 * 1 * 2)
            # print("Buffer size:", buffer_size)

            if (buffer.tell() >= sample_rate * 3):  # Vérifier si on a 1,30 secondes d'audio
                buffer.seek(0)
                audio_data = buffer.read()
                buffer = BytesIO()

                # Ajouter l'overlap du segment précédent au début du nouveau segment
                audio_data = previous_audio + audio_data
                previous_audio = audio_data[-overlap_samples:]  # Stocker l'overlap pour le prochain segment

                # Convertir l'audio
                audio = (np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)/ 32768.0)
                results = do_transcription(audio, model, processor, torch_dtype, device, file_path,lang_code=language)
                
                if results:
                    new_text = results["text"]
                    cleaned_text = cleanup_text(previous_text, new_text)
                    send_text(cleaned_text)
                    previous_text = new_text
        # logger.info("Starting post process")
        # start_post_process(write_auto_correction, file_path, file_name)

    except Exception as e:
        logger.info(f"erreur : {e}")
    #     logger.info("Starting post process")
    #     start_post_process(write_auto_correction, file_path, file_name)

if __name__ == "__main__":
    language = sys.argv[1] if len(sys.argv) > 1 else "transcribe"
    transcribe_stream(language)
    start_post_process(True, file_path, file_name)

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


def merge_repeated_segments(
    last_formatted_text, last_end_time, formatted_text, new_end_time
):
    """
    merge las formatted text and fromated text and adjust the time stemps
    """
    # Extraire le dernier bout de phrase du texte précédent (2 à 4 mots)
    match_prev = re.search(r"(\b\w+(?: \w+){1,3})$", last_formatted_text)
    match_curr = re.match(r"^(\w+(?: \w+){1,3})", formatted_text)

    if match_prev and match_curr:
        last_words = match_prev.group(0)  # Ex: "pour coder"
        first_words = match_curr.group(0)  # Ex: "pour coder"

        # Vérifier si la fin de last_formatted_text est répétée au début de formatted_text
        if last_words == first_words:
            # Fusionner les deux textes en supprimant la répétition
            merged_text = last_formatted_text + formatted_text[len(first_words) :]
            merged_end_time = (
                new_end_time  # Le timestamp final est celui du dernier segment
            )
            return merged_text, merged_end_time

    return formatted_text, new_end_time


def send_text(text):
    """Function to send text to the interface"""
    print(text)
    sys.stdout.flush()


def cleanup_text(previous_text, new_text):
    """
    Removes repetitions between previous_text and new_text,
    while preserving correct punctuation and without a predefined list of corrections.
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

def transcribe_stream(mode, write_auto_correction=True):
    """
    This function takes the buffer audio and transcribe it
    --- args ---
        mode 
    --- return ---
        Le fichier retranscrit
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
                results = do_transcription(audio, model, processor, torch_dtype, device, file_path, mode=mode)
                
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
    mode = sys.argv[1] if len(sys.argv) > 1 else "transcribe"
    transcribe_stream(mode)
    start_post_process(True, file_path, file_name)

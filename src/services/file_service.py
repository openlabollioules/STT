import os
import pypandoc
import sys
import numpy as np
from dotenv import load_dotenv
from pydub import AudioSegment
from .logger_service import logger

load_dotenv()
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

if not OUTPUT_DIR:
    logger.warning("OUTPUT_DIR is not set in the environment variables. Using default directory './output'.")
    OUTPUT_DIR = "./output"


def create_output_file(input_file, reunion_name="", date=""):
    """
    Creates a new transcription output file.

    Args:
        input_file (str): Name of the input file.
        reunion_name (str, optional): Name of the meeting. Defaults to "".
        date (str, optional): Date of the meeting. Defaults to "".

    Returns:
        str: Path of the output file.
    """
    try:
        output_file = os.path.join(OUTPUT_DIR, f"transcription_{input_file}.txt")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Transcription de {reunion_name} \nFait le {date} \n\n")

        logger.info(f"Output file created: {output_file}")
        return output_file

    except Exception as e:
        logger.error(f"Error creating output file {input_file}: {e}", exc_info=True)
        return None


def write_in_output_raw(text, output_file):
    """
    Writes raw text to the output file if it is not a known Whisper V3-Turbo false positive.

    Args:
        text (str): Text to write.
        output_file (str): Path to the output file.
    """
    if text in [" Sous-titrage Société Radio-Canada", " Merci."]:
        logger.warning(f"Ignoring known false positive: '{text}'")
        return

    try:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(text + "\n")

        logger.info(f"Text appended to {output_file}")

    except Exception as e:
        logger.error(f"Error writing to output file {output_file}: {e}", exc_info=True)


def write_in_output_formated(result, output_file):
    """
    Writes formatted transcription results to the output file.

    Args:
        result (dict): Transcription result containing timestamps and text.
        output_file (str): Path to the output file.
    """
    try:
        if "chunks" in result:
            formatted_text = ""
            for chunk in result["chunks"]:
                start_time, end_time = chunk["timestamp"]
                text = chunk["text"]
                formatted_text += f"[{start_time:.2f}s - {end_time:.2f}s] {text}\n"
        else:
            formatted_text = result.get("text", "")

        if formatted_text in [" Sous-titrage Société Radio-Canada", " Merci."]:
            logger.warning(f"Ignoring known false positive: '{formatted_text}'")
            return

        with open(output_file, "a", encoding="utf-8") as f:
            f.write(formatted_text + "\n")

        logger.info(f"Formatted transcription written to {output_file}")

    except Exception as e:
        logger.error(f"Error writing formatted transcription to {output_file}: {e}", exc_info=True)


def load_audio(file_path, target_rate=16000):
    """
    Loads an MP3 audio file and converts it into a numpy tensor.

    Args:
        file_path (str): Path to the audio file.
        target_rate (int, optional): Target sample rate. Defaults to 16000.

    Returns:
        tuple: (numpy array of samples, audio duration in seconds).
    """
    try:
        logger.info(f"Loading audio file: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        # Load the audio file
        audio = AudioSegment.from_file(file_path, format="mp3")
        duration = audio.duration_seconds

        if duration == 0:
            logger.warning(f"Audio file {file_path} seems to be empty!")

        # Convert to 16kHz mono
        audio = audio.set_frame_rate(target_rate).set_channels(1)

        # Normalize and convert to numpy
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32) / 32768.0

        logger.info(f"Audio file {file_path} loaded successfully. Duration: {duration:.2f} seconds")
        return samples, duration

    except FileNotFoundError:
        raise  # Rethrow file not found error

    except Exception as e:
        logger.error(f"Error loading audio file {file_path}: {e}", exc_info=True)
        return None, 0.0

def save_transcriptions(output_file, transcriptions):
    """Sauvegarde les transcriptions formatées dans un fichier."""
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("**Transcriptions par locuteur**\n\n")
            for segment in transcriptions:
                f.write(f"[{segment['start']:.2f}s - {segment['end']:.2f}s] {segment['speaker']} : {segment['transcription']}\n\n")
        logger.info(f"Transcriptions sauvegardées dans {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error saving transcription file: {e}", exc_info=True)


def cleanup_transcriptions(transcriptions):
    """Fusionne les transcriptions consécutives d'un même locuteur."""
    if not transcriptions:
        return []

    cleaned_transcriptions = []
    current_segment = transcriptions[0]

    for i in range(1, len(transcriptions)):
        segment = transcriptions[i]

        if segment["speaker"] == current_segment["speaker"]:
            current_segment["end"] = segment["end"]
            current_segment["transcription"] += " " + segment["transcription"]
        else:
            cleaned_transcriptions.append(current_segment)
            current_segment = segment

    cleaned_transcriptions.append(current_segment)
    return cleaned_transcriptions

def md_2_docx(file_path,output_path):

    output = pypandoc.convert_file(file_path, 'docx', outputfile=f"{output_path}.docx")
    print("Conversion terminée !")
    return output_path

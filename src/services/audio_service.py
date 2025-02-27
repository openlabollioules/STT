from .logger_service import logger
import torch
import os
from pydub import AudioSegment
import numpy as np
from librosa import resample

def convert_audio_to_wav(input_file, output_wav_file=None, target_rate=16000):
    """
    Converts any audio file into WAV (mono, 16kHz).
    Args:
        input_file (str): Imput source path
        output_wav_file (str, optional): Output path
        target_rate (int, optional): rate 16kHz
    Returns:
        str: Chemin du fichier WAV converti.
    """
    try:
        if output_wav_file is None:
            output_wav_file = os.path.splitext(input_file)[0] + ".wav"

        logger.info(f"Conversion de {input_file} en WAV (Mono, {target_rate}Hz)...")

        # Charger le fichier audio (Pydub gère plusieurs formats)
        audio = AudioSegment.from_file(input_file)

        # Convertir en mono et ajuster le taux d'échantillonnage
        audio = audio.set_frame_rate(target_rate).set_channels(1)

        # Exporter en WAV
        audio.export(output_wav_file, format="wav")

        logger.info(f"Conversion terminée : {input_file} → {output_wav_file} ({target_rate} Hz, mono)")
        return output_wav_file

    except Exception as e:
        logger.error(f"Erreur lors de la conversion de {input_file} : {e}", exc_info=True)
        return None

def process_audio_for_whisper(waveform, sample_rate):
    """Transforme un extrait audio Pyannote en format compatible Whisper."""
    try:
        if waveform.size == 0:
            logger.warning(f"⚠️ Segment vide détecté ({sample_rate} Hz), passage au suivant...")
            return None

        if isinstance(waveform, torch.Tensor):
            waveform = waveform.numpy()

        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=0)

        if sample_rate != 16000:
            waveform = resample(waveform, orig_sr=sample_rate, target_sr=16000)

        waveform = waveform.astype(np.float32)
        waveform = waveform / np.max(np.abs(waveform))

        return waveform

    except Exception as e:
        logger.error(f"Error processing audio for Whisper: {e}", exc_info=True)

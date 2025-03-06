from .logger_service import logger
import torch
import os
from pydub import AudioSegment
import numpy as np
from librosa import resample

def convert_audio_to_wav(input_file, output_wav_file=None, target_rate=16000):
    """Convert an audio file to WAV format with specific parameters.
    This function takes an input audio file and converts it to WAV format with
    specified sampling rate and mono channel. If no output filename is provided,
    it will use the same name as input file with .wav extension.
    Args:
        input_file (str): Path to the input audio file
        output_wav_file (str, optional): Path for the output WAV file. Defaults to None.
        target_rate (int, optional): Target sampling rate in Hz. Defaults to 16000.
    Returns:
        str or None: Path to the converted WAV file if successful, None if conversion fails.
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
    """
    Process and normalize audio waveform for Whisper model input.

    This function performs several preprocessing steps on the audio waveform:
    1. Converts PyTorch tensor to numpy array if needed
    2. Converts stereo to mono if needed
    3. Resamples to 16kHz if needed
    4. Normalizes the waveform amplitude

    Args:
        waveform (Union[torch.Tensor, numpy.ndarray]): Input audio waveform
        sample_rate (int): Sample rate of the input audio in Hz

    Returns:
        numpy.ndarray: Processed waveform as float32 numpy array normalized to [-1,1] range
        None: If input waveform is empty

    Raises:
        Exception: If any error occurs during processing
    """
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

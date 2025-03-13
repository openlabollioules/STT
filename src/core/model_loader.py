import os, sys
from pyannote.audio import Audio, Pipeline
import torch
from langchain_ollama import OllamaLLM
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services import logger
from config import config

MODEL_DIR = os.getenv("MODEL_DIR")
HF_TOKEN = os.getenv("HF_TOKEN")

def load_model():
    """
    This function loads the AUDIO_MODEL.
    Returns:
        model: the transcription model
        processor: the processor for the model
        torch_dtype: dtype depending on GPU usage
        device: detected device (CPU/GPU)
    """
    try:
        # Detects the device and sets the appropriate dtype
        if torch.backends.mps.is_available():  # Apple Silicon GPU
            device = "mps"
            torch_dtype = torch.float16
            logger.info("Apple Silicon GPU detected (MPS mode).")
        elif torch.cuda.is_available():  # CUDA GPU
            device = "cuda:0"
            torch_dtype = torch.float16
            logger.info("CUDA GPU detected.")
        else:
            device = "cpu"
            torch_dtype = torch.float32
            logger.warning("No GPU detected, using CPU. Performance may be affected.")

        logger.debug(f"Device selected: {device}, dtype: {torch_dtype}")

        # Loading the model
        model_id = os.getenv("AUDIO_MODEL_NAME")
        if not model_id:
            logger.error("AUDIO_MODEL_NAME environment variable is not set.")
            raise ValueError("AUDIO_MODEL_NAME is not set in environment variables.")

        logger.info(f"Loading audio model: {model_id}")

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            # low_cpu_mem_usage=True,
            cache_dir=MODEL_DIR
        )
        model.to(device)
        logger.info("Audio model loaded successfully.")

        # loading processor
        processor = AutoProcessor.from_pretrained(model_id)
        logger.info("Processor loaded successfully.")

        return model, processor, torch_dtype, device

    except Exception as e:
        logger.error(f"Error loading audio model: {e}", exc_info=True)
        raise

def load_ollama_model():
    """
    This function loads the OLLAMA_MODEL (LLM).
    Returns:
        model: the Ollama model
    """
    try:
        # Loading the model 
        OLLAMA_MODEL = config.get("MODEL_NAME")
        if not OLLAMA_MODEL:
            logger.error("MODEL_NAME is missing in config.")
            raise ValueError("MODEL_NAME is not set in config.")

        logger.info(f"Loading Ollama LLM model: {OLLAMA_MODEL}")
        model = OllamaLLM(model=OLLAMA_MODEL)
        logger.info("Ollama LLM model loaded successfully.")

        return model

    except Exception as e:
        logger.error(f"Error loading Ollama LLM model: {e}", exc_info=True)
        raise

def load_pyannote():
    """
    Load the PyAnnote speaker diarization pipeline and set the appropriate device.

    This function checks for the availability of MPS (Metal Performance Shaders) and CUDA
    (Compute Unified Device Architecture) to determine the device to be used for running
    the PyAnnote pipeline. If neither is available, it defaults to using the CPU.

    Returns:
        Pipeline: The PyAnnote speaker diarization pipeline loaded on the appropriate device.
    """
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda:0"
    else:
        device = "cpu"

    logger.info(f"utilisation of the device : {device}")

    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", cache_dir=MODEL_DIR)
    pipeline.to(torch.device(device))
    return pipeline
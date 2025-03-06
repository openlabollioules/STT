import os, sys
from pyannote.audio import Audio
from pyannote.core import Segment
from pydub import AudioSegment
# import re
# from langchain_ollama import OllamaLLM
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core import do_transcription, load_model, load_pyannote
from services import logger,process_audio_for_whisper,convert_audio_to_wav,save_transcriptions, cleanup_transcriptions, transcription_post_process
from config import config

MODEL_DIR = os.path.abspath("../../models")
os.makedirs(MODEL_DIR, exist_ok=True)

def start_transcription_n_diarization(output_path,file_path,lang_code):
    """
    This function transcribe an audio file and use diarization for Speaker separation
    Args:
        output_path: output path file 
        file_path : the file path
    Return:
        Path to the final txt file  
    """
    pipeline = load_pyannote()

    # loading the audio 
    audio_file = convert_audio_to_wav(file_path)
    audio = AudioSegment.from_wav(audio_file)
    duration = len(audio) / 1000

    # Logs 
    logger.info(f"Durée totale de l'audio : {duration:.2f} secondes")
    logger.info("Exécution de la diarisation...")
    
    # Start diarization
    diarization = pipeline(audio_file)

    audio_handler = Audio()
    output_transcriptions = []
    model, processor, torch_dtype, device = load_model()
    
    # for each speaker we do transcription with wisper V3 turbo
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segment_end = min(turn.end, duration)
        
        logger.debug(f"Vérification du segment : Speaker={speaker}, Start={turn.start:.2f}s, End={segment_end:.2f}s")
        
        if turn.start >= duration:
            logger.warning(f"⚠️ Ignoré : Start {turn.start:.2f}s dépasse la durée {duration:.2f}s")
            continue

        if turn.start == segment_end:
            logger.warning(f"⚠️ Ignoré : Start et End identiques ({turn.start:.2f}s)")
            continue

        try:
            waveform, sample_rate = audio_handler.crop(audio_file, Segment(turn.start, segment_end))

            if waveform.numel() == 0:
                logger.warning(f"Segment vide ! Speaker={speaker}, Start={turn.start:.2f}s, End={segment_end:.2f}s")
                continue

            waveform_np = process_audio_for_whisper(waveform, sample_rate)

            if waveform_np is None:
                continue

            logger.debug(f"Shape: {waveform_np.shape}, Min: {waveform_np.min()}, Max: {waveform_np.max()}")

            transcription = do_transcription(waveform_np, model, processor, torch_dtype, device, "output.txt",lang_code=lang_code)

            output_transcriptions.append({
                "speaker": speaker,
                "start": turn.start,
                "end": turn.end,
                "transcription": transcription["text"],
            })
        except Exception as e:
            logger.error(f"Error processing speaker segment: {e}", exc_info=True)
            
    return save_transcriptions(output_path,cleanup_transcriptions(output_transcriptions))
    
# parse_transcript("final_transcription.txt")

# def DirProcess(TEXT):
#     OLLAMA_MODEL = config.get("MODEL_NAME")
#     model = OllamaLLM(model=OLLAMA_MODEL)
#     transcription_post_process("final_transcription.txt", model, "diarization_test", OLLAMA_MODEL, "diarization_prompt_fr", True, 0.4, deepseek=True, TEXT=TEXT)
    
    
    
# def parse_transcript(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         text = f.read()

#     # Expression régulière pour capturer : [début - fin] SPEAKER_x : contenu
#     pattern = r"\[\d+(?:\.\d+)?s\s*-\s*\d+(?:\.\d+)?s\]\s*(SPEAKER_\d+)\s*:\s*(.*?)(?=\[\d+(?:\.\d+)?s\s*-\s*\d+(?:\.\d+)?s\]\s*SPEAKER_\d+\s*:|$)"
#     matches = re.findall(pattern, text, re.DOTALL)

#     # Dictionnaire pour regrouper les interventions par speaker
#     speakers = {}
    
#     for speaker, content in matches:
        
#         content = content.strip()
#         DirProcess(speaker+content)
#         speakers.setdefault(speaker, []).append(content)
        
    
#     return speakers

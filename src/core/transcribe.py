import os, sys
from transformers import pipeline

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services import write_in_output_formated, logger

def do_transcription(audio,
                     model,
                     processor,
                     torch_dtype, 
                     device, 
                     output_file,
                     ):
    """
    This function takes an audio input and outputs the transcription inside the output_file.

    Args:
        audio : Audio data
        model : Pre-trained ASR model
        processor : Processor for feature extraction and tokenization
        torch_dtype : Data type (depends on GPU/CPU configuration)
        device : CPU or GPU
        output_file : File to store the transcription
        mode : "transcribe" (default) or "translate"

    Returns:
        Writes the transcription inside the output file and returns the result.
    """
    
    known_false_positive = [" Sous-titrage Société Radio-Canada", " Merci.", " Thank you."," Bye."," ん"]
    
    try:
        logger.info(f"Starting transcription ( device: {device})")

        # Débogage des paramètres
        logger.debug(f"Pipeline parameters - dtype: {torch_dtype}, chunk length: 30s")

        # Initialisation du pipeline ASR
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            chunk_length_s=30,
            batch_size=16,
            torch_dtype=torch_dtype,
            device=device
        )
        logger.info("ASR pipeline initialized successfully.")

        # Conversion en texte
        result = pipe(
            {"raw": audio, "sampling_rate": 16000},
            return_timestamps=True,
            chunk_length_s=30,
            # generate_kwargs={ "language": "fr"},
        )

        if not result or "text" not in result:
            logger.warning("Transcription result is empty or missing 'text' field.")
            return None

        # Vérification des faux positifs connus avec Whisper-V3-Turbo
        if result["text"] in known_false_positive:
            logger.warning("Ignoring result due to known false positive.")
            return None

        logger.info("Transcription completed successfully.")
        logger.debug(f"Transcription result: {result['text']}")

        # Écriture du résultat dans le fichier de sortie
        write_in_output_formated(result, output_file)
        logger.info(f"Transcription saved to {output_file}")

        return result

    except Exception as e:
        logger.error(f"Error during transcription: {e}", exc_info=True)
        return None


    # if "chunks" in result:
    #     formatted_text = ""
    #     start_time, end_time = None, None

    # for chunk in result["chunks"]:
    #     start_time = chunk["timestamp"][0]
    #     end_time = chunk["timestamp"][1]
    #     text = chunk["text"]
    #     formatted_text += f"[{start_time:.2f}s - {end_time:.2f}s] {text}\n"
    # else:
    #     formatted_text = result["text"]
    #     start_time = result["chunks"][0]["timestamp"][0] if "chunks" in result and result["chunks"] else 0.00
    #     end_time = result["chunks"][-1]["timestamp"][1] if "chunks" in result and result["chunks"] else 0.00

    # global last_formatted_text, last_end_time  # Stocker le dernier segment pour comparaison

    # if last_formatted_text:
    #     formatted_text, end_time = merge_repeated_segments(last_formatted_text, last_end_time, formatted_text, end_time)

    # last_formatted_text = formatted_text
    # last_end_time = end_time

    # if result["text"] not in [" Sous-titrage Société Radio-Canada", " Merci."]:
    #     with open(output_file, "a", encoding="utf-8") as f:
    #         f.write(formatted_text + "\n")


# def transcribe_from_file(audio, model, processor, torch_dtype, device, output_file):
#     pipe = pipeline(
#         "automatic-speech-recognition",
#         model=model,
#         tokenizer=processor.tokenizer,
#         feature_extractor=processor.feature_extractor,
#         chunk_length_s=30,
#         batch_size=16,
#         torch_dtype=torch_dtype,
#         device=device,
#     )

#     result = pipe(
#         {"raw": audio, "sampling_rate": 16000},
#         return_timestamps=True,  # Force les timestamps
#         chunk_length_s=30,  # Découpage en segments de 30s pour plus de précision
#         generate_kwargs={
#             "language": "fr",
#         }
#     )
#     write_in_output_formated(result,output_file)

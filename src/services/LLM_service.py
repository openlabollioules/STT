import os
import sys
from dotenv import find_dotenv, load_dotenv
from langchain_ollama import OllamaLLM

from .json_service import load_prompt
from .remove_think import remove_think_tags

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import config
from .logger_service import logger



def transcription_post_process(
    transcription_file_path,
    model,
    file_name,
    model_name="Ollama LLM",
    prompt_name="formatage_prompt_fr",
    write_in_file=True,
    temperature=0.7,
    additional_feedback="",
    summary="",
    TEXT="",
    deepseek=False,
):
    """
    Summarizes and formats the transcription using Ollama LLM.

    Args:
        transcription_file_path (str): Path of the transcription file.
        model (OllamaLLM): The LLM model instance.
        file_name (str): Name of the file being processed.
        model_name (str): Name of the LLM model used (default: "Ollama LLM").
        prompt_name (str): Prompt template name.
        write_in_file (bool): Whether to save the output in a file (default: True).
        temperature (float): LLM generation temperature (default: 0.7).
        additional_feedback (str, optional): Feedback text for correction prompts.
        summary (str, optional): Summary text for feedback prompts.
        deepseek (bool): Whether to apply deepseek post-processing.

    Returns:
        str: The processed transcription output.
    """
    try:
        output_dir = os.getenv("OUTPUT_DIR")
        load_dotenv()
        logger.info(f"Processing transcription with {model_name} - {prompt_name}")
        
        # Charger la transcription depuis le fichier
        if not os.path.exists(transcription_file_path):
            logger.error(f"Transcription file not found: {transcription_file_path}")
            raise FileNotFoundError(f"File not found: {transcription_file_path}")

        with open(transcription_file_path, "r", encoding="utf-8") as f:
            transcription_text = f.read()

        logger.debug(f"Loaded transcription text (first 100 chars): {transcription_text[:100]}")

        # Charger le prompt
        prompt_template = load_prompt(prompt_name)
        if not prompt_template:
            logger.error(f"Prompt '{prompt_name}' could not be loaded.")
            raise ValueError(f"Invalid prompt name: {prompt_name}")

        # Formattage du prompt avec les paramètres dynamiques
        if prompt_name == "auto_feedback_prompt_fr":
            prompt = prompt_template.format(transcription_text=transcription_text, summary_text=summary)
        elif prompt_name == "correction_prompt_fr":
            prompt = prompt_template.format(
                transcription_text=transcription_text,
                feedback_response=additional_feedback,
                summary_text=summary,
            )
        elif prompt_name =="diarization_prompt_fr":
            prompt = prompt_template.format(text=TEXT)
        else:
            prompt = prompt_template.format(transcription_text=transcription_text)

        logger.info(f"Prompt '{prompt_name}' applied successfully.")

        # Appel à l'API Ollama
        ollama_response = model.invoke(input=prompt, config={"temperature": temperature})
        logger.debug(f"Ollama response (first 100 chars): {ollama_response[:100]}")

        # Sauvegarde du résultat
        summary_file = os.path.join(output_dir, f"summary_{file_name}_{model_name}.md")

        if deepseek:
            ollama_response = remove_think_tags(ollama_response)

        if write_in_file:
            with open(summary_file, "a", encoding="utf-8") as f:
                # f.write(f"\n Résumé généré par {model_name}:\n\n")
                f.write(ollama_response)
            logger.info(f"Transcription saved to {summary_file}")

        return ollama_response

    except FileNotFoundError as e:
        logger.error(e, exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error during transcription post-process: {e}", exc_info=True)


def start_post_process(write_in_file_auto_correction, file_path, file_name, deepseek=False):
    """
    Starts the post-processing pipeline (formatting, summarizing, feedback, and correction).

    Args:
        write_in_file_auto_correction (bool): Whether to save auto-corrected text.
        file_path (str): Path of the transcription file.
        file_name (str): Name of the file.
        deepseek (bool): Whether to apply deepseek processing.

    Returns:
        int: 0 if successful.
    """
    try:
        logger.info("Starting post-processing pipeline...")

        dotenv_path = find_dotenv()
        if dotenv_path:
            load_dotenv(dotenv_path)
            logger.info(f".env file loaded from: {dotenv_path}")
        else:
            logger.warning("No .env file found.")

        # Import Ollama models
        OLLAMA_MODEL = config.get("MODEL_NAME")
        OUTPUT_DIR = os.getenv("OUTPUT_DIR")

        if not OUTPUT_DIR:
            logger.warning("OUTPUT_DIR not set. Using default './output'.")
            OUTPUT_DIR = "./output"

        model = OllamaLLM(model=OLLAMA_MODEL)
        logger.info(f"Using LLM model: {OLLAMA_MODEL}")

        # Formatage
        logger.info("Starting formatting process...")
        transcription_post_process(file_path, model, file_name, OLLAMA_MODEL, "formatage_prompt_fr", True, 0.4, deepseek=deepseek)
        logger.info("Formatting completed.")

        # Résumé
        logger.info("Generating summary...")
        summary = transcription_post_process(
            file_path,
            model,
            file_name,
            OLLAMA_MODEL,
            "summary_prompt_fr",
            write_in_file_auto_correction,
            0.7,
            deepseek=deepseek,
        )

        # Feedback
        logger.info("Generating feedback...")
        feedback = transcription_post_process(file_path,
                                            model,
                                            file_name,
                                            OLLAMA_MODEL,
                                            "auto_feedback_prompt_fr",
                                            write_in_file_auto_correction,
                                            0.3,
                                            summary=summary,
                                            deepseek=deepseek,
                                            )

        # Correction
        logger.info("Applying corrections...")
        transcription_post_process(file_path, model,file_name,OLLAMA_MODEL,"correction_prompt_fr",True,0.7,additional_feedback=feedback,summary=summary,deepseek=deepseek)

        logger.info(f"Post-processing completed successfully. Output: {file_path}")
        return 0

    except Exception as e:
        logger.error(f"Unexpected error during post-processing: {e}", exc_info=True)
        return 1

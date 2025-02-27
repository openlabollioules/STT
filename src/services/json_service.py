import json
import os

PROMPTS_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prompts.json"))
from .logger_service import logger

def list_available_prompts():
    """
    Returns a list of available prompt names from the JSON file.

    Returns:
        list: List of prompt names.
    """
    try:
        logger.info("Loading available prompts...")

        if not os.path.exists(PROMPTS_FILE_PATH):
            logger.error(f"Prompts JSON file not found: {PROMPTS_FILE_PATH}")
            raise FileNotFoundError(f"File not found: {PROMPTS_FILE_PATH}")

        with open(PROMPTS_FILE_PATH, "r", encoding="utf-8") as f:
            prompts = json.load(f)

        if not isinstance(prompts, dict) or not prompts:
            logger.warning("The prompts JSON file is empty or has an invalid format.")
            return []

        available_prompts = [prompt["name"] for prompt in prompts.values()]
        logger.info(f"Successfully loaded {len(available_prompts)} prompts.")
        logger.debug(f"Available prompts: {available_prompts}")

        return available_prompts

    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON in {PROMPTS_FILE_PATH}: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Unexpected error while loading prompts: {e}", exc_info=True)
        return []


def load_prompt(prompt_name):
    """
    Loads a prompt from the JSON file based on its name.

    Args:
        prompt_name (str): The name of the prompt to load.

    Returns:
        str: The prompt template.

    Raises:
        ValueError: If the prompt does not exist.
    """
    try:
        logger.info(f"Loading prompt: {prompt_name}")

        if not os.path.exists(PROMPTS_FILE_PATH):
            logger.error(f"Prompts JSON file not found: {PROMPTS_FILE_PATH}")
            raise FileNotFoundError(f"File not found: {PROMPTS_FILE_PATH}")

        with open(PROMPTS_FILE_PATH, "r", encoding="utf-8") as f:
            prompts = json.load(f)

        if not isinstance(prompts, dict) or prompt_name not in prompts:
            logger.warning(f"Prompt '{prompt_name}' not found in JSON file.")
            raise ValueError(f"The prompt '{prompt_name}' doesn't exist inside the JSON file.")

        logger.info(f"Prompt '{prompt_name}' successfully loaded.")
        logger.debug(f"Prompt content: {prompts[prompt_name]['template']}")

        return prompts[prompt_name]["template"]

    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON in {PROMPTS_FILE_PATH}: {e}", exc_info=True)
        return None
    except ValueError as e:
        logger.error(e)
        return None
    except Exception as e:
        logger.error(f"Unexpected error while loading prompt '{prompt_name}': {e}", exc_info=True)
        return None

import re

def remove_think_tags(text: str) -> str:
    """
    Remove any <think>...</think> sections from the given text using regex.

    Args:
        text (str): The input string containing potential <think> tags.

    Returns:
        str: The string with all <think>...</think> sections removed.
    """
    # re.DOTALL allows the dot to match newline characters as well.
    cleaned_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    cleaned_text = re.sub(r"```md.*?```","",cleaned_text,flags=re.DOTALL)
    return cleaned_text.strip()

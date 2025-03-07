import re

def remove_think_tags(text: str) -> str:
    """
    Remove any <think>...</think> sections from the given text and keep content
    inside ```md``` tags while removing the tags themselves.

    Args:
        text (str): The input string containing potential <think> tags.

    Returns:
        str: The processed string.
    """
    # Remove <think> tags and their content
    cleaned_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    
    # Remove only the ```md and ``` tags but keep their content
    cleaned_text = re.sub(r"```md(.*?)```", r"\1", cleaned_text, flags=re.DOTALL)
    
    return cleaned_text.strip()

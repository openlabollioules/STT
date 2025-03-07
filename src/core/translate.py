import os
import torch
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
from langdetect import detect
from services import logger

device = "mps" if torch.backends.mps.is_available() else "cpu"
model_name = "facebook/m2m100_418M"
 
MODEL_DIR = os.getenv("MODEL_DIR")
torch_dtype = torch.float16

tokenizer = M2M100Tokenizer.from_pretrained(model_name)
model = M2M100ForConditionalGeneration.from_pretrained(model_name, cache_dir=MODEL_DIR, torch_dtype=torch_dtype)
model.to(device)

def translate_text(text, target_lang):
    try:
        # Détection automatique de la langue source
        src_lang = detect(text)
        # Correction éventuelle des codes pour M2M100
        lang_map = {'zh-cn': 'zh', 'zh-tw': 'zh'}
        src_lang = lang_map.get(src_lang, src_lang)
        
        tokenizer.src_lang = src_lang
        encoded_text = tokenizer(text, return_tensors="pt").to(device)
        forced_bos_token_id = tokenizer.get_lang_id(target_lang)
        generated_tokens = model.generate(**encoded_text, forced_bos_token_id=forced_bos_token_id)
        return tokenizer.decode(generated_tokens[0], skip_special_tokens=True)
    except Exception as e:
        logger.error(f"Error: Could not detect language or translate text ({e})")
        return text

# from transformers import MarianMTModel, MarianTokenizer
# import os


# # Charger le modèle et le tokenizer une seule fois pour la performance
# # 'Helsinki-NLP/opus-mt-ROMANCE-en',
# device = "mps"
# # src_lang = "ROMANCE" # 'fr' 
# # tgt_lang = "en"
# model_name_ang = "Helsinki-NLP/opus-mt-ROMANCE-en"
# tokenizer = MarianTokenizer.from_pretrained(model_name_ang)
# model_ang = MarianMTModel.from_pretrained(model_name_ang, cache_dir=MODEL_DIR)

# def translate_text(text):
#     """
#     Translates the given text using a pre-trained language model.

#     Args:
#         text (str): The text to be translated.

#     Returns:
#         str: The translated text.
#     """
#     inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
#     translated_tokens = model_ang.generate(**inputs)
#     return tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
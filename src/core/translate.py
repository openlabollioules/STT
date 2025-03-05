from transformers import MarianMTModel, MarianTokenizer
import os
import torch


# Charger le modèle et le tokenizer une seule fois pour la performance
# 'Helsinki-NLP/opus-mt-ROMANCE-en',
MODEL_DIR = os.path.abspath("./models")
device = "mps"
torch_dtype = torch.float16
# src_lang = "ROMANCE" # 'fr' 
# tgt_lang = "en"
model_name = "Helsinki-NLP/opus-mt-ROMANCE-en"
tokenizer = MarianTokenizer.from_pretrained(model_name)
model = MarianMTModel.from_pretrained(model_name)

def translate_text(text):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    translated_tokens = model.generate(**inputs)
    return tokenizer.decode(translated_tokens[0], skip_special_tokens=True)

# Using Facebook model for translation
# import torch
# from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer

# device = "mps" if torch.backends.mps.is_available() else "cpu"
# model_name = "facebook/m2m100_418M"

# tokenizer = M2M100Tokenizer.from_pretrained(model_name)
# model = M2M100ForConditionalGeneration.from_pretrained(model_name,cache_dir=MODEL_DIR,torch_dtype=torch_dtype)
# model.to(device)

# def translate_text(text, src_lang="fr", tgt_lang="en"):
#     tokenizer.src_lang = src_lang
#     encoded_text = tokenizer(text, return_tensors="pt").to(device)
#     generated_tokens = model.generate(**encoded_text, forced_bos_token_id=tokenizer.get_lang_id(tgt_lang))
#     return tokenizer.decode(generated_tokens[0], skip_special_tokens=True)


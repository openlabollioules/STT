# from pydub import AudioSegment
# import torch
# import numpy as np
# from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
# import os
# import time
# from LLM_formatting import transcription_formatting
# from langchain_ollama import  OllamaLLM


# # Définition du fichier
# file_name = "lead_co.mp3"
# audio_dir ="audiofiles/"
# output_dir = "./benchmark"
# file_path = audio_dir + file_name

# start_time = time.time()
# models = [
#     "phi4:latest",
#     "llama3.3-32k-context:latest",
#     "smallthinker:latest",
#     "qwen2.5:32b",
#     "llama3.3:latest",
#     "command-r-plus:latest",
#     "qwq:latest",
#     # "llama3.2:latest",
#     "llama3.1:latest",
#     "phi3:medium",
#     "mixtral:8x7b-instruct-v0.1-q8_0"
# ]


# last_time = start_time

# os.makedirs("benchmark", exist_ok=True)
# bench_file ="./benchmark/benchmark-1.txt"
# with open(bench_file, "w", encoding="utf-8") as f:
#         f.write(f"benchmark des models\n\n")

# for modele in models:
#     # Définition du modèle Ollama
#     model = OllamaLLM(model=modele)

#     transcription_formatting("output/transcription_lead_co.mp3.txt", model, output_dir, file_name, modele)
#     end_time =time.time()
#     elapsed_time = end_time - last_time

#     with open(bench_file, "a", encoding="utf-8") as f:
#         f.write( f'\n --- Mise en forme finie en : {elapsed_time:.2f}s par {modele} --- \n --- Qualité de la transofrmation :  ---' + "\n\n")

#     print(f'\n --- Mise en forme finie en : {elapsed_time:.2f}s par {modele} --- \n')

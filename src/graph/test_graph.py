from postprocess_graph import TranscriptionProcessor

# Création d'un fichier de test temporaire
test_file_path = "final_transcription.txt"

# Initialisation du processeur de transcription
processor = TranscriptionProcessor()

# with open("graph_png.png", "wb") as f:
#         f.write(processor.graph.get_graph(xray=1).draw_mermaid_png())
processor.process_transcription(test_file_path)

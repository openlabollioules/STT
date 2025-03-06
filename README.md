
---
# Speech-to-Text & Translation Application

This application provides robust speech-to-text and translation functionalities for both live audio and pre-recorded files. Its key features include:

- **Live Transcription & Translation:** Capture system audio in real time via a loopback device for immediate transcription and translation.
- **File Transcription with Drag & Drop:** Easily transcribe audio files by dragging and dropping them into the interface.
- **Meeting Summaries with LangGraph:** Generate concise summaries from transcriptions (ideal for meetings or lengthy audio recordings) using the LangGraph pipeline.
- **Markdown Viewer & Editor:** Review and edit generated summaries in Markdown format, then export the final output as a DOCX file.
- **Customizable Preferences:** Adjust the transcription and summary behaviors through a modifiable `prompt.json` file that serves as a user template.

---

## Requirements

- **Audio Loopback:**  
  For live transcription, your system audio must be routed through a loopback device.  
  > **Note:** This feature currently supports macOS users. For testing, the application was configured using **BackHole-2ch**.
- **FFmpeg & PyPandoc:**  
  These are required for audio processing and document conversion.

---

## Installation

1. **Install Python dependencies:**  
   ```bash
   pip install -r requirements.txt
   ```
2. **Install FFmpeg,Python Markdown and PyPandoc:**  
   ```bash
   brew install ffmpeg && brew install python-markdown && brew install pypandoc
   ```

---

## Running the Application

Launch the main interface of the application using:

```bash
python3 main.py
```

This starts the user-friendly interface where you can select live transcription, live translation, file transcription via drag & drop, and summary generation.

---

## Terminal Commands

The application also supports command-line execution. For example, to run a live transcription instance directly, use:

```bash
ffmpeg -f avfoundation -i ":0" -ac 1 -ar 16000 -f wav - | python3 ./src/live/STT_live.py
```

---

## LangGraph Iteration

The LangGraph module is used to generate summaries from transcribed audio. This pipeline processes the transcription through several steps to produce a concise meeting or audio file summary. The diagram below provides an overview of the LangGraph flow:

![LangGraph representation](graph_png.png)

---

## Customization with prompt.json

Users can adjust transcription, translation, and summarization preferences by modifying the `prompt.json` file. This allows you to tailor the behavior of the application to your specific needs or template preferences.

---

## Project Architecture

```
Speech2Text/
│── benchmark/                      # Performance test results and benchmarks
│── audiofiles/                     # Sample audio files for testing
│── models/                         # Models (e.g., Whisper, Pyannote)
│── output/                         # Transcription and summary output files
│── pipeline/                       # For open-webui implementation
│── src/
│   │── live/                       # Live transcription module
│   │   │── __init__.py
│   │   │── STT_live.py             # Live transcription logic
│   │
│   │── file/                       # File transcription module
│   │   │── __init__.py
│   │   │── STT_file.py             # File transcription logic 
│   │
│   │── services/                   # Auxiliary services
│   │   │── __init__.py
│   │   │── folder_service.py       # File and directory handling
│   │   │── json_service.py         # JSON file management
│   │   │── LLM_service.py          # Language model services for translation/summarization
│   │   │── Remove_think.py         # Regex module to remove unwanted "think" segments (deepseek integration)
│   │
│   │── core/                       # Core functionality
│   │   │── __init__.py
│   │   │── model_loader.py         # Model loader
│   │   │── transcriber.py          # Transcription logic
│   │
│   │── benchmark/                  # Additional benchmark files
│   │   │── __init__.py
│   │   │── benchmark.py
│
│── README.MD
│── Graph_png.png                   # Diagram of LangGraph pipeline
│── requirements.txt
│── main.py                         # Application entry point 
```

---

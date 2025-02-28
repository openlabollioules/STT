# Speech to Text live and file Transcription

This app is made to generate live time transcriptions or process files for a transcription and generate a sumary based on them.

## How to lauch the code 

You need to have a loopback of your system audio for the live transcription. 

> [!NOTE]
> This command only works for MacOS users. 
> you need to get an adui loopback form your system audio I used **BackHole-2ch** to test the code.
> 
### Requirements :

Install requirements :
```bash 
pip install -r requirements.txt
```
Install ffmpeg and Pypandoc : 
```bash
brew install ffmpeg && brew install pypandoc 
```
For an instance of the live Version :
```bash
ffmpeg -f avfoundation -i ":0" -ac 1 -ar 16000 -f wav - | python3 ./src/live/STT_live.py
```
For the live interface :
```bash
python3 ./src/frontend/interface.py
```
## Steps of the Project : 

This is a plan of each steps for the Speech2text application for audio Files

```
Audio_file --> Transcription + diarization ( Wisper & Pyannote ) 
|--> Post_Prossesing --> Fomatting with LLM --> Summary with LLM 
|--> Feedback of the Summary with LLM --> Correcting the summary with the LLM based on the Feedback
```

## Project Architecture :

```
Speech2Text/
│── benchmark/                      # performances test results
│── audiofiles/                     # audio Files for testing
│── models/                         # models like wisper or pyannote
│── output/                         # Output results
│── src/
│   │── live/                       # Live transcription
│   │   │── __init__.py
│   │   │── STT_live.py             # logic for live transcription
│   │
│   │── file/                       # File transcription
│   │   │── __init__.py
│   │   │── STT_file.py             # Logic for file transcription 
│   │
│   │── services/                   # Services 
│   │   │── __init__.py
│   │   │── folder_service.py       # File and directory service
│   │   │── json_service.py         # service for Json files 
│   │   │── LLM_service.py          # LLM service 
│   │   │── Remove_think.py         # Rejex to remove Think with deepseek
│   │
│   │── core/                       # core of the project
│   │   │── __init__.py
│   │   │── model_loader.py         # Loads the models 
│   │   │── transcriber.py          # Transcription logic
│   │
│   │── benchmark/                  # Benchmarkfiles
│   │   │── __init__.py
│   │   │── benchmark.py
│   │
│── README.MD
│── requirements.txt
│── main.py                         # Entry point 
```
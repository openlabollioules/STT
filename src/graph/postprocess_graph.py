import os, sys
import re
from typing import Dict
from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from langgraph.graph import END, START, StateGraph

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import config
from services import load_prompt, remove_think_tags


class TranscriptionProcessor:
    def __init__(self, output_dir=None):
        """
        Initialise le post-processeur avec LangGraph et plusieurs modèles OllamaLLM.
        """
        # Loading env variables
        load_dotenv()
        self.output_dir = output_dir or os.getenv("OUTPUT_DIR")

        # Initialisation des modèles LLM pour chaque tâche
        self.llm_intro = OllamaLLM(model="deepseek-r1:8b", num_ctx=128000)
        self.llm_speakers = OllamaLLM(model="phi4:14b-q4_K_M", num_ctx=128000)
        self.llm_format = OllamaLLM(model="mistral-small:latest", num_ctx=128000)
        self.llm_shorter_phrase = OllamaLLM(model="mistral-small:latest", num_ctx=128000)
        self.llm_summary = OllamaLLM(model="deepseek-r1:14b", num_ctx=128000)
        self.llm_feedback = OllamaLLM(model="deepseek-r1:14b", num_ctx=128000)
        self.llm_correction = OllamaLLM(model="deepseek-r1:14b", num_ctx=128000)

        # Construire le LangGraph
        self.graph = self.build_graph()

    def generate_introduction(self, state: Dict) -> Dict:
        """Generates an Introduction for the transcription"""
        prompt_template = load_prompt("introduction_prompt_fr")
        intro = self.llm_intro.invoke(
            input=prompt_template.format(transcription_text=state["transcription_text"]),
            config={"temperature": 0.2},
        )
        state["intro"] = remove_think_tags(intro)
        return state

    def speakers_identification(self, state: Dict) -> Dict:
        """Identification of each speaker"""
        prompt_template = load_prompt("identification_prompt_fr")
        speakers = self.llm_speakers.invoke(
            input=prompt_template.format(transcription_text=state["transcription_text"]),
            config={"temperature": 0.2},
        )
        state["speakers"] = remove_think_tags(speakers)
        return state

    def format_transcription_step_by_step(self, state: Dict) -> Dict:
        """Formatting the raw transcription"""
        prompt_template = load_prompt("diarization_prompt_fr")
        pattern = r"\[\d+(?:\.\d+)?s\s*-\s*\d+(?:\.\d+)?s\]\s*(SPEAKER_\d+)\s*:\s*(.*?)(?=\[\d+(?:\.\d+)?s\s*-\s*\d+(?:\.\d+)?s\]\s*SPEAKER_\d+\s*:|$)"
        matches = re.findall(pattern, state["transcription_text"], re.DOTALL)

        formatted_results = []
        for speaker, content in matches:
            content = content.strip()
            result = self.llm_format.invoke(
                input=prompt_template.format(speakers=state["speakers"], transcription_text=speaker + content),
                config={"temperature": 0.0},
            )
            formatted_results.append(remove_think_tags(result))

        state["formatted_text"] = "\n" + "\n\n".join(formatted_results)
        return state

    def shorter_phrase_step_by_step(self, state: Dict) -> Dict:
        """Shorten the phrases for context preservation"""
        prompt_template = load_prompt("shorter_phrase")
        pattern = r"\[\d+(?:\.\d+)?s\s*-\s*\d+(?:\.\d+)?s\]\s*(SPEAKER_\d+)\s*:\s*(.*?)(?=\[\d+(?:\.\d+)?s\s*-\s*\d+(?:\.\d+)?s\]\s*SPEAKER_\d+\s*:|$)"
        matches = re.findall(pattern, state["transcription_text"], re.DOTALL)

        formatted_results = []
        for speaker, content in matches:
            content = content.strip()
            result = self.llm_shorter_phrase.invoke(
                input=prompt_template.format(transcription_text=speaker + content),
                config={"temperature": 0.5},
            )
            formatted_results.append(remove_think_tags(result))

        state["summarise_phrases"] = "\n" + "\n\n".join(formatted_results)
        return state

    def summarize_transcription(self, state: Dict) -> Dict:
        """Generates the summary of the transcription"""
        prompt_template = load_prompt("summary_prompt_fr")
        summary_text = self.llm_summary.invoke(
            input=prompt_template.format(transcription_text=state["summarise_phrases"]),
            config={"temperature": 0.7},
        )
        state["summary_text"] = remove_think_tags(summary_text)
        return state

    def generate_feedback(self, state: Dict) -> Dict:
        """Generates feedback for the summary based on the original transcription"""
        prompt_template = load_prompt("auto_feedback_prompt_fr")
        feedback_text = self.llm_feedback.invoke(
            input=prompt_template.format(transcription_text=state["transcription_text"], summary_text=state["summary_text"]),
            config={"temperature": 0.3},
        )
        state["feedback_text"] = remove_think_tags(feedback_text)
        return state

    def correct_transcription(self, state: Dict) -> Dict:
        """Corrects the summary based on the feedback"""
        prompt_template = load_prompt("correction_prompt_fr")
        corrected_text = self.llm_correction.invoke(
            input=prompt_template.format(
                transcription_text=state["summarise_phrases"],
                feedback_response=state["feedback_text"],
                summary_text=state["summary_text"],
            ),
            config={"temperature": 0.7},
        )
        state["corrected_text"] = remove_think_tags(corrected_text)
        return state

    def build_graph(self):
        """
        Create the pipeline graph for post-processing a transcription
        """
        graph = StateGraph(dict)

        # Adding nodes to the graph
        graph.add_node("generate_introduction", self.generate_introduction)
        graph.add_node("shorter_phrase_step_by_step", self.shorter_phrase_step_by_step)
        graph.add_node("identification_speakers", self.speakers_identification)
        graph.add_node("format_transcription", self.format_transcription_step_by_step)
        graph.add_node("summarize_transcription", self.summarize_transcription)
        graph.add_node("generate_feedback", self.generate_feedback)
        graph.add_node("correct_transcription", self.correct_transcription)

        # Graph links
        graph.add_edge(START, "generate_introduction")        
        graph.add_edge("generate_introduction", "identification_speakers")
        graph.add_edge("identification_speakers", "format_transcription")
        graph.add_edge("format_transcription", "shorter_phrase_step_by_step")
        graph.add_edge("shorter_phrase_step_by_step", "summarize_transcription")
        graph.add_edge("summarize_transcription", "generate_feedback")
        graph.add_edge("generate_feedback", "correct_transcription")
        graph.add_edge("correct_transcription", END)

        return graph.compile()


    def process_transcription(self, file_path: str):
        """
        Execute the pipeline LangGraph for the postprocess of a transcription
        """
        
        with open(file_path, "r", encoding="utf-8") as f:
            transcription_text = f.read()

        # Calling the pipeline of langgraph
        initial_state = {"transcription_text": transcription_text}
        result = self.graph.invoke(initial_state)

        # Saving the output file
        file_name = os.path.basename(file_path).split(".")[0]
        output_path = os.path.join(
            self.output_dir, f"final_transcription_{file_name}.md"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            # Write each part inside the output file
            f.write(result["intro"])
            f.write("\n")
            f.write("\n## Transcription Formaté : \n")
            f.write(result["formatted_text"])
            f.write("\n")
            f.write(result["summary_text"])
            f.write("\n")
            f.write(result["feedback_text"])
            f.write("\n")
            f.write(result["corrected_text"])

        print(f"\n Transcription saved here : {output_path}")

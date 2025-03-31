import os
import sys
import re
from typing import Dict
from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from langgraph.graph import END, START, StateGraph

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import config
from services import load_prompt, remove_think_tags


class TranscriptionProcessor:
    """    TranscriptionProcessor is responsible for orchestrating a multi-step post-processing pipeline for speech-to-text transcriptions.
    The pipeline performs a sequence of tasks including generating introductions, identifying speakers, formatting raw transcriptions,
    shortening phrases, summarizing the transcription, generating feedback, and finally correcting the transcription based on feedback.
    Each task is executed via a corresponding language model, with prompts tailored for each step.
    Attributes:
        output_dir (str): Directory where the final processed transcription file will be saved.
        llm_intro (OllamaLLM): LLM instance used to generate the introduction.
        llm_speakers (OllamaLLM): LLM instance for speaker identification.
        llm_format (OllamaLLM): LLM instance for formatting the transcription.
        llm_shorter_phrase (OllamaLLM): LLM instance for generating shortened phrases.
        llm_summary (OllamaLLM): LLM instance used to summarize the transcription.
        llm_feedback (OllamaLLM): LLM instance used to generate feedback on the transcription summary.
        llm_correction (OllamaLLM): LLM instance used to correct the transcription based on feedback.
        graph (LangGraph): Compiled state graph representing the processing pipeline.
    Methods:
        __init__(self, output_dir=None):
            Initializes the TranscriptionProcessor by loading environment variables, instantiating the language models,
            and building the processing graph.
        generate_introduction(self, state: Dict) -> Dict:
            Generates an introduction for the transcription using a predefined prompt template and updates the state with the result.
        speakers_identification(self, state: Dict) -> Dict:
            Identifies speakers in the transcription using a dedicated LLM model and updates the state with the identified speakers.
        format_transcription_step_by_step(self, state: Dict) -> Dict:
            Formats the raw transcription (including speaker diarization) by processing segments with a specific LLM prompt,
            returning the formatted text and updating the state.
        shorter_phrase_step_by_step(self, state: Dict) -> Dict:
            Processes transcription segments to produce shorter phrases for context preservation using a specified LLM model,
            updating the state with these summarized phrases.
        summarize_transcription(self, state: Dict) -> Dict:
            Generates a comprehensive summary of the transcription based on the shortened phrases,
            updating the state with the summary text.
        generate_feedback(self, state: Dict) -> Dict:
            Produces feedback for the generated summary by comparing it with the original transcription,
            updating the state with feedback information.
        correct_transcription(self, state: Dict) -> Dict:
            Corrects the summary transcription by incorporating feedback and regenerating a final version,
            updating the state with the corrected transcription.
        build_graph(self):
            Constructs and compiles the directed graph (pipeline) that defines the sequence of processing steps. 
            Nodes in the graph are connected in the following order: generate introduction, speaker identification, 
            transcription formatting, phrase shortening, transcription summarization, feedback generation, and transcription correction.
        process_transcription(self, file_path: str):
            Reads the raw transcription from the specified file, executes the processing pipeline,
            saves the final processed transcription to an output file, and returns the output file path.
    """
    def __init__(self, output_dir=None):
        # Loading env variables
        load_dotenv()
        self.output_dir = output_dir or os.getenv("OUTPUT_DIR")
        if not self.output_dir:
            self.output_dir= './output'
        self.NUM_CTX = 128000

        # Initializing LLM models for each task
        self.llm_intro = OllamaLLM(model="deepseek-r1:8b", num_ctx=self.NUM_CTX)
        self.llm_speakers = OllamaLLM(model="phi4:latest", num_ctx=self.NUM_CTX)
        self.llm_format = OllamaLLM(model="phi4:latest", num_ctx=self.NUM_CTX)
        self.llm_shorter_phrase = OllamaLLM(model="mistral-small:latest", num_ctx=self.NUM_CTX)
        self.llm_summary = OllamaLLM(model="deepseek-r1:14b", num_ctx=self.NUM_CTX)
        self.llm_feedback = OllamaLLM(model="deepseek-r1:14b", num_ctx=self.NUM_CTX)
        self.llm_correction = OllamaLLM(model="deepseek-r1:14b", num_ctx=self.NUM_CTX)
        self.llm_feedback = OllamaLLM(model="deepseek-r1:14b", num_ctx=self.NUM_CTX)
        self.llm_correction = OllamaLLM(model="deepseek-r1:14b", num_ctx=self.NUM_CTX)

        # Build the LangGraph
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
        
        Constructs and compiles the pipeline graph for transcription post-processing.

        This method creates a state graph representing a sequence of post-processing steps,
        including introduction generation, speaker identification, transcription formatting,
        phrase shortening, summarization, feedback generation, and transcription correction.
        The graph is built by adding individual processing nodes and linking them with directed edges
        that define the execution order, starting from a designated START node and ending at an END node.

        Returns:
            A compiled state graph that encapsulates the defined transcription post-processing pipeline.
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
        Processes a transcription from the provided file path by reading its content, passing it through a processing pipeline,
        and saving the resulting formatted transcription to a new Markdown file.
        This function:
            - Reads the transcription from the given file.
            - Invokes a processing pipeline with the transcription text as input.
            - Formats the output from the pipeline into a Markdown file.
            - Saves the Markdown file in the designated output directory.
        Args:
            file_path (str): The path to the file containing the transcription text.
        Returns:
            str: The full output path of the saved Markdown file.
        Raises:
            IOError: If there is an error reading the input file or writing the output file.
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
            f.write("\n## Transcription Formatée : \n")
            f.write(result["formatted_text"])
            f.write("\n")
            f.write(result["summary_text"])
            f.write("\n")
            f.write(result["feedback_text"])
            f.write("\n")
            f.write(result["corrected_text"])

        print(f"\n Transcription saved here : {output_path}")
        return str(output_path)

# Global instance 
post_process_graph = TranscriptionProcessor()
import sys
import os
import queue
import re
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog, Toplevel, Text, BOTH, LEFT, RIGHT, Frame
from tkinterdnd2 import DND_FILES, TkinterDnD
import markdown
from tkhtmlview import HTMLLabel
from ttkbootstrap.icons import Icon
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services import start_post_process, md_2_docx
from core import translate_text
from diarization import start_transcription_n_diarization
from graph import post_process_graph


class STTInterface:
    """
    STTInterface Class
    ------------------
    This class implements the graphical user interface for a Speech-to-Text (STT) application using the tkinter framework. 
    It provides functionalities to start/stop audio recording with ffmpeg, display live transcription as well as real-time translation,
    manage settings and themes, process dropped audio files, and open a Markdown editor for transcription post-processing.
    Attributes:
        root: The main tkinter window.
        themes: A list of pre-defined UI themes.
        initial_theme: A tkinter StringVar holding the current theme.
        style: ttkbootstrap style object initialized with the selected theme.
        languages: A dictionary mapping human-readable language names to their language codes.
        text_size: Current font size for text displays.
        settings_button: A button to open the settings window.
        text_display: A scrolled text widget for displaying transcription text.
        start_button: A button to start the audio capturing and STT process.
        post_process_button: Buttons to start post-processing and open the Markdown editor.
        save_button: A button to save the transcription to a file.
        translation_enabled: A boolean variable indicating if live translation is active.
        toggle_translation_button: A button to toggle the live translation display.
        language_var: A tkinter StringVar indicating the language selected for audio processing.
        audio_devices: List of available audio input devices as fetched by ffmpeg.
        selected_device: A tkinter StringVar holding the currently selected audio device.
        ffmpeg_process: Reference to the ffmpeg subprocess handling audio input.
        stt_process: Reference to the subprocess running the live STT process.
        queue: A thread-safe queue used for inter-thread communication (transcription and translation updates).
        running: A flag indicating if the recording and STT processes are active.
        translation_display: A scrolled text widget used for displaying translated text.
    Methods:
        __init__(root)
            Initializes the STT interface, configures the main window, widgets, and necessary variables.
        get_audio_devices()
            Retrieves the list of available audio devices by invoking ffmpeg and parsing its output.
        start_process()
            Starts the audio recording process with ffmpeg and launches the STT live script. It also updates the UI to reflect 
            that the recording has begun.
        listen_to_stt()
            Spawns a thread to continuously listen to the STDOUT of the STT process and enqueue transcribed text and initiate 
            translation if enabled.
        stop_process()
            Terminates both the ffmpeg and STT subprocesses, stops the live transcription process and updates the UI accordingly.
        zoom_in()
            Increases the font size of the transcription text as well as the highlight for the last transcribed phrase.
        zoom_out()
            Decreases the font size for the transcription text while ensuring it remains above a minimum threshold.
        reset_zoom()
            Resets the font size settings back to the default value.
        highlight_last_phrase()
            Highlights the most recently transcribed phrase in the text display area to visually distinguish it.
        save_transcription()
            Opens a file dialog for the user to select a file path and then saves the current transcription content to that file.
        start_post_processing()
            Opens a file picker for post-processing. It then runs a post-process function (e.g. diarization or formatting)
            and reflects the result in the UI.
        drop_event(event)
            Handles drag-and-drop events over the interface. It checks for valid audio file extensions and either processes 
            the file via a dedicated post-process window or shows an error message.
        open_drag_post_process_window(file_path)
            Opens a pop-up window asking the user to select the language for the dragged audio file and then initiates
            processing with a loading screen.
        start_drag_processing(file_path, file_name, lang_code)
            Processes an audio file initiated by drag-and-drop. It displays a loading window, launches the transcription 
            and diarization process, and finally loads the transcription result into the main display.
        load_transcription(file_path)
            Opens a specified file and loads its content into the transcription display area, providing confirmation upon success.
        open_markdown_editor(file_path="")
            Opens a separate window providing a split view Markdown editor and previewer. It also allows loading an existing 
            Markdown file, saving, and exporting the content to a Word document.
        open_translation_window()
            Creates and displays a new window dedicated to live translation output, separate from the main transcription display.
        toggle_translation()
            Toggles the visibility of the translation display zone and updates the control button text accordingly.
        translate_text(text)
            Translates the provided text in a background thread and queues the translated output for display, provided that 
            translation is enabled.
        open_settings()
            Opens the settings window, allowing users to adjust UI preferences such as font size, theme, audio input device,
            and language selection for audio transcription.
        update_font_size(new_size)
            Updates the font size in the transcription and translation display areas based on the provided slider value.
        apply_settings(new_theme)
            Applies the selected UI theme to the interface by reinitializing the style with the new theme.
    """
    def __init__(self, root):
        self.line_id = 0 
        self.themes = ["flatly", "cosmo", "minty","sandstone" ,"darkly", "cyborg", "superhero"]
        self.initial_theme=tk.StringVar(value=self.themes[1])
        self.root = root
        self.root.title("STT Interface")
        self.root.geometry("700x550")
        
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        self.root.geometry(f"700x550+{x-350}+{y-225}")
        self.root.minsize(650, 400)
        
        # add a theme form ttkbootstrap
        self.style = ttkb.Style(theme=self.themes[1])
        self.languages = {
            "auto" : "",
            "Français": "fr",
            "Anglais": "en",
            "Espagnol": "es",
            "Allemand": "de",
            "Italien": "it",
            "Portugais": "pt",
        }

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.language_translation_var=tk.StringVar(value="Français")
        self.text_size = 16

        # settings button
        self.settings_button = ttkb.Button(
            root, text="⚙️", command=self.open_settings,
            bootstyle="link", 
            padding=0,
        )

        self.settings_button.grid(row=0, column=5, sticky="nw", ipady= 5,ipadx=5)

        self.text_display = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, font=("Arial", self.text_size)
        )
        self.text_display.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)
        self.text_display.tag_config(
            "last_phrase",
            font=("Arial", self.text_size + 2, "bold", "underline"),
        )

        self.start_button = ttkb.Button(
            root, text="Start", command=self.start_process, bootstyle="success"
        )
        self.start_button.grid(row=3, column=0, columnspan=1, padx=5, pady=5, sticky="ew")

        self.post_process_button = ttkb.Button(
            root, text="Start Post Process", command=self.start_post_processing, bootstyle="primary"
        )
        self.post_process_button.grid(row=3, column=3, padx=5, pady=5, sticky="ew")
        
        
        self.post_process_button = ttkb.Button(
            root, text="Open MD editor", command=self.open_markdown_editor, bootstyle="secondary"
        )
        self.post_process_button.grid(row=3, column=2, padx=5, pady=5, sticky="ew")
        
        self.save_button = ttkb.Button(
            root, text="Save Transcription", command=self.save_transcription, bootstyle="info"
        )
        self.save_button.grid(row=5, column=0, columnspan=4, padx=5, pady=5, sticky="ew")

        # Translation button
        self.translation_enabled = tk.BooleanVar(value=False)

        # activate translation button
        self.toggle_translation_button = ttkb.Button(
            root, text="Activer Traduction", command=self.toggle_translation, bootstyle="outline"
        )
        self.toggle_translation_button.grid(row=3, column=1, columnspan=1, padx=5, pady=5, sticky="ew")

        self.language_var = tk.StringVar(value="auto") 
        self.audio_devices = self.get_audio_devices()
        self.selected_device = tk.StringVar(value=self.audio_devices[0])

        # Process STT
        self.ffmpeg_process = None
        self.stt_process = None
        self.queue = queue.Queue()
        self.running = False

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.drop_event)
        
        # Text zone for transcription
        self.translation_display = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, font=("Arial", self.text_size), height=8
        )
        self.translation_display.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)
        self.translation_display.config(state=tk.DISABLED)

        if not self.translation_enabled.get():
            self.translation_display.grid_remove()

    def get_audio_devices(self):
        """get a list of all devices with ffmpeg."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-list_devices", "true", "-f", "avfoundation", "-i", ""],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
            )
            devices = []
            audio_section = False
            for line in result.stderr.splitlines():
                if "AVFoundation audio devices:" in line:
                    audio_section = True
                    continue
                if "AVFoundation video devices:" in line:
                    audio_section = False
                if audio_section:
                    match = re.search(r"\[(\d+)\]\s+(.*)", line)
                    if match:
                        index = match.group(1)
                        name = match.group(2).strip()
                        devices.append(f"{index} ({name})")
            if not devices:
                return ["0 (Micro par défaut)"]
            return devices
        except Exception as e:
            return [f"Erreur: {e}"]

    def start_process(self):
        """Démarre ffmpeg avec le périphérique sélectionné puis lance STT_live.py."""
        if self.ffmpeg_process is None and self.stt_process is None:
            self.running = True
            self.start_button.config(text="Stop", bootstyle="danger", command=self.stop_process)
            device_index = self.selected_device.get().split(" ")[0]
            language = self.language_var.get()

            self.ffmpeg_process = subprocess.Popen(
                [
                    "ffmpeg",
                    "-f",
                    "avfoundation",
                    "-i",
                    f":{device_index}",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-f",
                    "wav",
                    "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            self.stt_process = subprocess.Popen(
                [
                    "python3",
                    "./src/live/STT_live.py",
                    self.languages[language]
                ],
                stdin=self.ffmpeg_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )

            self.text_display.insert(
                tk.END,
                f"Loading model {os.getenv('AUDIO_MODEL_NAME')} with language({language}) using the device : {self.selected_device.get()}...\n",
            )
            self.text_display.yview(tk.END)

            self.listen_to_stt()

    def listen_to_stt(self):
        """Listen to the STT process and display the transcription."""
        def listen():
            for line in self.stt_process.stdout:
                text = line.strip()
                self.root.after(0, self.display_transcription, text)
        # Starts a new thread for the STT
        threading.Thread(target=listen, daemon=True).start()

    def display_transcription(self, text):
        """Display the transcription in the text display area."""
        self.text_display.insert(tk.END, f"{text}\n")
        self.highlight_last_phrase()
        self.text_display.yview(tk.END)
        threading.Thread(target=self.process_translation, args=(text,), daemon=True).start()
        

    def process_translation(self, text):
        """Process translation in a separate thread."""
        if not self.translation_enabled.get():
            return
        try:
            # Récupère la langue sélectionnée via la variable tkinter
            selected_lang = self.language_translation_var.get()
            # Mapp
            lang_map = {
                "Français": "fr",
                "Anglais": "en",
                "Espagnol": "es",
                "Allemand": "de",
                "Italien": "it",
                "Portugais": "pt"
            }
            target_code = lang_map.get(selected_lang, "fr")  # default value french
            translated_text = translate_text(text, target_code)
            self.root.after(10, self.display_translation, translated_text)
        except Exception as e:
            self.root.after(10, self.display_translation, f"⚠️ Erreur de traduction : {e}")


    def display_translation(self, translation):
        """Display the translation in the translation display area."""
        self.translation_display.config(state=tk.NORMAL)
        self.translation_display.insert(tk.END, f"{translation}\n")
        self.translation_display.yview(tk.END)
        self.translation_display.config(state=tk.DISABLED)


    def stop_process(self):
        """Stop the ffmpeg and STT processes."""
        if self.ffmpeg_process:
            self.running = False
            self.ffmpeg_process.terminate()
            self.ffmpeg_process = None

        if self.stt_process:
            self.stt_process.terminate()
            self.stt_process = None
        
        self.start_button.config(text="Start", bootstyle="success", command=self.start_process)
        self.text_display.insert(tk.END, "🛑 Enregistrement arrêté.\n")
        self.text_display.yview(tk.END)

    def zoom_in(self):
        """Rise the text size."""
        self.text_size += 2
        self.text_display.config(font=("Arial", self.text_size))
        self.text_display.tag_config(
            "last_phrase", font=("Arial", self.text_size + 2, "bold", "underline")
        )

    def zoom_out(self):
        """Reduce the text size."""
        if self.text_size > 8:
            self.text_size -= 2
            self.text_display.config(font=("Arial", self.text_size))
            self.text_display.tag_config(
                "last_phrase", font=("Arial", self.text_size + 2, "bold", "underline")
            )

    def reset_zoom(self):
        """Reset the text size to the default value."""
        self.text_size = 12
        self.text_display.config(font=("Arial", self.text_size))
        self.text_display.tag_config(
            "last_phrase", font=("Arial", self.text_size + 2, "bold", "underline")
        )

    def highlight_last_phrase(self):
        """highlight the last transcribed phrase."""
        self.text_display.tag_remove("last_phrase", "1.0", tk.END)
        last_index = self.text_display.index("end-2c linestart")
        self.text_display.tag_add("last_phrase", last_index, "end-1c")

    def save_transcription(self):
        """saves the transcription to a file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Enregistrer la transcription",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    content = self.text_display.get("1.0", tk.END)
                    file.write(content)
                self.text_display.insert(tk.END, f"Transcription sauvegardée dans {file_path}\n")
            except Exception as e:
                self.text_display.insert(tk.END, f"Erreur lors de la sauvegarde : {e}\n")
            self.text_display.yview(tk.END)

    def start_post_processing(self):
        """open a file picker for post-processing."""
        file_path = filedialog.askopenfilename(
            title="Sélectionnez un fichier pour le post process",
            filetypes=[("All Files", "*.*")]
        )
        if file_path:            
            self.text_display.insert(tk.END, f"Post process lancé pour le fichier : {file_path}\n")
            self.text_display.yview(tk.END)
            self.root.update()

            loading_window = Toplevel(self.root)
            loading_window.title("Processing...")
            loading_window.resizable(False, False)
            loading_window.geometry("300x100")
            
            window_width = loading_window.winfo_width()
            window_height = loading_window.winfo_height()
            screen_width = loading_window.winfo_screenwidth()
            screen_height = loading_window.winfo_screenheight()
            x = (screen_width // 2) - (window_width // 2)
            y = (screen_height // 2) - (window_height // 2)
            loading_window.geometry(f"300x100+{x}+{y}")
                
            label = ttkb.Label(
                loading_window, 
                text="Traitement en cours...\nVeuillez patienter.",
                font=("Arial", 12)
            )
            label.pack(pady=10)

            progress = ttkb.Progressbar(loading_window, orient=tk.HORIZONTAL, mode='indeterminate', length=250)
            progress.pack(pady=5)
            progress.start(10)
            loading_window.update()

            def worker():
                try:
                    result = post_process_graph.process_transcription(file_path)
                    print(result)
                    self.open_markdown_editor(result)
                    self.root.after(0, finish, result, None)
                except Exception as e:
                    self.root.after(0, finish, None, e)

            def finish(result, error):
                progress.stop()
                if error is not None:
                    self.text_display.insert(tk.END, f"Erreur lors du post process : {error}\n")
                else:
                    if result == 0:
                        self.text_display.insert(tk.END, "Post process terminé dans le dossier Output\n")
                    else:
                        self.text_display.insert(tk.END, f"Post process terminé avec le code : {result}\n")
                loading_window.destroy()
                self.text_display.yview(tk.END)

            threading.Thread(target=worker, daemon=True).start()
        else:
            self.text_display.insert(tk.END, "no file selected\n")
            self.text_display.yview(tk.END)
    
    def drop_event(self, event):
        """Treat the dropped file.
        Args:
            event (tkinter event): The event object containing the dropped file path.
        Returns:
            None"""
        files = self.root.tk.splitlist(event.data)
        audio_extensions = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')
        for file_path in files:
            if file_path.lower().endswith(audio_extensions):
                self.open_drag_post_process_window(file_path)
            else:
                self.text_display.insert(tk.END, f"Le fichier {file_path} n'est pas un fichier audio.\n")
        self.text_display.yview(tk.END)
    
    def open_drag_post_process_window(self, file_path):
        """
        Opens a popup window asking the user to select the language for the dragged audio file and then initiates processing with a loading screen.
        Args:
            file_path (str): The path to the dragged audio file.
        Returns:
            None
        """
        languages = {
            "Français": "fr",
            "Anglais": "en",
            "Espagnol": "es",
            "Allemand": "de",
            "Italien": "it",
            "Portugais": "pt",
        }
        file_name = os.path.basename(file_path)
        
        # Popup de sélection de langue
        lang_popup = Toplevel(self.root)
        lang_popup.title("Sélectionnez la langue de l'audio")
        lang_popup.resizable(False, False)
        lang_popup.geometry("300x150")
        lang_popup.update_idletasks()
        
        # center the popup 
        window_width = lang_popup.winfo_width()
        window_height = lang_popup.winfo_height()
        screen_width = lang_popup.winfo_screenwidth()
        screen_height = lang_popup.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        lang_popup.geometry(f"300x150+{x}+{y}")
        
        label = ttkb.Label(lang_popup, text="Sélectionnez la langue de l'audio:", font=("Arial", 12))
        label.pack(pady=10)
        
        selected_lang = tk.StringVar(value="Français")  # Par défaut Français
        combobox = ttk.Combobox(lang_popup, textvariable=selected_lang,
                                values=list(languages.keys()), state="readonly", font=("Arial", 12))
        combobox.pack(pady=5)
        
        def confirm_language():
            # Récupère le code de langue correspondant
            lang_code = languages[selected_lang.get()]
            lang_popup.destroy()
            # Lance le traitement avec la langue sélectionnée
            self.start_drag_processing(file_path, file_name, lang_code)
        
        confirm_button = ttkb.Button(lang_popup, text="Confirmer", command=confirm_language, bootstyle="primary")
        confirm_button.pack(pady=10)
        
        lang_popup.grab_set()  # Rend la popup modale

    def start_drag_processing(self, file_path, file_name, lang_code):
        """
        start the transcription and diarization process for a dragged audio file.
        Args:
            file_path (str): The path to the audio file.
            file_name (str): The name of the audio file.
            lang_code (str): The language code for the audio file.
        Returns:
            None
        """
        self.text_display.insert(tk.END, f"Début du traitement pour le fichier : {file_path}\n")
        self.text_display.yview(tk.END)
        
        loading_window = Toplevel(self.root)
        loading_window.title("Traitement du fichier glissé...")
        loading_window.resizable(False, False)
        loading_window.geometry("300x100")
        loading_window.update_idletasks()
        
        window_width = loading_window.winfo_width()
        window_height = loading_window.winfo_height()
        screen_width = loading_window.winfo_screenwidth()
        screen_height = loading_window.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        loading_window.geometry(f"300x100+{x}+{y}")
        
        label = ttkb.Label(loading_window, text="Traitement en cours...\nVeuillez patienter.", font=("Arial", 12))
        label.pack(pady=10)
        
        progress = ttkb.Progressbar(loading_window, orient=tk.HORIZONTAL, mode='indeterminate', length=250)
        progress.pack(pady=5)
        progress.start(10)
        loading_window.update()
        
        def worker():
            try:
                result = start_transcription_n_diarization(f'{os.getenv("OUTPUT_DIR")}/{file_name}.txt', file_path, lang_code)
                self.load_transcription(result)
                self.root.after(0, finish, result, None)
            except Exception as e:
                self.root.after(0, finish, None, e)
        
        def finish(result, error):
            progress.stop()
            if error is not None:
                self.text_display.insert(tk.END, f"Erreur lors du traitement du fichier : {error}\n")
            else:
                if result == 0:
                    self.text_display.insert(tk.END, f"Traitement du fichier {file_path} terminé.\n")
            loading_window.destroy()
            self.text_display.yview(tk.END)
        
        threading.Thread(target=worker, daemon=True).start()

    
    def load_transcription(self, file_path):
        """Ouvre un fichier et affiche son contenu dans la zone de texte."""
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.text_display.delete("1.0", tk.END) 
                self.text_display.insert(tk.END, content)
                self.text_display.insert(tk.END, "\nTranscription chargée avec succès.\n")
            except Exception as e:
                self.text_display.insert(tk.END, f"Erreur lors de la lecture du fichier : {e}\n")
    
    def open_markdown_editor(self, file_path=""):
        """open a markdown editor window.
        Args:
            file_path (str): The path to the file to be loaded in the editor.
        Returns:
            None
        """
        popup = Toplevel()
        popup.title("Éditeur Markdown Visuel")
        popup.geometry("800x600")
        popup.file_path = file_path

        button_frame = ttkb.Frame(popup)
        button_frame.pack(fill=tk.X, pady=5)

        def load_file():
            path = filedialog.askopenfilename(
                title="Ouvrir fichier Markdown",
                filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
            )
            if path:
                popup.file_path = path
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    editor.delete("1.0", tk.END)
                    editor.insert(tk.END, content)
                    update_preview()
                except Exception as e:
                    editor.insert(tk.END, f"Erreur lors du chargement du fichier : {e}")

        def save_file():
            if popup.file_path:
                path = popup.file_path
            else:
                path = filedialog.asksaveasfilename(
                    title="Sauvegarder fichier Markdown",
                    defaultextension=".md",
                    filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
                )
                if not path:
                    return
                popup.file_path = path

            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(editor.get("1.0", tk.END))
            except Exception as e:
                print(f"Erreur lors de la sauvegarde : {e}")

        def handle_export():
            # ask the user for the output path
            output_path = filedialog.asksaveasfilename(
                title="Enregistrer en tant que fichier Word",
                defaultextension=".docx",
                filetypes=[("Documents Word", "*.docx"), ("Tous les fichiers", "*.*")]
            )
            if not output_path:
                return  
            
            try:
                md_2_docx(popup.file_path, output_path)
            except Exception as e:
                print(f"Erreur lors de la sauvegarde : {e}")

            
        load_button = ttkb.Button(button_frame, text="Charger Fichier", command=load_file, bootstyle="secondary")
        load_button.pack(side=LEFT, padx=5)

        save_button = ttkb.Button(button_frame, text="Sauvegarder", command=save_file, bootstyle="primary")
        save_button.pack(side=LEFT, padx=5)
        
        export_button = ttkb.Button(button_frame, text="exporter en word", command=handle_export, bootstyle="info")
        export_button.pack(side=LEFT, padx=5)

        editor = Text(popup, wrap="word", font=("Arial", 12))
        editor.pack(side=LEFT, fill=BOTH, expand=True, padx=5, pady=5)

        preview = HTMLLabel(popup, html="<h1>Prévisualisation</h1>", background="white", font=("Arial", 12))
        preview.pack(side=RIGHT, fill=BOTH, expand=True, padx=5, pady=5)

        syncing = False

        def update_preview(event=None):
            nonlocal syncing
            try:
                scroll_fraction = preview.yview()[0]
            except Exception:
                scroll_fraction = 0.0
            md_text = editor.get("1.0", tk.END)
            html_content = markdown.markdown(md_text)
            preview.set_html(html_content)
            try:
                preview.yview_moveto(scroll_fraction)
            except Exception:
                pass
            editor.edit_modified(False)

        def on_editor_scroll(event):
            nonlocal syncing
            if syncing:
                return
            syncing = True
            try:
                fraction = editor.yview()[0]
                preview.yview_moveto(fraction)
            except Exception:
                pass
            syncing = False

        def on_preview_scroll(event):
            nonlocal syncing
            if syncing:
                return
            syncing = True
            try:
                fraction = preview.yview()[0]
                editor.yview_moveto(fraction)
            except Exception:
                pass
            syncing = False
        
        def sync_editor_to_preview(event=None):
            nonlocal syncing
            if syncing:
                return
            syncing = True
            try:
                fraction = editor.yview()[0]
                correction_factor = 1.1  
                target_fraction = min(1.0, fraction * correction_factor)
                preview.yview_moveto(target_fraction)
            finally:
                syncing = False

        def sync_preview_to_editor(event=None):
            nonlocal syncing
            if syncing:
                return
            syncing = True
            try:
                fraction = preview.yview()[0]
                correction_factor = 1 / 1.1  
                target_fraction = min(1.0, fraction * correction_factor)
                editor.yview_moveto(target_fraction)
            finally:
                syncing = False

        editor.bind("<MouseWheel>", on_editor_scroll)
        preview.bind("<MouseWheel>", on_preview_scroll)
        editor.bind("<MouseWheel>", sync_editor_to_preview)
        preview.bind("<MouseWheel>", sync_preview_to_editor)
        editor.bind("<KeyRelease>", sync_editor_to_preview)
        preview.bind("<KeyRelease>", sync_preview_to_editor)
        editor.bind("<KeyRelease>", lambda event: on_editor_scroll(event))
        preview.bind("<KeyRelease>", lambda event: on_preview_scroll(event))
        def on_modified(event):
            if editor.edit_modified():
                update_preview()
        editor.bind("<<Modified>>", on_modified)

        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                editor.insert(tk.END, content)
                update_preview()
            except Exception as e:
                editor.insert(tk.END, f"Erreur lors du chargement du fichier : {e}")
    
    def open_translation_window(self):
        """Opens a new window dedicated to live translation output."""
        if hasattr(self, "translation_window") and self.translation_window.winfo_exists():
            return  
        
        self.translation_window = Toplevel(self.root)
        self.translation_window.title("Traduction en Temps Réel")
        self.translation_window.geometry("600x400")

        self.translated_text_display = scrolledtext.ScrolledText(
            self.translation_window, wrap=tk.WORD, font=("Arial", self.text_size)
        )
        self.translated_text_display.pack(fill=BOTH, expand=True, padx=10, pady=10)
    
    def toggle_translation(self):
        """Activates or desactivates display translation zone"""
        if self.translation_enabled.get():
            self.translation_display.grid_remove()
            self.toggle_translation_button.config(text="Activer Traduction")
        else:
            self.translation_display.grid()
            self.toggle_translation_button.config(text="Désactiver Traduction")
        self.translation_enabled.set(not self.translation_enabled.get())

    def translate_text(self, text, index):
        """Translate text and display the result in the translation display area."""
        if not self.translation_enabled.get():
            return
        try:
            lang = self.language_translation_var.get()
            translated_text = translate_text(text, lang)
            # Planifie l'insertion de la traduction dans le thread principal
            self.root.after(0, self.insert_translation, index, translated_text)
        except Exception as e:
            self.root.after(0, self.insert_translation, index, f"⚠️ Erreur de traduction : {e}")

    
    def open_settings(self):
        """Open settings window."""
        settings_window = Toplevel(self.root)
        settings_window.title("Réglages")
        settings_window.geometry("500x400")
        settings_window.update_idletasks()
        window_width = settings_window.winfo_width()
        window_height = settings_window.winfo_height()
        screen_width = settings_window.winfo_screenwidth()
        screen_height = settings_window.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        settings_window.geometry(f"500x400+{x}+{y}")

        ttkb.Label(settings_window, text="Taille du texte:", font=("Arial", 12)).pack(pady=5)
        font_size_slider = ttkb.Scale(settings_window, from_=8, to=30, orient="horizontal", command=self.update_font_size)
        font_size_slider.set(self.text_size)
        font_size_slider.pack(pady=5)

        ttkb.Label(settings_window, text="Couleur de fond:", font=("Arial", 12)).pack(pady=5)
        self.bg_color_var = tk.StringVar(value=self.root["bg"])
        bg_color_selector = ttk.Combobox(
            settings_window, textvariable=self.initial_theme, values= self.themes,
            state="readonly"
        )
        bg_color_selector.pack(pady=5)
        
        ttkb.Label(settings_window, text="Audio Input :", font=("Arial", 12)).pack(pady=5)
        audio_selector = ttk.Combobox(
            settings_window,
            textvariable=self.selected_device,
            values=self.audio_devices,
            state="readonly",
        )
        audio_selector.pack(pady=5)
        

        ttkb.Label(settings_window, text="Sélection de la langue de l'audio :", font=("Arial", 12)).pack(pady=5)
        language_selector = ttk.Combobox(
            settings_window,
            textvariable=self.language_var,
            values=list(self.languages.keys()),
            state="readonly",
        )
        language_selector.pack(pady=5)
        
        ttkb.Label(settings_window, text="Traduction en : ", font=("Arial", 12)).pack(pady=5)
        translation_selector = ttk.Combobox(
            settings_window,
            textvariable=self.language_translation_var,
            values=["Français", "Anglais", "Espagnol", "Allemand", "Italien", "Portugais"],
            state="readonly",
            )
        translation_selector.bind("<<ComboboxSelected>>", self.on_translation_language_change)
        translation_selector.pack(pady=5)
        
        apply_button = ttkb.Button(settings_window, text="Appliquer", command=lambda: self.apply_settings(bg_color_selector.get()), bootstyle="primary")
        apply_button.pack(pady=20)
    
    def on_translation_language_change(self, event):
        """Handles the event when the translation language is changed."""
        self.translation_display.insert(tk.END, f"Traduction en {self.language_translation_var.get()}\n")
    
    def update_font_size(self, new_size):
        """update the text size in the transcription and translation display areas."""
        self.text_size = int(float(new_size))
        self.text_display.config(font=("Arial", self.text_size))
        self.translation_display.config(font=("Arial", self.text_size))
        self.text_display.tag_config("last_phrase", font=("Arial", self.text_size + 2, "bold", "underline"))

    def apply_settings(self, new_theme):
        """Apply the selected UI theme to the interface."""
        self.style = ttkb.Style(theme=new_theme)

def run():
    """
    Initializes and starts the Speech-to-Text interface application.

    This function creates the main application window using TkinterDnD,
    instantiates the STTInterface class, and starts the main event loop.
    """
    root = TkinterDnD.Tk()
    app = STTInterface(root)
    root.mainloop()


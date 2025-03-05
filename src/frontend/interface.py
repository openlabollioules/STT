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

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services import start_post_process, md_2_docx
from core import translate_text
from diarization import start_transcription_n_diarization
from graph import post_process_graph


class STTInterface:
    """
    This class is for the STT interface
    """
    def __init__(self, root):
        self.themes = ["flatly", "cosmo", "minty" ,"darkly", "cyborg", "superhero"]
        self.initial_theme=tk.StringVar(value=self.themes[-1])
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
        
        # Appliquer le thème ttkbootstrap
        self.style = ttkb.Style(theme=self.themes[-1])


        # Rendre la grille responsive
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Taille de la police
        self.text_size = 12

        # Bouton engrenage ⚙️ pour les réglages
        self.settings_button = ttkb.Button(
            root, text="⚙️", command=self.open_settings, bootstyle="secondary"
        )
        self.settings_button.grid(row=0, column=5, sticky="nw", padx=5, pady=5)

        self.text_display = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, font=("Arial", self.text_size)
        )
        self.text_display.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)
        self.text_display.tag_config(
            "last_phrase",
            foreground="white",
            font=("Arial", self.text_size + 2, "bold", "underline"),
        )

        self.start_button = ttkb.Button(
            root, text="Start", command=self.start_process, bootstyle="success"
        )
        self.start_button.grid(row=3, column=0, columnspan=1, padx=5, pady=5, sticky="ew")

        self.post_process_button = ttkb.Button(
            root, text="Start Post Process", command=self.start_post_processing, bootstyle="primary"
        )
        self.post_process_button.grid(row=3, column=2, padx=5, pady=5, sticky="ew")

        self.save_button = ttkb.Button(
            root, text="Save Transcription", command=self.save_transcription, bootstyle="info"
        )
        self.save_button.grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        # Variable pour activer/désactiver la traduction
        self.translation_enabled = tk.BooleanVar(value=False)

        # Bouton Activer/Désactiver la Traduction
        self.toggle_translation_button = ttkb.Button(
            root, text="Activer Traduction", command=self.toggle_translation, bootstyle="outline"
        )
        self.toggle_translation_button.grid(row=3, column=1, columnspan=1, padx=5, pady=5, sticky="ew")

        self.language_var = tk.StringVar(value="fr")  # valeur par défaut : français
        self.audio_devices = self.get_audio_devices()
        self.selected_device = tk.StringVar(value=self.audio_devices[0])

        # Processus STT
        self.ffmpeg_process = None
        self.stt_process = None
        self.queue = queue.Queue()
        self.running = False

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.drop_event)
        
        # Zone d'affichage pour la traduction
        self.translation_display = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, font=("Arial", self.text_size), height=8
        )
        self.translation_display.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)
        self.translation_display.insert(tk.END, "🟡 Traduction en temps réel s'affichera ici...\n")
        self.translation_display.config(state=tk.DISABLED)  # Empêcher l'édition manuelle

        if not self.translation_enabled.get():
            self.translation_display.grid_remove()

    def get_audio_devices(self):
        """Récupère la liste des périphériques audio disponibles avec ffmpeg."""
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
                ],
                stdin=self.ffmpeg_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )

            self.text_display.insert(
                tk.END,
                f"🔴 Enregistrement en cours ({language}) avec l'entrée {self.selected_device.get()}...\n",
            )
            self.text_display.yview(tk.END)

            self.listen_to_stt()

    def listen_to_stt(self):
        """Écoute les messages de STT en temps réel et traduit en parallèle."""
        def listen():
            while self.running:
                try:
                    for line in self.stt_process.stdout:
                        text = line.strip()
                        self.queue.put(text)
                        threading.Thread(target=self.translate_text, args=(text,), daemon=True).start()
                except Exception as e:
                    self.queue.put(f"Erreur : {e}")

        threading.Thread(target=listen, daemon=True).start()
        self.root.after(100, self.update_text_display)

    def update_text_display(self):
        """Met à jour l'affichage du texte transcrit et traduit."""
        while not self.queue.empty():
            message = self.queue.get()
            if isinstance(message, tuple) and message[0] == "translated":
                translated_text = message[1]
                self.translation_display.config(state=tk.NORMAL)
                self.translation_display.insert(tk.END, f"{translated_text}\n")
                self.translation_display.yview(tk.END)
                self.translation_display.config(state=tk.DISABLED)
            else:
                self.text_display.insert(tk.END, f"{message}\n")
                self.highlight_last_phrase()
                self.text_display.yview(tk.END)

        if self.running:
            self.root.after(100, self.update_text_display)

    def stop_process(self):
        """Arrête les processus ffmpeg et STT."""
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
        """Augmente la taille du texte."""
        self.text_size += 2
        self.text_display.config(font=("Arial", self.text_size))
        self.text_display.tag_config(
            "last_phrase", font=("Arial", self.text_size + 2, "bold", "underline")
        )

    def zoom_out(self):
        """Diminue la taille du texte."""
        if self.text_size > 8:
            self.text_size -= 2
            self.text_display.config(font=("Arial", self.text_size))
            self.text_display.tag_config(
                "last_phrase", font=("Arial", self.text_size + 2, "bold", "underline")
            )

    def reset_zoom(self):
        """Réinitialise la taille du texte."""
        self.text_size = 12
        self.text_display.config(font=("Arial", self.text_size))
        self.text_display.tag_config(
            "last_phrase", font=("Arial", self.text_size + 2, "bold", "underline")
        )

    def highlight_last_phrase(self):
        """Met en surbrillance la dernière ligne en blanc et en gras."""
        self.text_display.tag_remove("last_phrase", "1.0", tk.END)
        last_index = self.text_display.index("end-2c linestart")
        self.text_display.tag_add("last_phrase", last_index, "end-1c")

    def save_transcription(self):
        """Sauvegarde le contenu de la zone de texte dans un fichier TXT."""
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
        """Ouvre l'explorateur de fichiers pour sélectionner un fichier puis lance le post process."""
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
        """Gère le drag & drop."""
        files = self.root.tk.splitlist(event.data)
        audio_extensions = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')
        for file_path in files:
            if file_path.lower().endswith(audio_extensions):
                self.open_drag_post_process_window(file_path)
            else:
                self.text_display.insert(tk.END, f"Le fichier {file_path} n'est pas un fichier audio.\n")
        self.text_display.yview(tk.END)
    
    def open_drag_post_process_window(self, file_path):
        """Ouvre une nouvelle fenêtre avec une barre de chargement pour le fichier glissé."""
        file_name = os.path.basename(file_path)
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
                result = start_transcription_n_diarization('./testttttt.txt', file_path)
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
    
    def open_markdown_editor(self, file_path):
        """
        Ouvre un éditeur Markdown visuel dans une fenêtre pop-up.
        Si un chemin vers un fichier Markdown est fourni, le fichier est chargé.
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
                md_2_docx(file_path, path)
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
        """Ouvre une nouvelle fenêtre pour afficher la traduction en temps réel."""
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
        """Active ou désactive l'affichage de la zone de traduction."""
        if self.translation_enabled.get():
            self.translation_display.grid_remove()
            self.toggle_translation_button.config(text="Activer Traduction")
        else:
            self.translation_display.grid()
            self.toggle_translation_button.config(text="Désactiver Traduction")
        self.translation_enabled.set(not self.translation_enabled.get())

    def translate_text(self, text):
        """Traduit le texte transcrit en arrière-plan et met à jour l'interface."""
        if not self.translation_enabled.get():
            return
        try:
            translated_text = translate_text(text)
            self.queue.put(("translated", translated_text))
        except Exception as e:
            self.queue.put(("translated", f"⚠️ Erreur de traduction : {e}"))
    
    def open_settings(self):
        """Ouvre la fenêtre des réglages."""
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
        
        languages = {
            "Français": "fr",
            "Anglais": "en",
            "Espagnol": "es",
            "Allemand": "de",
            "Italien": "it",
            "Portugais": "pt",
        }
        ttkb.Label(settings_window, text="Sélection de la langue de l'audio :", font=("Arial", 12)).pack(pady=5)
        language_selector = ttk.Combobox(
            settings_window,
            textvariable=self.language_var,
            values=list(languages.keys()),
            state="readonly",
        )
        language_selector.pack(pady=5)
        
        apply_button = ttkb.Button(settings_window, text="Appliquer", command=lambda: self.apply_settings(bg_color_selector.get()), bootstyle="primary")
        apply_button.pack(pady=20)
    
    def update_font_size(self, new_size):
        """Met à jour la taille de la police dans les zones de texte."""
        self.text_size = int(float(new_size))
        self.text_display.config(font=("Arial", self.text_size))
        self.translation_display.config(font=("Arial", self.text_size))
        self.text_display.tag_config("last_phrase", font=("Arial", self.text_size + 2, "bold", "underline"))

    def apply_settings(self, new_theme):
        """Applique les changements de couleur de fond."""
        self.style = ttkb.Style(theme=new_theme)

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = STTInterface(root)
    root.mainloop()

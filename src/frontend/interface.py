import sys
import os
import queue
import re
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog, Toplevel, Text, BOTH, LEFT,RIGHT, filedialog, Button, Frame
from tkinterdnd2 import DND_FILES, TkinterDnD
import markdown
from tkhtmlview import HTMLLabel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services import start_post_process,md_2_docx
from diarization import start_transcription_n_diarization
from graph import post_process_graph


class STTInterface:
    def __init__(self, root):
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

        # Rendre la grille responsive : la ligne 0 (avec le texte) occupe tout l'espace
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Taille du texte (par défaut)
        self.text_size = 12

        # ------------------ Ligne 0 : Zone de texte ------------------
        self.text_display = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, font=("Arial", self.text_size)
        )
        self.text_display.grid(
            row=0, column=0, columnspan=4, sticky="nsew", padx=10, pady=10
        )

        # Configuration de la mise en évidence
        self.text_display.tag_config(
            "last_phrase",
            foreground="white",
            font=("Arial", self.text_size + 2, "bold", "underline"),
        )

        # ------------------ Ligne 1 : Start, Stop, Post Process, Save ------------------
        self.start_button = tk.Button(
            root,
            text="Start",
            command=self.start_process,
            bg="white",
            fg="green",
            font=("Arial", 12),
        )
        self.start_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.stop_button = tk.Button(
            root,
            text="Stop",
            command=self.stop_process,
            bg="white",
            fg="red",
            font=("Arial", 12),
        )
        self.stop_button.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.post_process_button = tk.Button(
            root,
            text="Start Post Process",
            command=self.start_post_processing,
            font=("Arial", 12),
        )
        self.post_process_button.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

        self.save_button = tk.Button(
            root,
            text="Save Transcription",
            command=self.save_transcription,
            font=("Arial", 12),
        )
        self.save_button.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # ------------------ Ligne 2 : Zoom +, Zoom -, Reset Zoom ------------------
        self.zoom_in_button = tk.Button(
            root, text="Zoom +", command=self.zoom_in, font=("Arial", 12)
        )
        self.zoom_in_button.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        self.zoom_out_button = tk.Button(
            root, text="Zoom -", command=self.zoom_out, font=("Arial", 12)
        )
        self.zoom_out_button.grid(row=2,column=1, padx=5, pady=5, sticky="ew")

        self.reset_zoom_button = tk.Button(
            root, text="Reset Zoom", command=self.reset_zoom, font=("Arial", 12)
        )
        self.reset_zoom_button.grid(row=2, column=2, padx=5, pady=5, sticky="ew")

        # ------------------ Ligne 3 : Mode, Langue, Audio ------------------
        # Variables pour les combobox
        self.mode_var = tk.StringVar(value="Transcribe")  # Par défaut, Transcribe
        self.language_var = tk.StringVar(value="fr")       # Par défaut, français
        self.audio_devices = self.get_audio_devices()
        self.selected_device = tk.StringVar(value=self.audio_devices[0])

        # Combobox du mode (Transcribe/Translate)
        self.mode_selector = ttk.Combobox(
            root,
            textvariable=self.mode_var,
            values=["Transcribe", "Translate"],
            state="readonly",
        )
        self.mode_selector.grid(row=3, column=0, padx=5, pady=5, sticky="ew")

        # Combobox de la langue
        languages = {
            "Français": "fr",
            "Anglais": "en",
            "Espagnol": "es",
            "Allemand": "de",
            "Italien": "it",
            "Portugais": "pt",
        }
        self.language_selector = ttk.Combobox(
            root,
            textvariable=self.language_var,
            values=list(languages.values()),
            state="readonly",
        )
        self.language_selector.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Combobox de l'entrée audio
        self.audio_selector = ttk.Combobox(
            root,
            textvariable=self.selected_device,
            values=self.audio_devices,
            state="readonly",
        )
        self.audio_selector.grid(row=3, column=2, padx=5, pady=5, sticky="ew")

        # Processus STT
        self.ffmpeg_process = None
        self.stt_process = None
        self.queue = queue.Queue()
        self.running = False

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.drop_event)

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
        """Démarre ffmpeg avec l'entrée sélectionnée et envoie le flux à STT_live.py."""
        if self.ffmpeg_process is None and self.stt_process is None:
            self.running = True

            device_index = self.selected_device.get().split(" ")[0]
            mode = "transcribe" if self.mode_var.get() == "Transcribe" else "translate"
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
                    mode,
                ],
                stdin=self.ffmpeg_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )

            self.text_display.insert(
                tk.END,
                f"🔴 Enregistrement en cours ({mode.capitalize()} - {language}) avec l'entrée {self.selected_device.get()}...\n",
            )
            self.text_display.yview(tk.END)

            self.listen_to_stt()

    def listen_to_stt(self):
        """Écoute les messages de STT_live.py et met à jour l'affichage."""
        def listen():
            while self.running:
                try:
                    for line in self.stt_process.stdout:
                        self.queue.put(line.strip())
                except Exception as e:
                    self.queue.put(f"Erreur : {e}")

        threading.Thread(target=listen, daemon=True).start()
        self.root.after(100, self.update_text_display)

    def update_text_display(self):
        """Mise à jour de la zone de texte avec les messages reçus."""
        while not self.queue.empty():
            message = self.queue.get()
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
        """Open the file explorer to select files than start post process"""
        file_path = filedialog.askopenfilename(
            title="Sélectionnez un fichier pour le post process",
            filetypes=[("All Files", "*.*")]
        )
        if file_path:            
            self.text_display.insert(tk.END, f"Post process lancé pour le fichier : {file_path}\n")
            self.text_display.yview(tk.END)
            self.root.update()

            loading_window = tk.Toplevel(self.root)
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
                
            label = tk.Label(
                loading_window, 
                text="Traitement en cours...\nVeuillez patienter.",
                font=("Arial", 12)
            )
            label.pack(pady=10)

            progress = ttk.Progressbar(loading_window, orient=tk.HORIZONTAL, mode='indeterminate', length=250)
            progress.pack(pady=5)
            progress.start(10)  # L'intervalle (ms) entre chaque mouvement de la barre
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
                progress.stop()  # Arrête la barre d'avancement
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
        """Handles the drag and drop"""
        files = self.root.tk.splitlist(event.data)
        audio_extensions = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')
        for file_path in files:
            if file_path.lower().endswith(audio_extensions):
                self.open_drag_post_process_window(file_path)
            else:
                self.text_display.insert(tk.END, f"Le fichier {file_path} n'est pas un fichier audio.\n")
        self.text_display.yview(tk.END)
    
    def open_drag_post_process_window(self, file_path):
        """Open a new windows with a loading bar"""
        file_name = os.path.basename(file_path)
        self.text_display.insert(tk.END, f"Début du traitement pour le fichier : {file_path}\n")
        self.text_display.yview(tk.END)

        # Création de la fenêtre de chargement
        loading_window = tk.Toplevel(self.root)
        loading_window.title("Traitement du fichier glissé...")
        loading_window.resizable(False, False)
        
        loading_window.geometry("300x100")
        loading_window.update_idletasks()  # Assure que la fenêtre est bien dimensionnée

        # Calculer la position pour centrer la fenêtre
        window_width = loading_window.winfo_width()
        window_height = loading_window.winfo_height()
        screen_width = loading_window.winfo_screenwidth()
        screen_height = loading_window.winfo_screenheight()

        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        loading_window.geometry(f"300x100+{x}+{y}")
        
        label = tk.Label(loading_window, text="Traitement en cours...\nVeuillez patienter.", font=("Arial", 12))
        label.pack(pady=10)
        
        progress = ttk.Progressbar(loading_window, orient=tk.HORIZONTAL, mode='indeterminate', length=250)
        progress.pack(pady=5)
        progress.start(10)
        loading_window.update()

        def worker():
            try:
                result = start_transcription_n_diarization('./testttttt.txt',file_path)
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
    
    def load_transcription(self,file_path):
        """Open a file and display his content inse the text zone"""
 
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
        
        # On stocke le chemin du fichier dans la fenêtre (attribut custom)
        popup.file_path = file_path

        # Créer un cadre en haut pour les boutons "Charger" et "Sauvegarder"
        button_frame = Frame(popup)
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
            # Utilise le chemin existant, sinon demande où sauvegarder
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
            # Utilise le chemin existant, sinon demande où sauvegarder
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
                md_2_docx(file_path,path)
            except Exception as e:
                print(f"Erreur lors de la sauvegarde : {e}")
            

        # Bouton pour charger un fichier Markdown
        load_button = Button(button_frame, text="Charger Fichier", command=load_file)
        load_button.pack(side=LEFT, padx=5)

        # Bouton pour sauvegarder les modifications
        save_button = Button(button_frame, text="Sauvegarder", command=save_file)
        save_button.pack(side=LEFT, padx=5)
        
        save_button = Button(button_frame, text="exporter en word", command=handle_export)
        save_button.pack(side=LEFT, padx=5)

        # Zone d'édition Markdown
        editor = Text(popup, wrap="word", font=("Arial", 12))
        editor.pack(side=LEFT, fill=BOTH, expand=True, padx=5, pady=5)

        # Zone de prévisualisation HTML
        preview = HTMLLabel(popup, html="<h1>Prévisualisation</h1>", background="white", font=("Arial", 12))
        preview.pack(side=RIGHT, fill=BOTH, expand=True, padx=5, pady=5)

        # Variable de synchronisation pour éviter les appels récursifs
        syncing = False

        # Fonction qui met à jour la prévisualisation en convertissant le Markdown en HTML
        def update_preview(event=None):
            nonlocal syncing
            # Sauvegarde de la position de défilement du widget preview
            try:
                scroll_fraction = preview.yview()[0]
            except Exception:
                scroll_fraction = 0.0
            # Conversion du Markdown en HTML
            md_text = editor.get("1.0", tk.END)
            html_content = markdown.markdown(md_text)
            # On met à jour le HTML puis on restaure la position de scroll
            preview.set_html(html_content)
            try:
                preview.yview_moveto(scroll_fraction)
            except Exception:
                pass
            editor.edit_modified(False)

        # Synchronisation du scroll de l'éditeur vers la prévisualisation
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

        # Synchronisation du scroll de la prévisualisation vers l'éditeur
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
                # Récupère la fraction de défilement de l'éditeur
                fraction = editor.yview()[0]
                # Applique un facteur de correction (à ajuster selon vos tests)
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
                # Inverse le facteur de correction (approximativement)
                correction_factor = 1 / 1.1  
                target_fraction = min(1.0, fraction * correction_factor)
                editor.yview_moveto(target_fraction)
            finally:
                syncing = False


        # Lier les événements de défilement à la molette de la souris
        editor.bind("<MouseWheel>", on_editor_scroll)
        preview.bind("<MouseWheel>", on_preview_scroll)
        editor.bind("<MouseWheel>", sync_editor_to_preview)
        preview.bind("<MouseWheel>", sync_preview_to_editor)
        # Et éventuellement sur d'autres événements de défilement (flèches, KeyRelease, etc.)
        editor.bind("<KeyRelease>", sync_editor_to_preview)
        preview.bind("<KeyRelease>", sync_preview_to_editor)

        
        # Optionnel : lier également les flèches et la barre d'espace, etc.
        editor.bind("<KeyRelease>", lambda event: on_editor_scroll(event))
        preview.bind("<KeyRelease>", lambda event: on_preview_scroll(event))

        # Lier l'événement de modification pour mettre à jour la prévisualisation
        def on_modified(event):
            if editor.edit_modified():
                update_preview()
        editor.bind("<<Modified>>", on_modified)

        # Si un chemin de fichier a été passé en paramètre, charge son contenu
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                editor.insert(tk.END, content)
                update_preview()
            except Exception as e:
                editor.insert(tk.END, f"Erreur lors du chargement du fichier : {e}")


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = STTInterface(root)
    root.mainloop()

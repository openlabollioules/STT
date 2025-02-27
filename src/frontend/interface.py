import sys
import os
import queue
import re
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog

# Assurez-vous que votre fichier post_process.py (ou services.py) est dans le bon répertoire
# Ici, on suppose que la fonction start_post_process est importée depuis services.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services import start_post_process


class STTInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("STT Interface")
        self.root.geometry("700x550")
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
                self.text_display.insert(tk.END, f"💾 Transcription sauvegardée dans {file_path}\n")
            except Exception as e:
                self.text_display.insert(tk.END, f"Erreur lors de la sauvegarde : {e}\n")
            self.text_display.yview(tk.END)

    def start_post_processing(self):
        """Ouvre l'explorateur de fichiers pour sélectionner un fichier et lance le post process dans un thread séparé avec une barre d'avancement."""
        file_path = filedialog.askopenfilename(
            title="Sélectionnez un fichier pour le post process",
            filetypes=[("All Files", "*.*")]
        )
        if file_path:
            import os
            file_name = os.path.basename(file_path)
            write_in_file_auto_correction = True
            deepseek = True

            self.text_display.insert(tk.END, f"Post process lancé pour le fichier : {file_path}\n")
            self.text_display.yview(tk.END)
            self.root.update()

            # Création d'une fenêtre de chargement
            loading_window = tk.Toplevel(self.root)
            loading_window.title("Processing...")
            loading_window.resizable(False, False)
            loading_window.geometry("300x100")
            
            # Label de chargement
            label = tk.Label(
                loading_window, 
                text="Traitement en cours...\nVeuillez patienter.",
                font=("Arial", 12)
            )
            label.pack(pady=10)

            # Barre d'avancement en mode indéterminé
            progress = ttk.Progressbar(loading_window, orient=tk.HORIZONTAL, mode='indeterminate', length=250)
            progress.pack(pady=5)
            progress.start(10)  # L'intervalle (ms) entre chaque mouvement de la barre
            loading_window.update()

            # Fonction worker exécutée dans un thread séparé
            def worker():
                try:
                    result = start_post_process(write_in_file_auto_correction, file_path, file_name, deepseek)
                    self.root.after(0, finish, result, None)
                except Exception as e:
                    self.root.after(0, finish, None, e)

            # Fonction appelée dans le thread principal une fois le traitement terminé
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

            # Démarrage du post process dans un thread séparé
            threading.Thread(target=worker, daemon=True).start()

        else:
            self.text_display.insert(tk.END, "Aucun fichier sélectionné.\n")
            self.text_display.yview(tk.END)





if __name__ == "__main__":
    root = tk.Tk()
    app = STTInterface(root)
    root.mainloop()

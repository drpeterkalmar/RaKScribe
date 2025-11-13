## RaKScribe - Version 0.9 
# Hybrid Streaming Diktat und Structured Reporting (Google STT + OpenAI GPT-4o Strukturierung)
# Kopiert fertigen Befund direkt im HTML Format in die Zwischenablage zB für Word

import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import threading
import os
import time
import pyperclip
import markdown
import re 

import win32clipboard

# --- Google Cloud & OpenAI Konfiguration ---
from google.cloud import speech
from google.oauth2 import service_account
from openai import OpenAI
import configparser

config = configparser.ConfigParser()

try:
    # Laden der Schlüssel aus config.ini
    config.read('config.ini')
    OPENAI_API_KEY = config['API_KEYS']['OPENAI_API_KEY'].strip()
    GOOGLE_JSON_FILENAME = config['API_KEYS']['GOOGLE_JSON_FILENAME'].strip().replace('"', '')
except KeyError:
    print("FEHLER: Konfigurationsdatei (config.ini) ist unvollständig oder fehlt. Bitte prüfen Sie die Schlüssel im Abschnitt [API_KEYS].")
    exit()

# Definiert den Pfad zum JSON-Schlüssel relativ zum Skript-Standort.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, GOOGLE_JSON_FILENAME)

# Globale Definition der Clients
speech_client = None
openai_client = None

# Initialisierung der Clients
try:
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
    speech_client = speech.SpeechClient(credentials=credentials)
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    print(f"Fehler bei Initialisierung der Clients. JSON-Pfad, Keys oder Guthaben prüfen: {e}")
    speech_client = None
    openai_client = None


# Audio Konfiguration für Google Streaming
GOOGLE_CONFIG = speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=16000, 
    language_code="de-DE",
    model="default", 
    use_enhanced=True
)
STREAMING_CONFIG = speech.StreamingRecognitionConfig(
    config=GOOGLE_CONFIG,
    interim_results=True 
)


def load_prompt_template(filename="radiology_prompt.txt"):
    """Lädt den Inhalt der Prompt-Datei."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, filename)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        messagebox.showerror("Fehler", f"Die Prompt-Datei '{filename}' wurde nicht gefunden. Bitte prüfen Sie den Ordner.")
        return ""
    except Exception as e:
        messagebox.showerror("Fehler", f"Fehler beim Laden der Prompt-Datei: {e}")
        return ""

INITIAL_PROMPT_CONTENT = load_prompt_template()


# --- Hauptanwendungsklasse ---

class GigaScribeApp:
    def __init__(self, master):
        self.master = master
        master.title("RaKScribe 0.9 - Fast Online Dictation and Hybrid Structured Reporting")
        
        self.samplerate = 16000 
        self.is_recording = False
        self.frames = []
        self.stream = None
        self.final_transcript = ""
        self.thread = None 

        try:
            default_input_device = sd.query_devices(kind='input')
            self.device_info_name = default_input_device['name']
        except Exception:
            self.device_info_name = "Nicht gefunden (Prüfen Sie Mikrofon)"
        
        self.create_widgets()

    def create_widgets(self):
        # --- FRAME: Haupt-Frame für Grid Layout ---
        main_frame = tk.Frame(self.master, padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)
        
        # --- Größenverstellbarkeit konfigurieren ---
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)  
        self.master.rowconfigure(0, weight=1)

        # --- A) Status & Buttons ---
        self.status_label = ttk.Label(main_frame, 
                                      text="Status: Bereit", 
                                      style="Success.TLabel", # Startstil
                                      font=('Tahoma', 12, 'bold'))
        self.status_label.grid(row=0, column=0, sticky='w', pady=5)
        
        self.record_button = ttk.Button(main_frame, text="Diktat Start / Stopp", command=self.toggle_recording, 
                                       bootstyle=(DANGER, OUTLINE), 
                                       width=20) 
        self.record_button.grid(row=0, column=1, sticky='e', pady=5)
        
        self.copy_button = ttk.Button(main_frame, text="Fertigen Befund kopieren (WORD-Formatierung)", command=self.copy_formatted_report, 
                                       bootstyle=(PRIMARY, OUTLINE))
        self.copy_button.grid(row=5, column=0, columnspan=2, sticky='ew', pady=5)

        # --- B) Audiopegel Visualisierung ---
        ttk.Label(main_frame, text="Mikrofonpegel:").grid(row=1, column=0, sticky='w', pady=5)
        ttk.Label(main_frame, text=f"Gerät: {self.device_info_name}").grid(row=1, column=1, sticky='e', pady=5)

        self.level_canvas = tk.Canvas(main_frame, width=200, height=20, bg='lightgray')
        self.level_canvas.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        self.level_rect = self.level_canvas.create_rectangle(0, 0, 0, 20, fill='darkgreen')
        
        # --- C) Prompt/Vorlage und D) Ergebnis-Ausgabe Container (Panedwindow) ---
        self.paned_window = ttk.Panedwindow(main_frame, orient=HORIZONTAL)
        self.paned_window.grid(row=4, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)

        # 2. PROMPT-FRAME (Linke Seite)
        prompt_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(prompt_frame, weight=1) 
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(1, weight=1)

        ttk.Label(prompt_frame, text="Radiologie Prompt/Vorlage (GPT-4o Anweisung):").grid(row=0, column=0, sticky='w', pady=5)
        
        self.prompt_text = tk.Text(prompt_frame, height=10, width=45)
        self.prompt_text.grid(row=1, column=0, sticky='nsew', padx=0, pady=0) 
        
        if INITIAL_PROMPT_CONTENT:
            self.prompt_text.insert(tk.END, INITIAL_PROMPT_CONTENT)
        else:
            self.prompt_text.insert(tk.END, "FEHLER: PROMPT-INHALT KONNTE NICHT GELADEN WERDEN.")

        # 3. ERGEBNIS-FRAME (Rechte Seite)
        result_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(result_frame, weight=1) 
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(1, weight=1)

        ttk.Label(result_frame, text="Strukturierter Befund (GPT-4o Output):").grid(row=0, column=0, sticky='w', pady=5)
        
        self.result_text = tk.Text(result_frame, height=10, width=45, bg=self.master.style.colors.inputbg)
        self.result_text.grid(row=1, column=0, sticky='nsew', padx=0, pady=0)


    # --- Diktat-Logik (Threading und Streaming) ---

    def toggle_recording(self):
        if not speech_client or not openai_client:
            messagebox.showerror("Fehler", "API-Clients nicht initialisiert. Prüfen Sie Konfiguration und Schlüssel.")
            return

        if not self.is_recording:
            # --- START AUFNAHME ---
            self.frames = []
            self.final_transcript = ""  
            self.is_recording = True
            
            # KORRIGIERT: Status-Änderung über Style
            self.status_label.config(text="Status: AUFNAHME LÄUFT... (Rot)", style="Danger.TLabel")
            self.record_button.config(text="Diktat Stoppen")
            
            self.thread = threading.Thread(target=self.record)
            self.thread.start()
            
        else:
            # --- AUFNAHME STOPPEN & SYNCHRONE VERARBEITUNG STARTEN ---
            
            # 1. ZUERST: Recording-Flag deaktivieren und Streams schließen
            self.is_recording = False 
            
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            # 2. Status und Button aktualisieren (Feedback an Nutzer)
            self.status_label.config(text="Status: Warten auf Finale Daten...", style="Warning.TLabel")
            self.record_button.config(text="Verarbeitung läuft...", state=tk.DISABLED)
            
            # 3. WICHTIG: Starte die asynchrone Warte- und Verarbeitungslogik
            self.master.after(100, self.check_thread_and_process)

    def check_thread_and_process(self):
        if self.thread and self.thread.is_alive():
            self.master.after(100, self.check_thread_and_process)
        else:
            # Der Thread ist beendet -> Starte die Verarbeitung in einem NEUEN THREAD
            process_thread = threading.Thread(target=self.process_dictation)
            process_thread.start()


    # --- Hilfsmethoden für Audio/Level ---

    def update_level_bar(self, rms_value):
        # Sicherheits-Check für NaN-Werte
        if np.isnan(rms_value) or rms_value is None:
            rms_value = 0
            
        max_val = 1500 # Empfindlichkeit
        level = rms_value / max_val
        
        bar_width = min(int(level * 200), 200)
        
        self.level_canvas.coords(self.level_rect, 0, 0, bar_width, 20)
        
        if level > 0.8:
            fill_color = 'red'
        elif level > 0.4:
            fill_color = 'orange'
        else:
            fill_color = 'darkgreen'
        
        self.level_canvas.itemconfig(self.level_rect, fill=fill_color)
        
    def update_interim_text(self, transcript, is_final):
        # Aktualisiert das Textfeld in Echtzeit
        if not is_final:
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, self.final_transcript + " [DIKTIERE: " + transcript + "]")
        
        if is_final:
            self.final_transcript += transcript + " "
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, self.final_transcript.strip())

    def google_streaming_generator(self):
        while self.is_recording:
            if self.frames:
                chunk = np.concatenate(self.frames, axis=0).tobytes()
                self.frames = []
                yield speech.StreamingRecognizeRequest(audio_content=chunk)
            else:
                time.sleep(0.02) 

    def record(self):
        # Callback-Funktion für sounddevice
        def callback(indata, frames, time, status):
            if status:
                print(status)
            if self.is_recording:
                self.frames.append(indata.copy())
                # Pegel-Berechnung und Update (Thread-Safe)
                rms = np.sqrt(np.mean(indata.astype(np.float64)**2))
                self.master.after(0, self.update_level_bar, rms) 

        # Startet den Audiostream
        try:
            self.stream = sd.InputStream(samplerate=self.samplerate, channels=1, dtype='int16', callback=callback)
            with self.stream:
                requests = self.google_streaming_generator()
                
                # Bidirektionaler Stream zu Google
                responses = speech_client.streaming_recognize(
                    requests=requests,
                    config=STREAMING_CONFIG,
                )
                
                # Verarbeite die Antworten in Echtzeit
                for response in responses:
                    if not response.results: continue
                    result = response.results[0]
                    if not result.alternatives: continue
                    
                    transcript = result.alternatives[0].transcript
                    
                    # Real-time Update der GUI
                    self.master.after(0, self.update_interim_text, transcript, result.is_final)
                    
        except Exception as e:
            self.master.after(0, messagebox.showerror, "Audio/Stream Fehler", f"Fehler: {e}")
            self.is_recording = False
            self.master.after(0, self.record_button.config, {'text': "Diktat Start / Stopp", 'state': tk.NORMAL})
            self.master.after(0, self.status_label.config, {'text': "Status: Fehler (Audio)", 'style': 'Danger.TLabel'}) # KORREKTUR des Styles

    # --- 4. Verarbeitungs-Logik (OpenAI GPT Strukturierung) ---
    
    def process_dictation(self):
        try:
            # 1. Text-Extraktion und Sicherheitscheck
            roh_text = self.result_text.get("1.0", tk.END).strip()
            
            if "[DIKTIERE:" in roh_text:
                roh_text = roh_text.split("[DIKTIERE:")[0].strip()

            if not roh_text:
                self.master.after(0, messagebox.showinfo, "Warnung", "Kein Text diktiert (Quelltext war leer).")
                return

            # 2. Strukturierung (GPT-4o)
            self.master.after(0, self.status_label.config, {'text': "Status: 🧠 Strukturiere mit GPT-4o..."})  

            base_prompt = self.prompt_text.get("1.0", tk.END).strip()
            
            full_prompt = base_prompt.replace('{roh_text}', roh_text)
            
            response = openai_client.chat.completions.create(
                model='gpt-4o',
                messages=[ 
                    {"role": "system", "content": "You are a helpful and precise medical documentation assistant."},
                    {"role": "user", "content": full_prompt}
                ]
            )
            
            final_report = response.choices[0].message.content

            # 3. Ausgabe in die GUI
            self.master.after(0, self.result_text.delete, "1.0", tk.END)
            self.master.after(0, self.result_text.insert, tk.END, final_report)
            self.master.after(0, self.status_label.config, {'text': "Status: Befund fertig!", 'style': 'Success.TLabel'}) 
            
            # 4. Automatisch kopieren
            self.master.after(0, self.copy_formatted_report) 
            
        except Exception as e:
            self.master.after(0, messagebox.showerror, "KI/API Fehler", f"Ein Fehler ist beim API-Aufruf aufgetreten: {e}. Prüfen Sie GPT-4o Key/Guthaben.")
            self.master.after(0, self.status_label.config, {'text': "Status: FEHLER! (API/Guthaben)", 'style': 'Danger.TLabel'}) 
            
        finally:
            self.master.after(0, self.record_button.config, {'text': "Diktat Start / Stopp", 'state': tk.NORMAL})
            self.master.after(0, self.update_level_bar, 0)
            
    
    
    
    def copy_formatted_report(self):
        try:
            import win32clipboard
            
            markdown_text = self.result_text.get("1.0", tk.END).strip()
            
            if not markdown_text:
                messagebox.showwarning("Kopier-Fehler", "Das Ausgabefeld ist leer.")
                return

            markdown_text_corrected = markdown_text 
            html_output = markdown.markdown(markdown_text_corrected)
            
            # --- 1. Definiere das Rumpf-HTML (Fragment) ---
            fragment = f"""<html>
<head><meta charset="utf-8"></head>
<body>
{html_output}
</body>
</html>"""

            # 2. Definiere den Windows Clipboard Header mit Platzhaltern
            html_header = """Version:1.0
StartHTML:00000000
EndHTML:00000000
StartFragment:00000000
EndFragment:00000000
SourceURL:none
"""

            # 3. Den kompletten String zusammenfügen
            html_data = html_header + fragment

            # 4. Berechne die genauen Start- und Endpunkte
            # Header Ende: Position des ersten Zeichens des Fragments (des <html>-Tags)
            # Fragment Start: Position des Markierungskommentars
            start_fragment = html_data.index("") + len("")
            end_fragment = html_data.index("")
            
            start_html = html_data.index("<html>")
            end_html = len(html_data)

            # 5. Ersetze die Platzhalter mit den berechneten Byte-Positionen (8-stellig)
            html_data = html_data.replace("StartHTML:00000000", f"StartHTML:{start_html:08}")
            html_data = html_data.replace("EndHTML:00000000", f"EndHTML:{end_html:08}")
            html_data = html_data.replace("StartFragment:00000000", f"StartFragment:{start_fragment:08}")
            html_data = html_data.replace("EndFragment:00000000", f"EndFragment:{end_fragment:08}")
            
            # --- FINALE LOGIK FÜR FORMATIERTES KOPIEREN ---
            
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            
            # Kopiert den formatierten HTML-Code (als Rich Text)
            HTML_CF = win32clipboard.RegisterClipboardFormat("HTML Format")
            win32clipboard.SetClipboardData(HTML_CF, html_data.encode('utf-8'))
            
            # Kopiert den reinen Text (als Fallback)
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, markdown_text)

            win32clipboard.CloseClipboard()
            
            self.status_label.config(text="Status: Befund als formatierter HTML-Text kopiert!", style='Info.TLabel') 
            
        except Exception as e:
            messagebox.showerror("Kopier-Fehler", f"Fehler beim Kopieren der Formatierung: {e}")
            self.status_label.config(text="Status: FEHLER beim Kopieren!", style='Danger.TLabel')
    
    
    
    
# --- 5. Starten der Anwendung ---
if __name__ == "__main__":
    # 1. Hauptfenster mit Theme initialisieren
    root = ttk.Window(themename="superhero") 
    
    # 2. GLOBALEN FONT-STIL UND FARBSTILE DEFINIEREN 
    custom_font = ("Tahoma", 12) 
    style = ttk.Style()
    
    # Überschreibt die Standard-Font-Definitionen für alle Widgets
    style.configure('.', font=custom_font)
    style.configure('TButton', font=custom_font)
    style.configure('TLabel', font=custom_font)
    
    # Definiert die spezifischen Farbstile, die in der App verwendet werden (für die .config-Aufrufe)
    style.configure("Danger.TLabel", foreground=style.colors.danger)
    style.configure("Warning.TLabel", foreground=style.colors.warning)
    style.configure("Success.TLabel", foreground=style.colors.success)
    style.configure("Info.TLabel", foreground=style.colors.info)

    # 3. App starten
    app = GigaScribeApp(root)
    root.mainloop()
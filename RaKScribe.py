## RaKScribe - Version 1.02 (verkleiner, kein scipy)
# Hybrid Streaming Diktat und Structured Reporting
# Optimierungen: Google 'latest_long', Scipy entfernt, Boost angepasst

import keyboard 
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import sounddevice as sd
# ENTFERNT: from scipy.io.wavfile import write (Spart ca. 50-80MB in der EXE)
import numpy as np
import threading
import os
import sys
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

# =========================================================================
# === PFAD-LOGIK ===
# =========================================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE_PATH = os.path.join(BASE_DIR, 'config.ini')

# =========================================================================
# === CONFIG LOADING ===
# =========================================================================
config = configparser.ConfigParser()

try:
    config.read(CONFIG_FILE_PATH)
    if not config.sections():
        raise FileNotFoundError
        
    OPENAI_API_KEY = config['API_KEYS']['OPENAI_API_KEY'].strip()
    GOOGLE_JSON_FILENAME = config['API_KEYS']['GOOGLE_JSON_FILENAME'].strip().replace('"', '')

except (KeyError, FileNotFoundError):
    # Fallback: Erstelle eine leere Config, falls sie fehlt, damit der User sieht was zu tun ist
    if not os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, 'w') as f:
            f.write("[API_KEYS]\nOPENAI_API_KEY = sk-...\nGOOGLE_JSON_FILENAME = google_key.json")
            
    messagebox.showerror("Konfigurations-Fehler", 
                         f"Datei 'config.ini' fehlt oder ist fehlerhaft.\n\nPfad: {BASE_DIR}\n\nBitte API-Keys eintragen und neustarten.")
    sys.exit()

SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, GOOGLE_JSON_FILENAME)

# Clients initialisieren
speech_client = None
openai_client = None

try:
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
    speech_client = speech.SpeechClient(credentials=credentials)
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    messagebox.showerror("Init Fehler", f"Fehler bei Initialisierung der Clients:\n{e}")

# -------------------------------------------------------------
# --- Liste wichtiger medizinischer Fachbegriffe ---
# -------------------------------------------------------------
MEDICAL_PHRASES = [
    "Hochauflösender Nervenschall", "Thorax pa/seitlich", "MRT", "MR", "CT", "Computertomografie", "DXA", "Knochendichtemessung",
    "Humerus", "Femur", "Tibia", "Fibula", "Patella", "Karpaltunnel", "Rotatorenmanschette",
    "Achillessehne", "Kalkaneus", "Acromioclaviculargelenk", "Sacroiliacalgelenk", "Halswirbelsäule (HWS)",
    "Brustwirbelsäule (BWS)", "Lendenwirbelsäule (LWS)", "Kreuzband", "Tarsus", "Metatarsus",
    "Fraktur", "Spondylarthrose", "Spondylodese", "Spondyolyse", "Spondylosis deformans", "pontifizierend", "pontifizierende", "Arthrose", "Coxarthrose", "Gonarthrose", "Meniskus", "Hinterhorn-Läsion",
    "Korbhenkelriss", "Bandscheibenprotrusion", "Bandscheibenprolaps", "Spinalkanalstenose", "Osteochondrose", "Nearthrosis interspinosa",  
    "Osteomyelitis", "Rheumatoide Arthritis", "Kapsel-Band-Läsion", "Osteoporose", "Bakerzyste",
    "Knochenödem", "Einklemmungssyndrom", "Arthrographie", "Szintigraphie", "Vertebroplastie",
    "Facetteninfiltration", "CT-gesteuerte Biopsie", "MR-Arthrographie", "Skelettaufnahme", "Ganzbeinaufnahme",
    "Gelenkspaltverschmälerung", "Subluxation", "Wirbelkörperkompression", "Rotatorenmanschettenruptur",
    "Labrumläsion", "Subchondrale Sklerosierung", "Nervus medianus", "Nervus radialis",
    "Liquor", "Zerebrospinalflüssigkeit", "Kortex", "Großhirnrinde", "Weiße Substanz", "Basalganglien",
    "Hypophyse", "Corpus callosum", "Sinus cavernosus", "Aorta", "Arteria carotis interna", "Arteria carotis externa",
    "Pulmonalarterie", "Vena cava superior", "Vena cava inferior", "A. vertebralis",
    "Aneurysma", "Intrakranielles Aneurysma", "Ischämie", "Ischämischer Infarkt", "Intracranielle Blutung",
    "Subarachnoidalblutung (SAB)", "Subduralhämatom (SDH)", "Epiduralhämatom (EDH)", "Multiple Sklerose (MS)",
    "Hypophysenadenom", "Hydrozephalus", "Normaldruckhydrozephalus", "Vaskulitis", "Stenose", "Carotisstenose",
    "Koronarstenose", "Dissektion", "Aortendissektion", "Thrombus", "Thrombose", "Embolie", "PAE", "Plaqubildung", "Softplaque", 
    "gemischte Plaqueformation", "IMT-Komplex", "Intima-Media-Hyperplasie", "Intimahyperplasie",
    "Varizen", "T1-gewichtete Sequenz", "T2-gewichtete Sequenz", "Flair-Sequenz", "Diffusion-weighted Imaging (DWI)",
    "Time-of-Flight (TOF) Angio", "MRA", "CTA", "Kontrastmittel (KM)", "Plaque", "Atherosklerotische Plaque",
    "Angioplastie", "Sakkuläres Aneurysma", "Gefäßokklusion",
    "Lunge", "Oberlappen", "Unterlappen", "Trachea", "Bronchien", "Mediastinum", "Herz", "Ventrikel",
    "Perikard", "Leber", "Gallenblase", "Pankreas", "Niere", "Milz", "Uterus", "Adnexe", "Appendix",
    "Schilddrüse", "Infiltrat", "Pulmonales Infiltrat", "Pleuraerguss", "Pneumothorax", "Spannungspneumothorax",
    "Kardiomegalie", "Aortenklappeninsuffizienz", "Leberzirrhose", "Cholezystitis", "Pankreatitis",
    "Nierenstein", "Ureterstein", "Nephrolithiasis", "Adnexitis", "Ovarielle Zyste", "Lymphknoten",
    "Lymphadenopathie", "Appendizitis", "Struma", "Verschattung", "Milzruptur", "Hernie", "Hiatushernie",
    "Inguinalhernie", "Dilatation", "Aszites", "Zystische Läsion", "Liquidation", "Faszienverdickung",
    "Hydronephrose", "Peritonealkarzinose", "Fokale Raumforderung (FRF)", "Hyperdens", "Hypodens", "Isodens",
    "Echoarm", "Echogen",
    "Malignität", "Benignität", "Tumor", "Karzinom", "Metastase", "Läsion", "Atypisch", "unspezifisch",
    "Degenerativ", "entzündlich", "Chronisch", "akut", "Ödem", "Hämatom", "Abszess", "Kalzifizierung",
    "Sklerosierung", "Nekrose", "Atrophie", "Randscharf", "unscharf begrenzt", "Rückbildung", "Progression",
    "V. a.", "Verdacht auf", "Differenzialdiagnose (DD)", "Interventionell", "Biopsie", "Drainage",
    "Normalbefund", "kein Nachweis für", "Axial", "koronar", "sagittal", "Anamnese", "Indikation",
    "Kontraindikation", "Artefakt", "Pixel", "Voxel", "Echoarmut", "Echogenität", "Hyperintens", "Hypointens",
    "Dosis-Längen-Produkt (DLP)", "Field of View (FOV)", "Standard-Abweichung (SD)", "Flüssigkeitsspiegel",
    "Röntgen-Thorax", "Projektionsaufnahme", "Z.n.", "Zustand nach", "Adenokarzinom", "Cholangiokarzinom",
    "Fibrose", "Hämangiom", "Atelektase", "Bronchiektasen", "Emphysem", "Sarkom", "Neurofibrom", "Lipom",
    "Aortenaneurysma", "Klaustrophobie", "Sequester", "Vollbild", "Partialruptur", "Tendinose", "Impingement"
]

# --- Optimierte Google Konfiguration ---
GOOGLE_CONFIG = speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=16000, 
    language_code="de-DE",
    model="latest_long",  # <--- UPDATE: Besseres Modell
    use_enhanced=True,
    enable_automatic_punctuation=True, # <--- NEU: Hilft GPT-4o die Sätze zu erkennen
    speech_contexts=[
        speech.SpeechContext(
            phrases=MEDICAL_PHRASES,
            boost=10.0  # <--- UPDATE: Moderaterer Boost
        )
    ]
)

STREAMING_CONFIG = speech.StreamingRecognitionConfig(
    config=GOOGLE_CONFIG,
    interim_results=True 
)

def load_prompt_template(filename="radiology_prompt.txt"):
    try:
        file_path = os.path.join(BASE_DIR, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback Prompt, falls Datei fehlt (verhindert Crash)
        return "Formatiere den folgenden radiologischen Befundtext strukturiert. Korrigiere medizinische Fehler:\n\n{roh_text}"
    except Exception as e:
        messagebox.showerror("Fehler", f"Fehler beim Laden der Prompt-Datei: {e}")
        return ""

INITIAL_PROMPT_CONTENT = load_prompt_template()


# --- Hauptanwendungsklasse ---

class GigaScribeApp:
    def __init__(self, master):
        self.master = master
        master.title("RaKScribe 1.02 - Optimized")
        
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
            self.device_info_name = "Standard Mikrofon"
        
        self.create_widgets()
        self.register_hotkey() 

    def create_widgets(self):
        main_frame = tk.Frame(self.master, padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)
        
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)  
        self.master.rowconfigure(0, weight=1)

        self.status_label = ttk.Label(main_frame, 
                                      text="Status: Bereit", 
                                      style="Success.TLabel",
                                      font=('Tahoma', 12, 'bold'))
        self.status_label.grid(row=0, column=0, sticky='w', pady=5)
        
        self.record_button = ttk.Button(main_frame, text="F10 Diktat Start / Stopp", command=self.toggle_recording, 
                                       bootstyle=(DANGER, OUTLINE), 
                                       width=20) 
        self.record_button.grid(row=0, column=1, sticky='e', pady=5)
        
        self.copy_button = ttk.Button(main_frame, text="Fertigen Befund kopieren", command=self.copy_formatted_report, 
                                       bootstyle=(PRIMARY, OUTLINE))
        self.copy_button.grid(row=5, column=0, columnspan=2, sticky='ew', pady=5)

        ttk.Label(main_frame, text="Mikrofonpegel:").grid(row=1, column=0, sticky='w', pady=5)
        ttk.Label(main_frame, text=f"Gerät: {self.device_info_name}").grid(row=1, column=1, sticky='e', pady=5)

        self.level_canvas = tk.Canvas(main_frame, width=200, height=20, bg='lightgray')
        self.level_canvas.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        self.level_rect = self.level_canvas.create_rectangle(0, 0, 0, 20, fill='darkgreen')
        
        self.paned_window = ttk.Panedwindow(main_frame, orient=HORIZONTAL)
        self.paned_window.grid(row=4, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)

        prompt_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(prompt_frame, weight=1) 
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(1, weight=1)

        ttk.Label(prompt_frame, text="Radiologie Prompt (Vorlage):").grid(row=0, column=0, sticky='w', pady=5)
        self.prompt_text = tk.Text(prompt_frame, height=10, width=45)
        self.prompt_text.grid(row=1, column=0, sticky='nsew', padx=0, pady=0) 
        self.prompt_text.insert(tk.END, INITIAL_PROMPT_CONTENT)

        result_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(result_frame, weight=1) 
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(1, weight=1)

        ttk.Label(result_frame, text="Befund (GPT-4o Output):").grid(row=0, column=0, sticky='w', pady=5)
        self.result_text = tk.Text(result_frame, height=10, width=45, bg=self.master.style.colors.inputbg)
        self.result_text.grid(row=1, column=0, sticky='nsew', padx=0, pady=0)

    def toggle_recording(self):
        if not speech_client or not openai_client:
            messagebox.showerror("Fehler", "API-Clients nicht initialisiert.")
            return

        if not self.is_recording:
            self.frames = []
            self.final_transcript = ""  
            self.is_recording = True
            
            self.status_label.config(text="Status: AUFNAHME LÄUFT... (Rot)", style="Danger.TLabel")
            self.record_button.config(text="F10 Diktat Stoppen")
            
            self.thread = threading.Thread(target=self.record)
            self.thread.start()
            
        else:
            self.is_recording = False 
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            self.status_label.config(text="Status: Verarbeite Daten...", style="Warning.TLabel")
            self.record_button.config(text="Bitte warten...", state=tk.DISABLED)
            self.master.after(100, self.check_thread_and_process)

    def check_thread_and_process(self):
        if self.thread and self.thread.is_alive():
            self.master.after(100, self.check_thread_and_process)
        else:
            process_thread = threading.Thread(target=self.process_dictation)
            process_thread.start()

    def hotkey_toggle(self, event):
        if self.record_button['state'] != tk.DISABLED:
            self.toggle_recording()

    def register_hotkey(self):
        keyboard.add_hotkey('f10', lambda: self.hotkey_toggle(None), suppress=True) 
        
    def update_level_bar(self, rms_value):
        if np.isnan(rms_value) or rms_value is None: rms_value = 0
        max_val = 1500 
        level = rms_value / max_val
        bar_width = min(int(level * 200), 200)
        self.level_canvas.coords(self.level_rect, 0, 0, bar_width, 20)
        fill_color = 'red' if level > 0.8 else 'orange' if level > 0.4 else 'darkgreen'
        self.level_canvas.itemconfig(self.level_rect, fill=fill_color)
        
    def update_interim_text(self, transcript, is_final):
        if not is_final:
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, self.final_transcript + " [.. " + transcript + " ..]")
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
        def callback(indata, frames, time, status):
            if self.is_recording:
                self.frames.append(indata.copy())
                rms = np.sqrt(np.mean(indata.astype(np.float64)**2))
                self.master.after(0, self.update_level_bar, rms) 

        try:
            self.stream = sd.InputStream(samplerate=self.samplerate, channels=1, dtype='int16', callback=callback)
            with self.stream:
                requests = self.google_streaming_generator()
                responses = speech_client.streaming_recognize(requests=requests, config=STREAMING_CONFIG)
                
                for response in responses:
                    if not response.results: continue
                    result = response.results[0]
                    if not result.alternatives: continue
                    
                    transcript = result.alternatives[0].transcript
                    self.master.after(0, self.update_interim_text, transcript, result.is_final)
                    
        except Exception as e:
            # Fehlerbehandlung, falls Stream abbricht
            if self.is_recording: # Nur Fehler zeigen, wenn wir nicht absichtlich gestoppt haben
                print(f"Stream Fehler: {e}")

    
    def process_dictation(self):
        try:
            roh_text = self.result_text.get("1.0", tk.END).strip()
            
            # Bereinigung von [.. ..] Artefakten
            roh_text = re.sub(r'\[\.\..*?\.\.\]', '', roh_text)

            if not roh_text:
                self.master.after(0, messagebox.showinfo, "Warnung", "Kein Text diktiert.")
                return

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

            self.master.after(0, self.result_text.delete, "1.0", tk.END)
            self.master.after(0, self.result_text.insert, tk.END, final_report)
            self.master.after(0, self.status_label.config, {'text': "Status: Befund fertig!", 'style': 'Success.TLabel'}) 
            
            self.master.after(0, self.copy_formatted_report) 
            self.master.after(500, lambda: keyboard.press_and_release('ctrl+v')) 
            
        except Exception as e:
            self.master.after(0, messagebox.showerror, "Fehler", f"GPT Fehler: {e}")
            self.master.after(0, self.status_label.config, {'text': "Status: Fehler", 'style': 'Danger.TLabel'}) 
            
        finally:
            self.master.after(0, self.record_button.config, {'text': "F10 Diktat Start / Stopp", 'state': tk.NORMAL})
            self.master.after(0, self.update_level_bar, 0)
    
    def copy_formatted_report(self):
        try:
            markdown_text = self.result_text.get("1.0", tk.END).strip()
            if not markdown_text: return

            html_output = markdown.markdown(markdown_text)
            
            fragment = f"<html><head><meta charset='utf-8'></head><body>{html_output}</body></html>"
            
            # Windows Clipboard Header Helper
            html_header = """Version:1.0\r\nStartHTML:{0:08d}\r\nEndHTML:{1:08d}\r\nStartFragment:{2:08d}\r\nEndFragment:{3:08d}\r\nSourceURL:none\r\n"""
            
            # Dummy-Offsets berechnen
            start_html = len(html_header.format(0, 0, 0, 0))
            start_fragment = start_html + fragment.find("<body>") + 6
            end_fragment = start_html + fragment.find("</body>")
            end_html = start_html + len(fragment)
            
            final_data = html_header.format(start_html, end_html, start_fragment, end_fragment) + fragment

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.RegisterClipboardFormat("HTML Format"), final_data.encode('utf-8'))
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, markdown_text)
            win32clipboard.CloseClipboard()
            
            self.status_label.config(text="Status: Befund kopiert!", style='Info.TLabel') 
            
        except Exception as e:
            print(f"Kopierfehler: {e}") # Kein Popup, nervt sonst im Flow

if __name__ == "__main__":
    root = ttk.Window(themename="superhero") 
    
    custom_font = ("Tahoma", 12) 
    style = ttk.Style()
    style.configure('.', font=custom_font)
    style.configure('TButton', font=custom_font)
    style.configure('TLabel', font=custom_font)
    
    style.configure("Danger.TLabel", foreground=style.colors.danger)
    style.configure("Warning.TLabel", foreground=style.colors.warning)
    style.configure("Success.TLabel", foreground=style.colors.success)
    style.configure("Info.TLabel", foreground=style.colors.info)
    
    app = GigaScribeApp(root)
    root.mainloop()

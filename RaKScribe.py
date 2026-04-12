## RaKScribe 2.0 Offline - (c) 2025 Dr. Peter Kalmar - Licensed under GPLv3
# Hybrid Streaming Diktat und Structured Reporting - Vollständig Offline
# STT: Faster-Whisper large-v3-turbo (Pseudo-Streaming mit Chunks)
# LLM: MedGemma via Ollama (lokale OpenAI-kompatible API)

import keyboard
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import sounddevice as sd
import numpy as np
import threading
import os
import sys
import time
import queue
import io
import wave
import pyperclip
import markdown
import re
import win32clipboard

# --- Faster-Whisper & Ollama (via OpenAI-Kompatibilitäts-API) ---
from faster_whisper import WhisperModel
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

    OLLAMA_URL = config['SETTINGS']['OLLAMA_URL'].strip()
    LLM_MODEL = config['SETTINGS']['LLM_MODEL'].strip()
    WHISPER_MODEL_SIZE = config['SETTINGS']['WHISPER_MODEL'].strip()
    WHISPER_COMPUTE_TYPE = config['SETTINGS']['WHISPER_COMPUTE_TYPE'].strip()
    CHUNK_DURATION = int(config['SETTINGS']['CHUNK_DURATION'].strip())

except (KeyError, FileNotFoundError):
    if not os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, 'w') as f:
            f.write("[SETTINGS]\nOLLAMA_URL = http://localhost:11434\nLLM_MODEL = alibayram/medgemma\n"
                    "WHISPER_MODEL = large-v3-turbo\nWHISPER_COMPUTE_TYPE = int8\nCHUNK_DURATION = 5\n")

    messagebox.showerror("Konfigurations-Fehler",
                         f"Datei 'config.ini' fehlt oder ist fehlerhaft.\n\nPfad: {BASE_DIR}\n\nBitte Einstellungen prüfen und neustarten.")
    sys.exit()

# --- Whisper Modell laden ---
print(f"[INIT] Lade Whisper-Modell '{WHISPER_MODEL_SIZE}' ({WHISPER_COMPUTE_TYPE})...")
whisper_model = None
try:
    whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cuda", compute_type=WHISPER_COMPUTE_TYPE)
    print("[INIT] Whisper-Modell geladen ✓")
except Exception as e:
    print(f"[INIT] CUDA nicht verfügbar, versuche CPU: {e}")
    try:
        whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
        print("[INIT] Whisper-Modell geladen (CPU-Modus) ✓")
    except Exception as e2:
        messagebox.showerror("Whisper Fehler", f"Whisper-Modell konnte nicht geladen werden:\n{e2}")

# --- Ollama Client (OpenAI-kompatible API) ---
openai_client = None
try:
    openai_client = OpenAI(base_url=f"{OLLAMA_URL}/v1", api_key="ollama")
    print(f"[INIT] Ollama-Client konfiguriert → {OLLAMA_URL} (Modell: {LLM_MODEL}) ✓")
except Exception as e:
    messagebox.showerror("Ollama Fehler", f"Fehler bei Initialisierung des Ollama-Clients:\n{e}")

# -------------------------------------------------------------
# --- Liste wichtiger medizinischer Fachbegriffe ---
# --- (Wird für Post-Processing / Referenz beibehalten) ---
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


# --- Hilfsfunktion: NumPy-Audio → WAV-Bytes ---
def numpy_to_wav_bytes(audio_np, samplerate=16000):
    """Konvertiert ein NumPy int16 Array in WAV-Bytes für Whisper."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(samplerate)
        wf.writeframes(audio_np.tobytes())
    buf.seek(0)
    return buf


# --- Hauptanwendungsklasse ---

class GigaScribeApp:
    def __init__(self, master):
        self.master = master
        master.title("RaKScribe 2.0 Offline")

        self.samplerate = 16000
        self.is_recording = False
        self.final_transcript = ""
        self.thread = None

        # Chunk-basiertes Streaming
        self.audio_queue = queue.Queue()
        self.chunk_worker_thread = None
        self.stream = None

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
                                      text="Status: Bereit (Offline-Modus)",
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

        ttk.Label(result_frame, text="Befund (MedGemma Output):").grid(row=0, column=0, sticky='w', pady=5)
        self.result_text = tk.Text(result_frame, height=10, width=45, bg=self.master.style.colors.inputbg)
        self.result_text.grid(row=1, column=0, sticky='nsew', padx=0, pady=0)

    def toggle_recording(self):
        if not whisper_model or not openai_client:
            messagebox.showerror("Fehler", "Whisper- oder Ollama-Client nicht initialisiert.")
            return

        if not self.is_recording:
            self.final_transcript = ""
            self.is_recording = True

            self.status_label.config(text="Status: AUFNAHME LÄUFT... (Rot)", style="Danger.TLabel")
            self.record_button.config(text="F10 Diktat Stoppen")

            # Audio-Queue leeren
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break

            # Aufnahme- und Chunk-Worker starten
            self.thread = threading.Thread(target=self.record, daemon=True)
            self.thread.start()

            self.chunk_worker_thread = threading.Thread(target=self.chunk_worker, daemon=True)
            self.chunk_worker_thread.start()

        else:
            self.is_recording = False
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            self.status_label.config(text="Status: Verarbeite letzte Chunks...", style="Warning.TLabel")
            self.record_button.config(text="Bitte warten...", state=tk.DISABLED)

            # Warte auf Chunk-Worker und starte dann Befundstrukturierung
            self.master.after(100, self.check_worker_and_process)

    def check_worker_and_process(self):
        """Wartet bis der Chunk-Worker fertig ist, dann startet GPT-Verarbeitung."""
        if self.chunk_worker_thread and self.chunk_worker_thread.is_alive():
            self.master.after(100, self.check_worker_and_process)
        else:
            process_thread = threading.Thread(target=self.process_dictation, daemon=True)
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

    def update_transcript_display(self, new_segment, is_interim=False):
        """Aktualisiert die Transkript-Anzeige im UI."""
        self.result_text.delete("1.0", tk.END)
        if is_interim:
            self.result_text.insert(tk.END, self.final_transcript + " [.. " + new_segment + " ..]")
        else:
            self.result_text.insert(tk.END, self.final_transcript.strip())

    def record(self):
        """Nimmt Audio auf und schiebt Chunks in die Queue."""
        chunk_buffer = []
        samples_per_chunk = self.samplerate * CHUNK_DURATION

        def callback(indata, frames, time_info, status):
            if self.is_recording:
                chunk_buffer.append(indata.copy())
                rms = np.sqrt(np.mean(indata.astype(np.float64)**2))
                self.master.after(0, self.update_level_bar, rms)

                # Prüfe ob ein voller Chunk zusammen ist
                total_samples = sum(len(c) for c in chunk_buffer)
                if total_samples >= samples_per_chunk:
                    full_chunk = np.concatenate(chunk_buffer, axis=0)
                    self.audio_queue.put(full_chunk[:samples_per_chunk])
                    # Rest für nächsten Chunk behalten
                    remaining = full_chunk[samples_per_chunk:]
                    chunk_buffer.clear()
                    if len(remaining) > 0:
                        chunk_buffer.append(remaining)

        try:
            self.stream = sd.InputStream(samplerate=self.samplerate, channels=1, dtype='int16', callback=callback)
            with self.stream:
                while self.is_recording:
                    time.sleep(0.05)

                # Aufnahme gestoppt - letzten Partial-Chunk senden
                if chunk_buffer:
                    remaining_audio = np.concatenate(chunk_buffer, axis=0)
                    if len(remaining_audio) > self.samplerate * 0.3:  # Mindestens 0.3s Audio
                        self.audio_queue.put(remaining_audio)
                    chunk_buffer.clear()

                # Sentinel: signalisiert dem Worker, dass keine Chunks mehr kommen
                self.audio_queue.put(None)

        except Exception as e:
            print(f"[FEHLER] Audio-Stream: {e}")
            self.audio_queue.put(None)

    def chunk_worker(self):
        """Verarbeitet Audio-Chunks aus der Queue mit Whisper."""
        chunk_count = 0
        while True:
            try:
                audio_chunk = self.audio_queue.get(timeout=1.0)
            except queue.Empty:
                if not self.is_recording:
                    # Prüfe nochmal ob Queue leer ist
                    if self.audio_queue.empty():
                        break
                continue

            if audio_chunk is None:
                # Sentinel empfangen - Worker beenden
                break

            chunk_count += 1
            self.master.after(0, self.status_label.config,
                            {'text': f"Status: AUFNAHME ▶ Chunk {chunk_count} wird transkribiert..."})

            try:
                # NumPy int16 → WAV-Bytes → Whisper
                wav_buffer = numpy_to_wav_bytes(audio_chunk, self.samplerate)
                
                # BESSERE ERKENNUNG: Initial Prompt nutzt jetzt den gesamten Vokabel-Vorrat
                initial_hint = ", ".join(MEDICAL_PHRASES[:100]) # Erste 100 Begriffe als Hint
                
                segments, info = whisper_model.transcribe(
                    wav_buffer,
                    language="de",
                    beam_size=5,
                    initial_prompt=initial_hint,
                    condition_on_previous_text=True,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=300)
                )

                chunk_text = " ".join([seg.text.strip() for seg in segments])

                if chunk_text:
                    self.final_transcript += chunk_text + " "
                    self.master.after(0, self.update_transcript_display, "", False)
                    print(f"  [Chunk {chunk_count}] {chunk_text}")

            except Exception as e:
                print(f"  [FEHLER] Chunk {chunk_count}: {e}")

        print(f"[WHISPER] Fertig - {chunk_count} Chunks verarbeitet")

    def process_dictation(self):
        """Sendet das Rohtranskript an MedGemma via Ollama zur Strukturierung."""
        try:
            roh_text = self.final_transcript.strip()

            # Bereinigung von [.. ..] Artefakten (falls vorhanden)
            roh_text = re.sub(r'\[\.\..*?\.\.\]', '', roh_text)

            if not roh_text:
                self.master.after(0, messagebox.showinfo, "Warnung", "Kein Text diktiert.")
                return

            self.master.after(0, self.status_label.config, {'text': "Status: 🧠 Strukturiere mit MedGemma..."})

            base_prompt = self.prompt_text.get("1.0", tk.END).strip()
            full_prompt = base_prompt.replace('{roh_text}', roh_text)

            # STRENGERER PROMPT gegen Halluzinationen
            system_msg = (
                "Du bist ein präziser Radiologie-Assistent. Deine Aufgabe ist es, phonetische Fehler der Spracherkennung "
                "zu korrigieren (z.B. 'Habe' -> 'HWS', 'Strickhaltung' -> 'Streckhaltung') und den Text in das Zielformat "
                "zu bringen. Erfinde NIEMALS neue medizinische Sachverhalte oder Komplikationen, die nicht im Text stehen. "
                "Wenn der Text unverständlich ist, gib ihn unverändert im Zielformat aus, aber erfinde keine Diagnosen."
            )

            response = openai_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": full_prompt}
                ]
            )

            final_report = response.choices[0].message.content

            self.master.after(0, self.result_text.delete, "1.0", tk.END)
            self.master.after(0, self.result_text.insert, tk.END, final_report)
            self.master.after(0, self.status_label.config, {'text': "Status: Befund fertig! (Offline)", 'style': 'Success.TLabel'})

            self.master.after(0, self.copy_formatted_report)
            self.master.after(500, lambda: keyboard.press_and_release('ctrl+v'))

        except Exception as e:
            self.master.after(0, messagebox.showerror, "Fehler", f"MedGemma/Ollama Fehler: {e}")
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

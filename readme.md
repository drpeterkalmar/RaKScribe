# 🚀 RaKScribe
Willkommen bei **RaKScribe**, dem hybriden Diktier-Tool für strukturierte radiologische Befunde.

RaKScribe kombiniert die Geschwindigkeit der Spracherkennung des Google Cloud Streamings mit der relativ preiswerten Strukturierungsintelligenz von OpenAI GPT-4o. 
> **Hinweis:** Für die Nutzung fallen API-Kosten an (ca. 1,3 Cent pro Befundminute, Stand Nov. 2025).

## 💡 Konzept und Begründung der Hybrid-Architektur

RaKScribe nutzt eine hybride Cloud-Lösung, um die jeweiligen Stärken der führenden KI-Anbieter optimal zu kombinieren:

| Komponente | Anbieter | Begründung |
| :--- | :--- | :--- |
| **Speech-to-Text (STT)** | Google Cloud Speech-to-Text | Bietet eine extrem schnelle, latenzarme Streaming-API, die Audio in kurzen Segmenten (z.B. 5-Sekunden-Chunks) verarbeitet, während Sie sprechen. Dies ist entscheidend für das flüssige Diktat in Echtzeit. Die Konkurrenz (wie OpenAI Whisper API) ist typischerweise auf die Auswertung kompletter Audiodateien nach Beendigung des Diktats ausgelegt und daher für Echtzeit-Anwendungen zu langsam. |
| **Text-Strukturierung (LLM)** | OpenAI GPT-4o | Wird für die regelbasierte Nachbearbeitung verwendet. GPT-4o ist preiswert bei der Einhaltung langer Anweisungsketten (`radiology_prompt.txt`) und der fehlerfreien Konvertierung von Roh-Diktat in den gewünschten, strukturierten Befund (Markdown-Format mit Korrekturen und Hervorhebungen). |

---

### 👉 [DIE DETAILLIERTE INSTALLATIONSANLEITUNG BEFINDET SICH HIER (INSTALL.MD)](install.md)

---

## Grobes Vorgehen

### ⚙️ Voraussetzungen und API-Zugriff
* **Python 3.10** oder neuer. 
* **OpenAI:** API-Schlüssel (für das Modell `gpt-4o`)
* **Google Cloud:** JSON-Datei mit aktivierter "Cloud Speech-to-Text API"

> **🇩🇪 Sprachhinweis:** > Das RaKScribe-Projekt ist in seiner aktuellen Version vollständig auf die deutsche Sprache fixiert. Dies betrifft sowohl die Spracherkennung (`language_code="de-DE"` in Google Cloud STT) als auch die gesamte Befundstrukturierung durch GPT-4o (`radiology_prompt.txt`). Eine Nutzung in anderen Sprachen erfordert Anpassungen im Code und im Prompt-Template.

### 📦 1. Installation der Abhängigkeiten
Pakete installieren aus `requirements.txt` und Audio-Treiber testen.

### 🔐 2. Authentifizierung einrichten
OPENAI-API-Schlüssel und die Google JSON-Datei im Projektordner hinterlegen.

### 🚀 3. Starten
Spracherkennung mit **F10** starten und stoppen.  
Falls ein Textfenster offen ist, wird der fertige Befund sofort WORD/HTML-formatiert eingefügt.

# 🚀 RaKScribe 2.0 (Offline)

Willkommen bei **RaKScribe**, dem spezialisierten Diktier-Tool für strukturierte radiologische Befunde – jetzt **100% Offline**, datenschutzkonform und kostenlos.

RaKScribe nutzt modernste lokale KI-Modelle, um gesprochenes Wort direkt auf Ihrem Rechner in hochpräzise medizinische Berichte zu verwandeln. 

> [!TIP]
> **Vorteil:** Es verlassen keine Patientendaten Ihren Rechner (DSGVO-konform). Es entstehen keine API-Kosten.

## 💡 Architektur: 100% Lokale Intelligenz

RaKScribe ersetzt Cloud-Dienste durch leistungsstarke lokale Worker-Modelle:

| Komponente | Engine | Begründung |
| :--- | :--- | :--- |
| **Spracherkennung (STT)** | **Faster-Whisper** (`large-v3-turbo`) | Nutzt die GPU zur Echtzeit-Transkription. Durch Chunk-basiertes Pseudo-Streaming sehen Sie Ihren Text bereits während des Sprechens – ganz ohne Google Cloud. |
| **Strukturierung (LLM)** | **Gemma 4** (`gemma4:e4b`) | Ein hochmodernes lokales Modell von Google DeepMind, das via Ollama betrieben wird. Es korrigiert Diktatfehler und formatiert den Befund basierend auf Ihren Vorlagen (`radiology_prompt.txt`). |

---

### 👉 [DETAILLIERTE INSTALLATIONSANLEITUNG (INSTALL.MD)](install.md)

---

## Kernfunktionen

### ⚙️ Voraussetzungen
* **Python 3.12** oder neuer. 
* **NVIDIA GPU:** Empfohlen (mind. 8GB VRAM für flüssigen Betrieb).
* **Ollama:** Der lokale Backend-Server für das Sprachmodell.

### 🔒 Sicherheit & Datenschutz
* Keine Übertragung von Audio- oder Textdaten an externe Server (OpenAI, Google).
* Vollständige Kontrolle über die verwendeten Modelle und Daten.
* Ideal für sensible klinische Umgebungen und Praxen.

### 🚀 Schneller Workflow
1. **F10** drücken → Diktat startet (Live-Anzeige der Chunks).
2. **F10** erneut drücken → Modell strukturiert den Befund innerhalb von Sekunden.
3. Der fertige Befund wird automatisch in Word/RIS/PACS eingefügt (via Clipboard).

## Anpassung
Die medizinische Intelligenz steckt in der `radiology_prompt.txt`. Hier können Sie Ihre persönlichen Normalbefunde, Abkürzungen und Formatierungswünsche hinterlegen.

---
*(c) 2025-2026 Dr. Peter Kalmar - Erstellt für die lokale radiologische Befundung.*

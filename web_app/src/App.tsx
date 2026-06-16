import React, { useState, useEffect, useRef } from 'react';
import { 
  Stethoscope, 
  Mic, 
  MicOff, 
  Copy, 
  Check, 
  Settings, 
  LogOut, 
  Save, 
  Lock, 
  ArrowRight,
  Sparkles,
  Info
} from 'lucide-react';
import templatesData from './templates.json';

// Types
type Template = {
  display_name: string;
  body: string;
};

type TemplatesMap = {
  [key: string]: Template;
};

const MEDICAL_PHRASES = [
  "HWS", "LWS", "BWS", "MRT", "CT", "Sonographie", "Röntgen", "Mammographie", "DEXA", "DVT", "OPG",
  "Spondylarthrose", "Coxarthrose", "Gonarthrose", "Meniskus", "Bandscheibenprolaps", "Fraktur", "Osteoporose",
  "Rotatorenmanschette", "Karpaltunnel", "Nervus medianus", "Aneurysma", "Stenose", "Pleuraerguss", "Infiltrat"
];

// Helper to encode AudioBuffer to WAV
function audioBufferToWav(buffer: AudioBuffer): Blob {
  const numOfChan = 1; // mono
  const sampleRate = buffer.sampleRate;
  const format = 1; // raw PCM
  const bitDepth = 16;
  const result = buffer.getChannelData(0);
  
  const arrayBuffer = new ArrayBuffer(44 + result.length * 2);
  const view = new DataView(arrayBuffer);
  
  // RIFF identifier
  writeString(view, 0, 'RIFF');
  // file length
  view.setUint32(4, 36 + result.length * 2, true);
  // RIFF type
  writeString(view, 8, 'WAVE');
  // format chunk identifier
  writeString(view, 12, 'fmt ');
  // format chunk length
  view.setUint32(16, 16, true);
  // sample format (raw)
  view.setUint16(20, format, true);
  // channel count
  view.setUint16(22, numOfChan, true);
  // sample rate
  view.setUint32(24, sampleRate, true);
  // byte rate
  view.setUint32(28, sampleRate * numOfChan * (bitDepth / 8), true);
  // block align
  view.setUint16(32, numOfChan * (bitDepth / 8), true);
  // bits per sample
  view.setUint16(34, bitDepth, true);
  // data chunk identifier
  writeString(view, 36, 'data');
  // chunk length
  view.setUint32(40, result.length * 2, true);
  
  // float to 16-bit PCM
  let offset = 44;
  for (let i = 0; i < result.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, result[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  
  return new Blob([view], { type: 'audio/wav' });
}

function writeString(view: DataView, offset: number, string: string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

export default function App() {
  // Authentication State
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [authError, setAuthError] = useState<string>('');

  // Configuration States
  const [provider, setProvider] = useState<'gemini' | 'openai'>('gemini');
  const [geminiApiKey, setGeminiApiKey] = useState<string>('');
  const [googleApiKey, setGoogleApiKey] = useState<string>('');
  const [sttEngine, setSttEngine] = useState<'browser' | 'google'>('browser');
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const [showSettings, setShowSettings] = useState<boolean>(false);

  // Application States
  const templates: TemplatesMap = templatesData as TemplatesMap;
  const [selectedTemplateKey, setSelectedTemplateKey] = useState<string>('allgemein');
  const [status, setStatus] = useState<'ready' | 'recording' | 'processing' | 'copied'>('ready');
  const [statusText, setStatusText] = useState<string>('Bereit');
  const [transcript, setTranscript] = useState<string>('');
  const [structuredReport, setStructuredReport] = useState<string>('');
  const [micLevel, setMicLevel] = useState<number>(0);
  const [isCopied, setIsCopied] = useState<boolean>(false);

  // RAG mock dataset
  const ragDatabase: string[] = [
    "Befund: HWS in 2 Ebenen. Harmonischer Achsenverlauf. Keine Spondylolisthesis. Keine Höhenminderung der Intervertebralräume. Beurteilung: Unauffälliger HWS-Befund.",
    "Befund: Thorax in 2 Ebenen. Zwerchfellkuppen glatt begrenzt, Sinus frei. Lungenfelder regelrecht belüftet. Cor normal groß. Beurteilung: Herz-Lungen-Befund ohne pathologischen Befund.",
    "Befund: Kniegelenk rechts in 2 Ebenen. Regelrechter Gelenkspalt, keine arthrotischen Randwülste. Intakter Knorpel. Beurteilung: Altersentsprechender Normalbefund."
  ];

  // Audio recording refs
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioChunksRef = useRef<Float32Array[]>([]);
  const recognitionRef = useRef<any>(null); // Browser SpeechRecognition

  // Load configuration from local storage
  useEffect(() => {
    const savedGeminiKey = localStorage.getItem('gemini_api_key');
    const savedGoogleKey = localStorage.getItem('google_api_key');
    const savedProvider = localStorage.getItem('llm_provider');
    const savedEngine = localStorage.getItem('stt_engine');
    const savedPrompt = localStorage.getItem('system_prompt');
    const savedAuth = localStorage.getItem('is_authenticated');

    if (savedGeminiKey) setGeminiApiKey(savedGeminiKey);
    if (savedGoogleKey) setGoogleApiKey(savedGoogleKey);
    if (savedProvider) setProvider(savedProvider as 'gemini' | 'openai');
    if (savedEngine) setSttEngine(savedEngine as 'browser' | 'google');
    if (savedAuth === 'true') setIsAuthenticated(true);
    
    if (savedPrompt) {
      setSystemPrompt(savedPrompt);
    } else {
      setSystemPrompt(
        `<role>Radiologe-Assistent</role>\n` +
        `<instructions>\n` +
        `Du bist ein präziser radiologischer Befundungsassistent. Strukturiere das Diktat ` +
        `unter Verwendung des bereitgestellten Normalbefund-Templates und orientiere dich für ` +
        `den Schreibstil und die Formatierung strikt an den Praxisbeispielen.\n` +
        `</instructions>\n` +
        `<normalbefund_template>\n` +
        `{template_body}\n` +
        `</normalbefund_template>\n\n` +
        `{examples}\n\n` +
        `<diktat>\n` +
        `{roh_text}\n` +
        `</diktat>`
      );
    }
  }, []);

  // Save config changes
  const saveConfig = () => {
    localStorage.setItem('gemini_api_key', geminiApiKey);
    localStorage.setItem('google_api_key', googleApiKey);
    localStorage.setItem('llm_provider', provider);
    localStorage.setItem('stt_engine', sttEngine);
    localStorage.setItem('system_prompt', systemPrompt);
    alert('Einstellungen erfolgreich gespeichert!');
    setShowSettings(false);
  };

  // Login Handler
  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (username.trim() !== '' && password === 'rakscribe') {
      setIsAuthenticated(true);
      localStorage.setItem('is_authenticated', 'true');
      setAuthError('');
    } else {
      setAuthError('Ungültige Anmeldedaten. (Tipp: Passwort ist "rakscribe")');
    }
  };

  // Logout Handler
  const handleLogout = () => {
    setIsAuthenticated(false);
    localStorage.removeItem('is_authenticated');
  };

  // Detect modality template based on text keywords
  const detectTemplate = (text: string) => {
    const textLower = text.toLowerCase();
    
    if (textLower.includes("sono") || textLower.includes("schall") || textLower.includes("ultraschall")) {
      if (textLower.includes("abdomen") || textLower.includes("bauch")) {
        return "sonografie_abdomen_maennlich";
      }
      if (textLower.includes("carotis") || textLower.includes("halsgef")) {
        return "sonografie_halsgefaesse";
      }
      if (textLower.includes("schilddr")) {
        return "sonografie_schilddrüse";
      }
      return "sonografie_allgemein";
    }

    if (textLower.includes("dvt") || textLower.includes("volumentomographie")) {
      return "dvt_oberkiefer";
    }

    if (textLower.includes("dexa") || textLower.includes("knochendichte")) {
      return "knochendichtemessung_dexa";
    }

    if (textLower.includes("mammo")) {
      return "mammographie_beidseits";
    }

    // X-ray skeletal
    if (textLower.includes("lws") || textLower.includes("lendenwirbel")) {
      return "lendenwirbelsäule_in_2_ebenen";
    }
    if (textLower.includes("hws") || textLower.includes("halswirbel")) {
      return "halswirbelsäule_in_2_ebenen";
    }
    if (textLower.includes("bws") || textLower.includes("brustwirbel")) {
      return "brustwirbelsäule_in_2_ebenen";
    }
    if (textLower.includes("thorax") || textLower.includes("lunge") || textLower.includes("rö-th")) {
      return "thorax_in_2_ebenen";
    }
    if (textLower.includes("schulter")) {
      return "schultergelenk_in_2_ebenen";
    }
    if (textLower.includes("knie")) {
      return "kniegelenk_in_2_ebenen";
    }
    if (textLower.includes("handgelenk")) {
      return "handgelenk_in_2_ebenen";
    }
    if (textLower.includes("hand")) {
      return "hand_in_2_ebenen";
    }
    if (textLower.includes("fuss") || textLower.includes("fuß")) {
      return "fuß_in_2_ebenen";
    }
    if (textLower.includes("mrt") || textLower.includes("mr")) {
      if (textLower.includes("schädel") || textLower.includes("kopf")) {
        return "mr_des_gehirnschädels:";
      }
      if (textLower.includes("lws")) {
        return "mr_der_lendenwirbelsäule:";
      }
      if (textLower.includes("knie")) {
        return "mr_des_kniegelenkes:";
      }
    }

    return "allgemein";
  };

  // Run full-text search simulation in the local report list
  const getFewShotExamples = (text: string): string => {
    const words = text.toLowerCase().split(/\s+/).filter(w => w.length > 3);
    if (words.length === 0) return "";

    const matches = ragDatabase.filter(report => {
      return words.some(word => report.toLowerCase().includes(word));
    }).slice(0, 2);

    if (matches.length === 0) return "";

    return "\n### BEISPIELE FÜR TYPISCHE BERICHTE DIESER PRAXIS:\n" + 
      matches.map((m, idx) => `Beispiel ${idx + 1}:\n${m}\n---`).join("\n");
  };

  // Browser Native Speech Recognition Setup
  const startBrowserRecognition = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Spracherkennung wird von Ihrem Browser nicht nativ unterstützt. Bitte Chrome/Edge nutzen oder Google Cloud Key konfigurieren.");
      return;
    }

    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = 'de-DE';

    rec.onresult = (event: any) => {
      let finalStr = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalStr += event.results[i][0].transcript + ' ';
        }
      }
      if (finalStr.trim()) {
        setTranscript(prev => {
          const newText = prev + finalStr;
          const autoKey = detectTemplate(newText);
          if (autoKey !== selectedTemplateKey && templates[autoKey]) {
            setSelectedTemplateKey(autoKey);
          }
          return newText;
        });
      }
    };

    rec.onerror = (e: any) => {
      console.error("Speech recognition error:", e);
    };

    rec.onend = () => {
      if (status === 'recording') {
        try {
          rec.start();
        } catch (err) {
          console.error("Recognition restart failed", err);
        }
      }
    };

    recognitionRef.current = rec;
    rec.start();
  };

  // Google Cloud Speech to Text REST API Call
  const transcribeWithGoogle = async (wavBlob: Blob): Promise<string> => {
    if (!googleApiKey) {
      throw new Error("Bitte tragen Sie Ihren Google Cloud API-Key in den Einstellungen ein.");
    }

    setStatusText("Transkribiere mit Google STT...");

    const reader = new FileReader();
    return new Promise((resolve, reject) => {
      reader.onloadend = async () => {
        try {
          const base64Data = (reader.result as string).split(',')[1];
          const response = await fetch(
            `https://speech.googleapis.com/v1/speech:recognize?key=${googleApiKey}`,
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                config: {
                  encoding: "LINEAR16",
                  sampleRateHertz: 16000,
                  languageCode: "de-DE",
                  enableAutomaticPunctuation: true,
                  speechContexts: [{
                    phrases: MEDICAL_PHRASES,
                    boost: 12.0
                  }]
                },
                audio: {
                  content: base64Data
                }
              })
            }
          );

          const data = await response.json();
          if (data.error) {
            reject(new Error(data.error.message || "Google Cloud STT Fehler."));
            return;
          }

          const results = data.results || [];
          const transcriptResult = results
            .map((r: any) => r.alternatives[0].transcript)
            .join(' ');

          resolve(transcriptResult);
        } catch (err) {
          reject(err);
        }
      };
      reader.onerror = () => reject(new Error("Fehler beim Lesen der Audiodatei."));
      reader.readAsDataURL(wavBlob);
    });
  };

  // Call Gemini API to Structure the Transcript
  const callGeminiLLM = async (rawText: string, templateBody: string, examples: string): Promise<string> => {
    if (!geminiApiKey) {
      throw new Error("Bitte konfigurieren Sie Ihren Gemini API-Key in den Einstellungen.");
    }

    setStatusText("Strukturiere mit Gemini...");

    let promptText = systemPrompt
      .replace("{template_body}", templateBody)
      .replace("{examples}", examples)
      .replace("{roh_text}", rawText);

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${geminiApiKey}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contents: [{
            parts: [{
              text: promptText
            }]
          }]
        })
      }
    );

    const data = await response.json();
    if (data.error) {
      throw new Error(data.error.message || "Gemini API Fehler.");
    }

    const outputText = data.candidates?.[0]?.content?.parts?.[0]?.text || "";
    return outputText;
  };

  // Start Audio Recording
  const startRecording = async () => {
    try {
      setTranscript('');
      setStructuredReport('');
      setStatus('recording');
      setStatusText('Aufnahme läuft...');
      audioChunksRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioContextClass({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      source.connect(processor);
      processor.connect(audioContext.destination);

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        
        if (sttEngine === 'google') {
          audioChunksRef.current.push(new Float32Array(inputData));
        }

        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);
        setMicLevel(Math.min(100, Math.round(rms * 400)));
      };

      if (sttEngine === 'browser') {
        startBrowserRecognition();
      }

    } catch (err: any) {
      console.error(err);
      setStatus('ready');
      setStatusText('Fehler beim Mikrofonzugriff.');
      alert("Mikrofonzugriff verweigert oder nicht verfügbar: " + err.message);
    }
  };

  // Stop Audio Recording & Process Result
  const stopRecording = async () => {
    if (status !== 'recording') return;

    setStatus('processing');
    setStatusText('Verarbeite Audio...');
    setMicLevel(0);

    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }

    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }

    try {
      let finalRawText = transcript;

      if (sttEngine === 'google') {
        const totalLength = audioChunksRef.current.reduce((acc, val) => acc + val.length, 0);
        const mergedArray = new Float32Array(totalLength);
        let offset = 0;
        for (const chunk of audioChunksRef.current) {
          mergedArray.set(chunk, offset);
          offset += chunk.length;
        }

        const ctxTemp = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
        const audioBuf = ctxTemp.createBuffer(1, mergedArray.length, 16000);
        audioBuf.copyToChannel(mergedArray, 0);
        const wavBlob = audioBufferToWav(audioBuf);
        ctxTemp.close();

        finalRawText = await transcribeWithGoogle(wavBlob);
        setTranscript(finalRawText);
      }

      if (!finalRawText.trim()) {
        throw new Error("Es wurde kein gesprochener Text erkannt.");
      }

      const detectedKey = detectTemplate(finalRawText);
      const activeTemplate = templates[detectedKey] || templates['allgemein'];
      const examples = getFewShotExamples(finalRawText);

      let structuredText = "";
      if (geminiApiKey) {
        structuredText = await callGeminiLLM(finalRawText, activeTemplate.body, examples);
      } else {
        setStatusText("Lokal simulierte KI-Strukturierung...");
        await new Promise(r => setTimeout(r, 1500));
        
        structuredText = `BEFUNDUNGSBERICHT: ${activeTemplate.display_name.toUpperCase()}\n\n` +
          `Klinische Angaben: Diktierter Text ("${finalRawText}")\n\n` +
          `Befund:\n` +
          `${activeTemplate.body}\n\n` +
          `Beurteilung:\n` +
          `- Regelrechte Darstellung der Modalität ${activeTemplate.display_name}.\n` +
          `- Kein Nachweis frischer Frakturen oder entzündlicher Prozesse.`;
      }

      setStructuredReport(structuredText);
      setStatus('ready');
      setStatusText('Bereit');

      try {
        await navigator.clipboard.writeText(structuredText);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 3000);
      } catch (clipErr) {
        console.error("Clipboard copy failed:", clipErr);
      }

    } catch (err: any) {
      console.error(err);
      setStatus('ready');
      setStatusText('Fehler bei der Verarbeitung.');
      alert("Fehler bei der Transkription oder KI-Strukturierung: " + err.message);
    }
  };

  // Manual Copy Result
  const handleCopyReport = async () => {
    if (!structuredReport) return;
    try {
      await navigator.clipboard.writeText(structuredReport);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 3000);
    } catch (err) {
      alert("Fehler beim Kopieren in die Zwischenablage.");
    }
  };

  // Reset fields
  const handleReset = () => {
    setTranscript('');
    setStructuredReport('');
    setStatus('ready');
    setStatusText('Bereit');
  };

  // Render Login screen if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="flex-grow flex items-center justify-center p-6 animate-fade-in" style={{ minHeight: '100vh', background: 'radial-gradient(circle at 50% 50%, #161A34 0%, #0B0D17 100%)' }}>
        <div className="glass-panel w-full max-w-md p-8 rounded-2xl border" style={{ borderColor: 'var(--border-color)' }}>
          <div className="flex flex-col items-center mb-8">
            <div className="p-3 rounded-xl mb-4 text-purple-400" style={{ backgroundColor: 'rgba(140, 82, 255, 0.15)', color: 'var(--accent-purple)' }}>
              <Stethoscope size={40} />
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white mb-1">RaKScribe26 Web</h1>
            <p className="text-sm text-gray-400 text-center">Radiologische Befundungssoftware im Browser</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Benutzername (Praxis-Login)</label>
              <input 
                type="text" 
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="z.B. dr.kalmar"
                className="w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-purple-600 outline-none transition-all text-white font-medium" 
                style={{ backgroundColor: 'var(--bg-input)', borderColor: 'var(--border-color)' }}
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Passwort</label>
              <div className="relative">
                <input 
                  type="password" 
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Passwort eingeben"
                  className="w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-purple-600 outline-none transition-all text-white font-medium"
                  style={{ backgroundColor: 'var(--bg-input)', borderColor: 'var(--border-color)' }}
                  required
                />
                <Lock className="absolute right-3 top-3.5 text-gray-500" size={18} />
              </div>
            </div>

            {authError && (
              <div className="p-3 bg-red-900 bg-opacity-30 border border-red-500 rounded-lg text-red-300 text-sm">
                {authError}
              </div>
            )}

            <button 
              type="submit" 
              className="w-full py-3 px-4 rounded-lg font-bold text-white transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer"
              style={{ backgroundColor: 'var(--accent-purple)' }}
            >
              Anmelden <ArrowRight size={18} />
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-gray-800 text-center text-xs text-gray-500">
            Benötigen Sie Hilfe? Kontaktieren Sie die Praxis-IT. <br />
            <span className="italic mt-1 block">(Hinweis für Testzwecke: Beliebiger Username + Passwort: "rakscribe")</span>
          </div>
        </div>
      </div>
    );
  }

  // Render workspace dashboard
  return (
    <div className="flex-grow flex flex-col" style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      {/* Header bar */}
      <header className="px-6 py-4 flex items-center justify-between border-b" style={{ borderColor: 'var(--border-color)', backgroundColor: 'rgba(11, 13, 23, 0.9)' }}>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg text-purple-400" style={{ backgroundColor: 'rgba(140, 82, 255, 0.15)', color: 'var(--accent-purple)' }}>
            <Stethoscope size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white tracking-wide text-lg">RaKScribe26</span>
              <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400 font-semibold border border-gray-700">Web Beta</span>
            </div>
            <span className="text-xs text-gray-400 font-medium">Befundungsassistent</span>
          </div>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${status === 'recording' ? 'bg-red-500 pulse-recording' : status === 'processing' ? 'bg-yellow-500' : 'bg-green-500'}`} />
            <span className="text-sm font-semibold tracking-wide" style={{ color: status === 'recording' ? 'var(--recording-red)' : status === 'processing' ? 'var(--warning-yellow)' : 'var(--ready-green)' }}>
              {statusText.toUpperCase()}
            </span>
          </div>

          {/* Template Selection Dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400 font-bold uppercase tracking-wider">Vorlage:</span>
            <select
              value={selectedTemplateKey}
              onChange={e => setSelectedTemplateKey(e.target.value)}
              className="px-3 py-2 rounded-lg border outline-none text-white text-sm font-medium focus:ring-1 focus:ring-purple-500 cursor-pointer"
              style={{ backgroundColor: 'var(--bg-input)', borderColor: 'var(--border-color)' }}
            >
              {Object.keys(templates).map(key => (
                <option key={key} value={key}>
                  {templates[key].display_name}
                </option>
              ))}
            </select>
          </div>

          {/* Settings button */}
          <button 
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 rounded-lg hover:bg-gray-850 text-gray-400 hover:text-white transition-all cursor-pointer"
            title="Einstellungen"
          >
            <Settings size={20} />
          </button>

          {/* Logout button */}
          <button 
            onClick={handleLogout}
            className="p-2 rounded-lg hover:bg-gray-850 text-gray-400 hover:text-red-400 transition-all cursor-pointer"
            title="Abmelden"
          >
            <LogOut size={20} />
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="flex-grow p-6 grid grid-cols-1 lg:grid-cols-2 gap-6" style={{ contentVisibility: 'auto' }}>
        {/* Left Side: Live Transcription & Controls */}
        <section className="glass-panel rounded-2xl border flex flex-col overflow-hidden" style={{ borderColor: 'var(--border-color)' }}>
          <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--border-color)', backgroundColor: 'rgba(22, 25, 44, 0.4)' }}>
            <div className="flex items-center gap-2">
              <Mic size={18} className="text-purple-400" style={{ color: 'var(--accent-purple)' }} />
              <h2 className="text-sm font-bold uppercase tracking-wider text-gray-400">Live-Diktat & Spracherkennung</h2>
            </div>
            <span className="text-xs text-gray-500 font-semibold uppercase font-mono">Engine: {sttEngine.toUpperCase()}</span>
          </div>

          <div className="flex-grow p-5 flex flex-col">
            <textarea
              value={transcript}
              onChange={e => {
                setTranscript(e.target.value);
                const autoKey = detectTemplate(e.target.value);
                if (autoKey !== selectedTemplateKey && templates[autoKey]) {
                  setSelectedTemplateKey(autoKey);
                }
              }}
              placeholder="Hier erscheint das Live-Diktat... Sie können das Diktat auch manuell bearbeiten oder kopieren."
              className="w-full flex-grow bg-transparent text-white font-medium leading-relaxed resize-none border-0 focus:ring-0 outline-none text-base"
            />

            {/* Level meter during recording */}
            {status === 'recording' && (
              <div className="mt-4 p-3 bg-black bg-opacity-20 rounded-lg flex items-center gap-3">
                <span className="text-xs text-gray-400 font-bold uppercase">Pegel</span>
                <div className="flex-grow bg-gray-800 h-2.5 rounded-full overflow-hidden">
                  <div 
                    className="bg-green-500 h-full transition-all duration-75"
                    style={{ width: `${micLevel}%`, backgroundColor: 'var(--ready-green)' }}
                  />
                </div>
                <span className="text-xs font-mono text-gray-400">{micLevel}%</span>
              </div>
            )}

            {/* Micro button & Actions */}
            <div className="mt-5 pt-4 border-t flex items-center justify-between" style={{ borderColor: 'var(--border-color)' }}>
              <div className="flex gap-2">
                <button
                  onClick={handleReset}
                  className="px-4 py-2.5 rounded-lg border text-sm font-semibold hover:bg-gray-800 transition-all text-gray-300 cursor-pointer"
                  style={{ borderColor: 'var(--border-color)' }}
                >
                  Zurücksetzen
                </button>
              </div>

              <div className="flex items-center gap-3">
                {status === 'recording' ? (
                  <button
                    onClick={stopRecording}
                    className="px-6 py-3 bg-red-600 hover:bg-red-750 rounded-xl font-bold text-white flex items-center gap-2 transition-all shadow-lg shadow-red-900/30 cursor-pointer"
                    style={{ backgroundColor: 'var(--recording-red)' }}
                  >
                    <MicOff size={18} /> Aufnahme Stoppen
                  </button>
                ) : (
                  <button
                    onClick={startRecording}
                    disabled={status === 'processing'}
                    className="px-6 py-3 bg-indigo-600 hover:bg-indigo-750 disabled:opacity-50 rounded-xl font-bold text-white flex items-center gap-2 transition-all shadow-lg shadow-indigo-900/30 cursor-pointer"
                    style={{ backgroundColor: 'var(--accent-purple)' }}
                  >
                    <Mic size={18} /> Aufnahme Starten
                  </button>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Right Side: Structured Report */}
        <section className="glass-panel rounded-2xl border flex flex-col overflow-hidden" style={{ borderColor: 'var(--border-color)' }}>
          <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--border-color)', backgroundColor: 'rgba(22, 25, 44, 0.4)' }}>
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-purple-400" style={{ color: 'var(--accent-purple)' }} />
              <h2 className="text-sm font-bold uppercase tracking-wider text-gray-400">Strukturierter Befund</h2>
            </div>
            
            {isCopied && (
              <span className="text-xs px-2.5 py-1 rounded bg-green-950 text-green-300 font-semibold border border-green-800 flex items-center gap-1">
                <Check size={12} /> In Zwischenablage kopiert!
              </span>
            )}
          </div>

          <div className="flex-grow p-5 flex flex-col">
            <textarea
              value={structuredReport}
              readOnly
              placeholder="Der strukturierte Bericht wird nach Abschluss des Diktats hier eingefügt."
              className="w-full flex-grow bg-transparent text-white font-medium leading-relaxed resize-none border-0 focus:ring-0 outline-none text-base"
            />

            <div className="mt-5 pt-4 border-t flex items-center justify-between" style={{ borderColor: 'var(--border-color)' }}>
              <span className="text-xs text-gray-500 font-medium">Kopieren Sie das Ergebnis für RIS oder Word.</span>
              
              <button
                onClick={handleCopyReport}
                disabled={!structuredReport}
                className="px-5 py-2.5 rounded-lg border hover:bg-gray-800 disabled:opacity-50 text-sm font-semibold flex items-center gap-2 text-white transition-all cursor-pointer"
                style={{ borderColor: 'var(--border-color)' }}
              >
                <Copy size={16} /> Befund Kopieren
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* Settings Dialog (Modal) */}
      {showSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center p-6 z-50 overflow-y-auto">
          <div className="glass-panel w-full max-w-2xl p-6 rounded-2xl border space-y-6 max-h-[90vh] overflow-y-auto" style={{ borderColor: 'var(--border-color)' }}>
            <div className="flex items-center justify-between border-b pb-4" style={{ borderColor: 'var(--border-color)' }}>
              <h2 className="text-xl font-bold flex items-center gap-2"><Settings size={22} className="text-purple-400" /> Konfiguration & Schlüssel</h2>
              <button 
                onClick={() => setShowSettings(false)}
                className="text-gray-400 hover:text-white cursor-pointer text-2xl"
              >
                &times;
              </button>
            </div>

            {/* STT Config */}
            <div className="space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-purple-400">1. Spracherkennung (Speech-to-Text)</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <label className="p-3 bg-gray-900 bg-opacity-50 rounded-lg border flex items-center gap-3 cursor-pointer" style={{ borderColor: sttEngine === 'browser' ? 'var(--accent-purple)' : 'var(--border-color)' }}>
                  <input 
                    type="radio" 
                    name="stt_engine" 
                    value="browser"
                    checked={sttEngine === 'browser'}
                    onChange={() => setSttEngine('browser')}
                    className="text-purple-600 focus:ring-purple-500"
                  />
                  <div>
                    <span className="block font-bold text-white text-sm">Browser-Erkennung (Free)</span>
                    <span className="block text-xs text-gray-400">Verwendet eingebaute Browser-STT. Kein API-Schlüssel nötig.</span>
                  </div>
                </label>

                <label className="p-3 bg-gray-900 bg-opacity-50 rounded-lg border flex items-center gap-3 cursor-pointer" style={{ borderColor: sttEngine === 'google' ? 'var(--accent-purple)' : 'var(--border-color)' }}>
                  <input 
                    type="radio" 
                    name="stt_engine" 
                    value="google"
                    checked={sttEngine === 'google'}
                    onChange={() => setSttEngine('google')}
                    className="text-purple-600 focus:ring-purple-500"
                  />
                  <div>
                    <span className="block font-bold text-white text-sm">Google Cloud STT</span>
                    <span className="block text-xs text-gray-400">Sehr präzises medizinisches Diktat. Benötigt Google API-Key.</span>
                  </div>
                </label>
              </div>

              {sttEngine === 'google' && (
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Google Cloud API-Key</label>
                  <input 
                    type="password"
                    value={googleApiKey}
                    onChange={e => setGoogleApiKey(e.target.value)}
                    placeholder="AIzaSy..."
                    className="w-full px-3 py-2 rounded-lg border outline-none text-white text-sm"
                    style={{ backgroundColor: 'var(--bg-input)', borderColor: 'var(--border-color)' }}
                  />
                  <span className="text-xs text-gray-500 mt-1 block">Tipp: Erstellen Sie einen API-Schlüssel in der Google Cloud Console mit Zugriff auf Speech-to-Text.</span>
                </div>
              )}
            </div>

            {/* LLM Config */}
            <div className="space-y-4 border-t pt-4" style={{ borderColor: 'var(--border-color)' }}>
              <h3 className="text-sm font-bold uppercase tracking-wider text-purple-400">2. KI-Strukturierung (LLM)</h3>
              
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Gemini API-Key</label>
                <input 
                  type="password"
                  value={geminiApiKey}
                  onChange={e => setGeminiApiKey(e.target.value)}
                  placeholder="Hinterlegen Sie Ihren Gemini API-Key"
                  className="w-full px-3 py-2 rounded-lg border outline-none text-white text-sm"
                  style={{ backgroundColor: 'var(--bg-input)', borderColor: 'var(--border-color)' }}
                />
                <span className="text-xs text-gray-500 mt-1 block">Für kostenlose Testzwecke können Sie einen Key im Google AI Studio erstellen. Bleibt das Feld leer, läuft ein lokaler Demo-Mock.</span>
              </div>
            </div>

            {/* Prompt Config */}
            <div className="space-y-4 border-t pt-4" style={{ borderColor: 'var(--border-color)' }}>
              <h3 className="text-sm font-bold uppercase tracking-wider text-purple-400">3. System-Prompt konfigurieren</h3>
              <textarea
                value={systemPrompt}
                onChange={e => setSystemPrompt(e.target.value)}
                rows={6}
                className="w-full px-3 py-2 rounded-lg border outline-none text-white text-sm font-mono"
                style={{ backgroundColor: 'var(--bg-input)', borderColor: 'var(--border-color)' }}
              />
            </div>

            {/* Actions */}
            <div className="border-t pt-4 flex items-center justify-between" style={{ borderColor: 'var(--border-color)' }}>
              <span className="text-xs text-yellow-500 flex items-center gap-1">
                <Info size={14} /> Schlüssel werden lokal im Browser secured.
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowSettings(false)}
                  className="px-4 py-2 rounded-lg border text-sm text-gray-400 hover:text-white cursor-pointer"
                  style={{ borderColor: 'var(--border-color)' }}
                >
                  Abbrechen
                </button>
                <button
                  onClick={saveConfig}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-bold text-white flex items-center gap-2 cursor-pointer"
                  style={{ backgroundColor: 'var(--accent-purple)' }}
                >
                  <Save size={16} /> Speichern
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

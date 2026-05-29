/* ═══════════════════════════════════════════════════════════════════
   Voxa AI  ·  app.js  v7.0 — Cotton Candy Skies Theme
   ─────────────────────────────────────────────────────────────────
   REAL-TIME STT SYSTEM:
   ∙ continuous=true  interimResults=true (zero-buffer, live display)
   ∙ Word-by-word animation in dedicated live-transcript zone
ve-transcript zone
   ∙ 1.5s silence detection → auto-finalize → auto-send
   ∙ Smooth text transfer: live-zone → composer → chat bubble
   ∙ Deduplication of interim results (no text scrambling)
   ∙ Auto-reconnect on drop, noise/pause tolerance

   3D PARTICLES & WAVEFORM (Cotton Candy Synthwave colors):
   ∙ Pastel Purple/Cyan/Pink palette
   ═══════════════════════════════════════════════════════════════════ */

/* ─── Config ──────────────────────────────────────────────── */
// Dynamically use the current origin so it works flawlessly through ngrok/localtunnel
const API_BASE = (window.location.port === "5500" || window.location.port === "5501") ? "http://127.0.0.1:8000" : window.location.origin;
const WS_BASE = API_BASE.replace(/^http/, "ws");
const SESSION_ID = `s_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;

/* ─── DOM refs ────────────────────────────────────────────── */
const chatArea       = document.getElementById("chatArea");
const textInput      = document.getElementById("textInput");
const composerWrap   = document.getElementById("composerWrap");
const sendBtn        = document.getElementById("sendBtn");
const micBtn         = document.getElementById("micBtn");
const micHint        = document.getElementById("micHint");
const clearBtn       = document.getElementById("clearBtn");
const systemMessage  = document.getElementById("systemMessage");
const stateBadge     = document.getElementById("stateBadge");
const langBadge      = document.getElementById("langBadge");
const voiceLangSelect = document.getElementById("voiceLangSelect");
const ttftBadge      = document.getElementById("ttftBadge");
const providerLabel  = document.getElementById("providerLabel");
const providerChip   = document.getElementById("providerChip");
const sttLatEl       = document.getElementById("sttLatency");
const llmLatEl       = document.getElementById("llmLatency");
const ttsLatEl       = document.getElementById("ttsLatency");
const totLatEl       = document.getElementById("totalLatency");
const modelNameEl    = document.getElementById("modelName");
const geminiDot      = document.getElementById("geminiDot");
const sarvamDot      = document.getElementById("sarvamDot");
const geminiKeys     = document.getElementById("geminiKeys");
const sarvamKeys     = document.getElementById("sarvamKeys");
const ollamaDot      = document.getElementById("ollamaDot");
const ollamaKeys     = document.getElementById("ollamaKeys");
// OpenAI removed — these are null stubs kept to avoid ReferenceErrors in old code paths
const openaiDot      = null;
const openaiKeys     = null;
const toastContainer = document.getElementById("toastContainer");
const statMessages   = document.getElementById("statMessages");
const statAvgTtft    = document.getElementById("statAvgTtft");
const statLang       = document.getElementById("statLang");
const statModel      = document.getElementById("statModel");
const sidebar        = document.getElementById("sidebar");
const sidebarToggle  = document.getElementById("sidebarToggle");
const waveCanvas     = document.getElementById("waveformCanvas");
const waveGlow       = document.getElementById("waveGlow");
const liveZone       = document.getElementById("liveZone");
const liveText       = document.getElementById("liveText");
const liveWordCount  = document.getElementById("liveWordCount");
const liveConfidence = document.getElementById("liveConfidence");
const particleCanvas = document.getElementById("particleCanvas");
const wCtx           = waveCanvas.getContext("2d");
const pCtx           = particleCanvas.getContext("2d");

/* ─── Global state ────────────────────────────────────────── */
// Auto-detect SESS_LANG from browser locale so Indian-language users don't need
// to click a chip before speaking. Falls back to 'English' if unmapped.
const _BROWSER_LANG_INIT = {
  'kn': 'Kannada', 'mr': 'Marathi', 'bn': 'Bengali', 'te': 'Telugu', 'ta': 'Tamil',
  'hi': 'Hindi',   'gu': 'Gujarati','ml': 'Malayalam','pa': 'Punjabi',
};
let SESS_LANG    = _BROWSER_LANG_INIT[(navigator.language || 'en').split('-')[0]] || "English";
let msgCount     = 0;
let totalTtft    = 0;
let ttftCount    = 0;
let isListening  = false;
let isProcessing = false;
let isSpeaking   = false;
let isProcessingMessage = false; // Turn lock to prevent race conditions
let currentAbortController = null; // Aborts SSE stream on interrupt

/* ─── Transliteration & STT Maps ─────────────────────────── */
// Code-switched (romanized) languages MUST use en-IN so the browser captures
// Latin-script text like "matte hege idira" instead of expecting native script.
// The backend's detect_language() then identifies the true Indian language.
const _CODE_SWITCHED = new Set(["Hinglish", "Kanglish", "Tenglish", "Tamlish"]);

const STT_LANG_MAP = {
  // ── Indian Languages (Native Capture) ────────────────────────────────────
  // We capture in the native script (e.g. hi-IN for perfect Hindi recognition).
  // The 'transliterateIndic' function then converts the Devanagari/Kannada text
  // back to "normal English" (Romanized) for the UI before sending to the backend.
  "Auto":      "en-US",
  "English":   "en-US",
  "Hindi":     "hi-IN",
  "Kannada":   "kn-IN",
  "Marathi":   "mr-IN",
  "Bengali":   "bn-IN",
  "Tamil":     "ta-IN",
  "Telugu":    "te-IN",
  "Gujarati":  "gu-IN",
  "Malayalam": "ml-IN",
  "Punjabi":   "pa-IN",
  "Odia":      "or-IN",
  // Code-switched → en-IN (romanized capture)
  "Hinglish":  "en-IN",
  "Kanglish":  "en-IN",
  "Tenglish":  "en-IN",
  "Tamlish":   "en-IN",
  // European / East Asian — keep native STT for accurate non-romanized capture
  "Spanish":   "es-ES",
  "French":    "fr-FR",
  "German":    "de-DE",
  "Japanese":  "ja-JP",
  "Chinese":   "zh-CN",
  "Arabic":    "ar-SA",
  "Italian":   "it-IT",
  "Russian":   "ru-RU",
  "Korean":    "ko-KR",
  "Portuguese":"pt-BR",
};

// Indian languages must use the Sarvam STT backend for 100% accurate recognition,
// because Chrome's Web Speech API for kn-IN, ta-IN, te-IN etc. is severely broken and often returns no input.
// We capture natively via Sarvam, and transliterate to English for the UI.
const BACKEND_STT_LANGS = [
  'hi-IN', 'kn-IN', 'ta-IN', 'te-IN', 'mr-IN', 
  'bn-IN', 'gu-IN', 'ml-IN', 'pa-IN', 'or-IN'
];

/**
 * Returns the STT provider for the given display language name.
 * Code-switched languages always use webspeech/en-IN for romanized capture.
 * @param {string} language - Display name (e.g. 'Kannada', 'Kanglish')
 * @returns {'backend'|'webspeech'}
 */
function getSTTProvider(language) {
  if (_CODE_SWITCHED.has(language)) return 'webspeech'; // always en-IN romanized
  const code = STT_LANG_MAP[language] || language;
  return BACKEND_STT_LANGS.includes(code) ? 'backend' : 'webspeech';
}

// ── Full Indic + Arabic transliteration map ──────────────────────────────────
const indicMap = {
  // ── DEVANAGARI (Hindi, Marathi) ──────────────────────────────────────────
  'अ':'a','आ':'aa','इ':'i','ई':'ii','उ':'u','ऊ':'uu','ऋ':'ri','ए':'e','ऐ':'ai','ओ':'o','औ':'au',
  'क':'k','ख':'kh','ग':'g','घ':'gh','ङ':'ng','च':'ch','छ':'chh','ज':'j','झ':'jh','ञ':'ny',
  'ट':'t','ठ':'th','ड':'d','ढ':'dh','ण':'n','त':'t','थ':'th','द':'d','ध':'dh','न':'n',
  'प':'p','फ':'ph','ब':'b','भ':'bh','म':'m','य':'y','र':'r','ल':'l','व':'v','श':'sh','ष':'sh','स':'s','ह':'h','ळ':'l',
  'ा':'aa','ि':'i','ी':'ii','ु':'u','ू':'uu','ृ':'ri','े':'e','ै':'ai','ो':'o','ौ':'au','ं':'n','ः':'h','्':'','।':'.','॥':'.',
  // ── KANNADA ──────────────────────────────────────────────────────────────
  'ಅ':'a','ಆ':'aa','ಇ':'i','ಈ':'ii','ಉ':'u','ಊ':'uu','ಋ':'ri','ಎ':'e','ಏ':'e','ಐ':'ai','ಒ':'o','ಓ':'o','ಔ':'au',
  'ಕ':'k','ಖ':'kh','ಗ':'g','ಘ':'gh','ಙ':'ng','ಚ':'ch','ಛ':'chh','ಜ':'j','ಝ':'jh','ಞ':'nj',
  'ಟ':'t','ಠ':'th','ಡ':'d','ಢ':'dh','ಣ':'n','ತ':'t','ಥ':'th','ದ':'d','ಧ':'dh','ನ':'n',
  'ಪ':'p','ಫ':'ph','ಬ':'b','ಭ':'bh','ಮ':'m','ಯ':'y','ರ':'r','ಱ':'r','ಲ':'l','ವ':'v','ಶ':'sh','ಷ':'sh','ಸ':'s','ಹ':'h','ಳ':'l','ೞ':'l',
  'ಾ':'aa','ಿ':'i','ೀ':'ii','ು':'u','ೂ':'uu','ೃ':'ri','ೆ':'e','ೇ':'e','ೈ':'ai','ೊ':'o','ೋ':'o','ೌ':'au','ಂ':'n','ಃ':'h','್':'',
  // ── BENGALI ──────────────────────────────────────────────────────────────
  'অ':'o','আ':'a','ই':'i','ঈ':'ii','উ':'u','ঊ':'uu','ঋ':'ri','এ':'e','ঐ':'oi','ও':'o','ঔ':'ou',
  'ক':'k','খ':'kh','গ':'g','ঘ':'gh','ঙ':'ng','চ':'ch','ছ':'chh','জ':'j','ঝ':'jh','ঞ':'n',
  'ট':'t','ঠ':'th','ড':'d','ঢ':'dh','ণ':'n','ত':'t','থ':'th','দ':'d','ধ':'dh','ন':'n',
  'প':'p','ফ':'ph','ব':'b','ভ':'bh','ম':'m','য':'j','র':'r','ল':'l','শ':'sh','ষ':'sh','স':'s','হ':'h','ড়':'r','ঢ়':'rh','য়':'y','ৎ':'t',
  'া':'a','ি':'i','ী':'ii','ু':'u','ূ':'uu','ৃ':'ri','ে':'e','ৈ':'oi','ো':'o','ৌ':'ou','ং':'ng','ঃ':'h','ঁ':'n','্':'',
  // ── TAMIL (U+0B80–U+0BFF) ────────────────────────────────────────────────
  'அ':'a','ஆ':'aa','இ':'i','ஈ':'ii','உ':'u','ஊ':'uu','எ':'e','ஏ':'ee','ஐ':'ai','ஒ':'o','ஓ':'oo','ஔ':'au',
  'க':'k','ங':'ng','ச':'ch','ஞ':'ny','ட':'t','ண':'n','த':'th','ந':'n','ன':'n',
  'ப':'p','ம':'m','ய':'y','ர':'r','ற':'rr','ல':'l','ள':'ll','ழ':'zh','வ':'v','ஶ':'sh','ஷ':'sh','ஸ':'s','ஹ':'h',
  'ா':'aa','ி':'i','ீ':'ii','ு':'u','ூ':'uu','ெ':'e','ே':'ee','ை':'ai','ொ':'o','ோ':'oo','ௌ':'au','்':'','ஂ':'n',
  // ── TELUGU (U+0C00–U+0C7F) ───────────────────────────────────────────────
  'అ':'a','ఆ':'aa','ఇ':'i','ఈ':'ii','ఉ':'u','ఊ':'uu','ఎ':'e','ఏ':'ee','ఐ':'ai','ఒ':'o','ఓ':'oo','ఔ':'au',
  'క':'k','ఖ':'kh','గ':'g','ఘ':'gh','చ':'ch','జ':'j','ట':'t','డ':'d','త':'th','ద':'d','న':'n',
  'ప':'p','బ':'b','మ':'m','య':'y','ర':'r','ళ':'l','వ':'v','శ':'sh','స':'s','హ':'h','ఱ':'r','ల':'l',
  'థ':'th','ధ':'dh',
  'ా':'aa','ి':'i','ీ':'ii','ు':'u','ూ':'uu','ె':'e','ే':'ee','ై':'ai','ొ':'o','ో':'oo','ౌ':'au','ం':'m','్':'',
  // ── GUJARATI (U+0A80–U+0AFF) ─────────────────────────────────────────────
  'અ':'a','આ':'aa','ઇ':'i','ઈ':'ii','ઉ':'u','ઊ':'uu','એ':'e','ઐ':'ai','ઓ':'o','ઔ':'au',
  'ક':'k','ખ':'kh','ગ':'g','ઘ':'gh','ઙ':'ng','ચ':'ch','છ':'chh','જ':'j','ઝ':'jh','ઞ':'ny',
  'ટ':'t','ઠ':'th','ડ':'d','ઢ':'dh','ણ':'n','ત':'t','થ':'th','દ':'d','ધ':'dh','ન':'n',
  'પ':'p','ફ':'ph','બ':'b','ભ':'bh','મ':'m','ય':'y','ર':'r','લ':'l','ળ':'l','વ':'v','શ':'sh','ષ':'sh','સ':'s','હ':'h',
  'ા':'aa','િ':'i','ી':'ii','ુ':'u','ૂ':'uu','ે':'e','ૈ':'ai','ો':'o','ૌ':'au','ં':'n','ઃ':'h','્':'',
  // ── GURMUKHI / PUNJABI (U+0A00–U+0A7F) ──────────────────────────────────
  'ਅ':'a','ਆ':'aa','ਇ':'i','ਈ':'ii','ਉ':'u','ਊ':'uu','ਏ':'e','ਐ':'ai','ਓ':'o','ਔ':'au',
  'ਕ':'k','ਖ':'kh','ਗ':'g','ਘ':'gh','ਙ':'ng','ਚ':'ch','ਛ':'chh','ਜ':'j','ਝ':'jh','ਞ':'ny',
  'ਟ':'t','ਠ':'th','ਡ':'d','ਢ':'dh','ਣ':'n','ਤ':'t','ਥ':'th','ਦ':'d','ਧ':'dh','ਨ':'n',
  'ਪ':'p','ਫ':'ph','ਬ':'b','ਭ':'bh','ਮ':'m','ਯ':'y','ਰ':'r','ਲ':'l','ਲ਼':'l','ਵ':'v','ਸ਼':'sh','ਸ':'s','ਹ':'h',
  'ਾ':'aa','ਿ':'i','ੀ':'ii','ੁ':'u','ੂ':'uu','ੇ':'e','ੈ':'ai','ੋ':'o','ੌ':'au','ੰ':'n','ਂ':'n','ਃ':'h','੍':'',
  // ── MALAYALAM (U+0D00–U+0D7F) ────────────────────────────────────────────
  'അ':'a','ആ':'aa','ഇ':'i','ഈ':'ii','ഉ':'u','ഊ':'uu','എ':'e','ഏ':'ee','ഐ':'ai','ഒ':'o','ഓ':'oo','ഔ':'au',
  'ക':'k','ഖ':'kh','ഗ':'g','ഘ':'gh','ങ':'ng','ച':'ch','ഛ':'chh','ജ':'j','ഝ':'jh','ഞ':'ny',
  'ട':'t','ഠ':'th','ഡ':'d','ഢ':'dh','ണ':'n','ത':'t','ഥ':'th','ദ':'d','ധ':'dh','ന':'n',
  'പ':'p','ഫ':'ph','ബ':'b','ഭ':'bh','മ':'m','യ':'y','ര':'r','റ':'rr','ല':'l','ള':'l','ഴ':'zh','വ':'v','ശ':'sh','ഷ':'sh','സ':'s','ഹ':'h',
  'ാ':'aa','ി':'i','ീ':'ii','ു':'u','ൂ':'uu','െ':'e','േ':'ee','ൈ':'ai','ൊ':'o','ോ':'oo','ൌ':'au','ൗ':'au','ം':'m','ഃ':'h','്':'',
  // ── ARABIC / URDU ─────────────────────────────────────────────────────────
  '\u0627':'a','\u0628':'b','\u062A':'t','\u062B':'th','\u062C':'j','\u062D':'h','\u062E':'kh',
  '\u062F':'d','\u0630':'dh','\u0631':'r','\u0632':'z','\u0633':'s','\u0634':'sh','\u0635':'s',
  '\u0636':'d','\u0637':'t','\u0638':'z','\u0639':'a','\u063A':'gh','\u0641':'f','\u0642':'q',
  '\u0643':'k','\u0644':'l','\u0645':'m','\u0646':'n','\u0647':'h','\u0648':'w','\u064A':'y',
};

// Auto-detect cycle for when Web Speech returns 'language-not-supported'
const AUTO_DETECT_CYCLE = [
  "hi-IN","ta-IN","te-IN","kn-IN","mr-IN","bn-IN","gu-IN","ml-IN","en-IN"
];
let autoDetectIndex = 0;

// ── Virama (halant) codepoints — they suppress the inherent 'a' of a consonant ──
const _VIRAMAS = new Set([
  0x094D, // Devanagari  ्
  0x09CD, // Bengali     ্
  0x0A4D, // Gurmukhi    ੍
  0x0ACD, // Gujarati    ્
  0x0BCD, // Tamil       ்
  0x0C4D, // Telugu      ్
  0x0CCD, // Kannada     ್
  0x0D4D, // Malayalam   ്
]);

// ── Matra (vowel sign) ranges — explicit vowel follows consonant, no inherent 'a' ──
const _MATRA_RANGES = [
  [0x093E, 0x094C], // Devanagari ा–ौ
  [0x09BE, 0x09CC], // Bengali    া–ৌ
  [0x0A3E, 0x0A4C], // Gurmukhi  ਾ–ੌ
  [0x0ABE, 0x0ACC], // Gujarati  ા–ૌ
  [0x0BBE, 0x0BCC], // Tamil     ா–ௌ
  [0x0C3E, 0x0C4C], // Telugu    ా–ౌ
  [0x0CBE, 0x0CCC], // Kannada   ಾ–ೌ
  [0x0D3E, 0x0D4C], // Malayalam ാ–ൌ
  [0x0D57, 0x0D57], // Malayalam ൗ
];

// ── Consonant codepoint ranges — these need inherent 'a' via look-ahead ──
const _CONS_RANGES = [
  [0x0915, 0x0939], // Devanagari  क–ह
  [0x0933, 0x0933], // Devanagari  ळ
  [0x0958, 0x095F], // Devanagari  qa/xa extended
  [0x0995, 0x09B9], // Bengali     ক–হ
  [0x09DC, 0x09DF], // Bengali     extended
  [0x0A15, 0x0A39], // Gurmukhi   ਕ–ਹ
  [0x0A95, 0x0AB9], // Gujarati   ક–હ
  [0x0AB3, 0x0AB3], // Gujarati   ળ
  [0x0B95, 0x0BB9], // Tamil      க–ஹ
  [0x0C15, 0x0C39], // Telugu     క–హ
  [0x0C31, 0x0C31], // Telugu     ఱ
  [0x0C33, 0x0C33], // Telugu     ళ
  [0x0C95, 0x0CB9], // Kannada    ಕ–ಹ
  [0x0CB1, 0x0CB1], // Kannada    ಱ
  [0x0CB3, 0x0CB3], // Kannada    ಳ
  [0x0D15, 0x0D39], // Malayalam  ക–ഹ
  [0x0D31, 0x0D31], // Malayalam  റ
  [0x0D33, 0x0D33], // Malayalam  ള
  [0x0D34, 0x0D34], // Malayalam  ഴ
];

function _isVirama(code) { return _VIRAMAS.has(code); }
function _isMatra(code)  { return _MATRA_RANGES.some(([s, e]) => code >= s && code <= e); }
function _isCons(code)   { return _CONS_RANGES.some(([s, e]) => code >= s && code <= e); }

/**
 * Transliterates Indic and Arabic script to Latin phonetic approximation.
 * Features:
 *  - Inherent 'a' vowel insertion after bare consonants
 *  - Virama look-ahead to suppress inherent 'a' in consonant clusters
 *  - Matra look-ahead to skip 'a' when an explicit vowel sign follows
 *  - Arabic/Urdu support (U+0600–U+06FF) — NOT skipped by Latin guard
 *  - Pure ASCII/Latin (U+0000–U+05FF) passed through unchanged
 */
function transliterateIndic(str) {
  if (!str) return '';
  const chars = [...str]; // spread handles multi-byte codepoints
  let result = '';
  for (let i = 0; i < chars.length; i++) {
    const char = chars[i];
    const code = char.codePointAt(0);
    // Pure Latin / ASCII / Latin-Extended (< U+0600): pass through unchanged
    if (code < 0x0600) { result += char; continue; }
    // Virama: already consumed by look-ahead below — skip standalone occurrences
    if (_isVirama(code)) continue;
    // Look up in indicMap
    const mapped = indicMap[char];
    if (mapped === undefined) { result += char; continue; }
    result += mapped;
    // Consonant look-ahead: decide whether to append inherent 'a'
    if (_isCons(code) && mapped !== '') {
      const nextCode = (i + 1 < chars.length) ? chars[i + 1].codePointAt(0) : -1;
      if (_isVirama(nextCode)) {
        i++; // consume the virama — suppresses inherent 'a' in cluster
      } else if (!_isMatra(nextCode)) {
        result += 'a'; // no explicit vowel follows → insert inherent 'a'
      }
      // If next is a matra: it will supply the explicit vowel, no 'a' needed
    }
  }
  return result.replace(/\s+/g, ' ').trim();
}

/**
 * Dynamically update the SpeechRecognition language and restart if needed.
 * Called whenever the backend detects a new language mid-session.
 * @param {string} newLang - Display name e.g. "Tamil", "Telugu"
 */
function updateSTTLanguage(newLang) {
  if (!recognition) return; // Web Speech not active
  const langCode = STT_LANG_MAP[newLang] || 'en-IN';
  if (recognition.lang === langCode) return; // already correct

  const wasRunning = isListening && !backendSTTActive;
  if (wasRunning) {
    try { recognition.stop(); } catch (_) {}
  }
  recognition.lang = langCode;
  console.log(`[STT] Dynamic lang update → ${newLang} (${langCode})`);

  if (wasRunning) {
    setTimeout(() => {
      if (!isSpeaking && isListening) {
        try { recognition.start(); } catch (_) {}
      }
    }, 150);
  }
}

/**
 * Update the live-zone transcript display showing native script + romanized hint.
 * @param {string} nativeText - Raw transcript from Web Speech
 * @param {boolean} isFinal - Whether this is a finalized result
 */
function updateTranscriptDisplay(nativeText, isFinal) {
  if (!nativeText) return;
  const transliterated = transliterateIndic(nativeText);
  const hasNativeScript = nativeText !== transliterated;
  if (hasNativeScript) {
    liveText.innerHTML =
      `<span class="native-script" style="display:block;font-size:1.05em">${nativeText}</span>` +
      `<span class="roman-hint" style="display:block;font-size:0.82em;opacity:0.65;margin-top:2px">${transliterated}</span>`;
  } else {
    liveText.textContent = nativeText;
  }
  if (isFinal) liveText.classList.add('final');
}

// Enable clicking Lang Chips to manual force STT hints
document.querySelectorAll('.lang-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    let raw = chip.dataset.lang || chip.textContent.replace('🇮🇳','').replace('🇬🇧','').replace('+14 more','').trim();
    if(raw) {
      SESS_LANG = raw;
      setLangBadge(SESS_LANG);
      if (voiceLangSelect && STT_LANG_MAP[SESS_LANG]) voiceLangSelect.value = SESS_LANG;
      showToast(`Language explicitly set to ${SESS_LANG}`);
      if(isListening) {
        stopListening();
        setTimeout(startListening, 300);
      }
    }
  });
});

if (voiceLangSelect) {
  voiceLangSelect.value = STT_LANG_MAP[SESS_LANG] ? SESS_LANG : "English";
  voiceLangSelect.addEventListener("change", () => {
    const selected = voiceLangSelect.value;
    if (!STT_LANG_MAP[selected]) return;
    SESS_LANG = selected;
    setLangBadge(selected);
    showToast(`Voice input set to ${selected}`);
    if (isListening) {
      stopListening();
      setTimeout(startListening, 300);
    }
  });
}

/* ═══════════════════════════════════════════════════════════
   3D INTERACTIVE PARTICLE SYSTEM
   ═══════════════════════════════════════════════════════════ */
const mouse = { x: -9999, y: -9999 };
document.addEventListener("mousemove", e => { mouse.x = e.clientX; mouse.y = e.clientY; });
document.addEventListener("touchmove", e => {
  mouse.x = e.touches[0].clientX; mouse.y = e.touches[0].clientY;
}, { passive: true });

class Particle {
  constructor() { this.reset(); }
  reset() {
    this.x = (Math.random() - .5) * 2.4;
    this.y = (Math.random() - .5) * 2.4;
    this.z = (Math.random() - .5) * 2.4;
    this.vx = (Math.random() - .5) * .00055;
    this.vy = (Math.random() - .5) * .00055;
    this.vz = (Math.random() - .5) * .00035;
  }
  project(W, H) {
    const fov = 2.4, z = this.z + fov;
    const px  = (this.x / z) * W * .5 + W * .5;
    const py  = (this.y / z) * H * .5 + H * .5;
    const sz  = Math.max(.8, 1.6 / z * 3.2);
    const al  = Math.min(1, .9 / z);
    return { px, py, sz, al, d: 1 / z };
  }
  update(W, H) {
    this.x += this.vx; this.y += this.vy; this.z += this.vz;
    if (this.x >  1.4) this.x = -1.4; if (this.x < -1.4) this.x =  1.4;
    if (this.y >  1.4) this.y = -1.4; if (this.y < -1.4) this.y =  1.4;
    if (this.z >  1.4) this.z = -1.4; if (this.z < -1.4) this.z =  1.4;
    const { px, py } = this.project(W, H);
    const dx = px - mouse.x, dy = py - mouse.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 110) {
      const f = (110 - dist) / 110 * .0022;
      this.vx += (dx / dist) * f; this.vy += (dy / dist) * f;
    }
    this.vx *= .982; this.vy *= .982; this.vz *= .988;
  }
}

let particles = [];
function initParticles() {
  particleCanvas.width  = window.innerWidth;
  particleCanvas.height = window.innerHeight;
  particles = Array.from({ length: 95 }, () => new Particle());
}
function drawParticles() {
  const W = particleCanvas.width, H = particleCanvas.height;
  pCtx.clearRect(0, 0, W, H);

  const proj = particles.map(p => ({ p, ...p.project(W, H) }));

  // Lines (Pastel Purple)
  for (let i = 0; i < proj.length; i++) {
    for (let j = i + 1; j < proj.length; j++) {
      const a = proj[i], b = proj[j];
      const dx = a.px - b.px, dy = a.py - b.py;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 130) {
        const s = 1 - dist / 130;
        const alpha = s * .15 * Math.min(a.al, b.al);
        pCtx.beginPath();
        pCtx.moveTo(a.px, a.py);
        pCtx.lineTo(b.px, b.py);
        pCtx.strokeStyle = `rgba(187,162,232,${alpha})`;
        pCtx.lineWidth   = s * .7;
        pCtx.stroke();
      }
    }
  }
  // Dots
  for (const { px, py, sz, al, d } of proj) {
    const dx = px - mouse.x, dy = py - mouse.y;
    const md = Math.sqrt(dx * dx + dy * dy);
    const isNear = md < 110;
    if (isNear) { pCtx.shadowBlur = 10; pCtx.shadowColor = "rgba(182,226,229,.6)"; }
    else         { pCtx.shadowBlur = 0; }
    
    // Mix purple to cyan based on depth
    const r  = Math.round(187 - d * 5);
    const g_ = Math.round(162 + d * 64);
    const b_ = Math.round(232 - d * 3);
    
    pCtx.beginPath();
    pCtx.arc(px, py, sz, 0, Math.PI * 2);
    pCtx.fillStyle = `rgba(${r},${g_},${b_},${al * .9})`;
    pCtx.fill();
    pCtx.shadowBlur = 0;
  }
  particles.forEach(p => p.update(W, H));
  requestAnimationFrame(drawParticles);
}
window.addEventListener("resize", () => {
  particleCanvas.width  = window.innerWidth;
  particleCanvas.height = window.innerHeight;
});
initParticles();
drawParticles();

/* ═══════════════════════════════════════════════════════════
   HORIZONTAL LINE WAVEFORM (Cotton Candy Synthwave)
   ═══════════════════════════════════════════════════════════ */
let aCtx         = null;
let analyserNode = null;
let micSrcNode   = null;
let wRafId       = null;
let micStreamRef = null;
let idleT        = 0;
let speakT       = 0;

function resizeWave() {
  const el  = waveCanvas.parentElement;
  const dpr = devicePixelRatio || 1;
  const W   = el.clientWidth, H = el.clientHeight;
  waveCanvas.width  = W * dpr; waveCanvas.height = H * dpr;
  waveCanvas.style.width = W + "px"; waveCanvas.style.height = H + "px";
  wCtx.scale(dpr, dpr);
}
window.addEventListener("resize", resizeWave);
resizeWave();

function stopWave() { if (wRafId) { cancelAnimationFrame(wRafId); wRafId = null; } }

/* ── Idle: gentle breathing line (Purple -> Cyan -> Purple) ── */
function drawIdle() {
  if (analyserNode) return;
  const W = waveCanvas.offsetWidth, H = waveCanvas.offsetHeight, cy = H / 2;
  wCtx.clearRect(0, 0, W, H);

  const g = wCtx.createLinearGradient(0, 0, W, 0);
  g.addColorStop(0,    "rgba(187,162,232,0)");
  g.addColorStop(0.15, "rgba(187,162,232,0.45)");
  g.addColorStop(0.5,  "rgba(182,226,229,0.75)");
  g.addColorStop(0.85, "rgba(187,162,232,0.45)");
  g.addColorStop(1,    "rgba(187,162,232,0)");

  wCtx.beginPath();
  for (let x = 0; x <= W; x++) {
    const y = cy + Math.sin(x * .016 + idleT) * 2.8 + Math.sin(x * .032 + idleT * .55) * 1.4;
    x === 0 ? wCtx.moveTo(x, y) : wCtx.lineTo(x, y);
  }
  wCtx.strokeStyle = g; wCtx.lineWidth = 1.5; wCtx.stroke();
  idleT += 0.022;
  wRafId = requestAnimationFrame(drawIdle);
}

/* ── Live mic: amplitude-driven vibrating line ── */
function drawLive() {
  if (!analyserNode) return;
  const W = waveCanvas.offsetWidth, H = waveCanvas.offsetHeight, cy = H / 2;
  const buf = new Float32Array(analyserNode.fftSize);
  analyserNode.getFloatTimeDomainData(buf);

  const rms    = Math.sqrt(buf.reduce((s, v) => s + v * v, 0) / buf.length);
  const energy = Math.min(1, rms * 9);

  wCtx.clearRect(0, 0, W, H);

  const g = wCtx.createLinearGradient(0, 0, W, 0);
  g.addColorStop(0,    "rgba(187,162,232,0)");
  g.addColorStop(0.1,  `rgba(187,162,232,${.45 + energy * .45})`);
  g.addColorStop(0.45, `rgba(182,226,229,${.65 + energy * .35})`);
  g.addColorStop(0.55, `rgba(238,174,202,${.65 + energy * .35})`);
  g.addColorStop(0.9,  `rgba(187,162,232,${.45 + energy * .45})`);
  g.addColorStop(1,    "rgba(187,162,232,0)");

  if (energy > 0.12) { wCtx.shadowBlur = 14 * energy; wCtx.shadowColor = `rgba(182,226,229,${energy * .65})`; }

  wCtx.beginPath();
  const step = W / buf.length;
  for (let i = 0; i < buf.length; i++) {
    const x = i * step, y = cy + buf[i] * cy * .85;
    i === 0 ? wCtx.moveTo(x, y) : wCtx.lineTo(x, y);
  }
  wCtx.strokeStyle = g; wCtx.lineWidth = 1.8 + energy * 1.2; wCtx.stroke();
  wCtx.shadowBlur  = 0;
  wRafId = requestAnimationFrame(drawLive);
}

/* ── Speaking: animated pink/cyan wave ── */
function drawSpeaking() {
  if (analyserNode) return;
  const W = waveCanvas.offsetWidth, H = waveCanvas.offsetHeight, cy = H / 2;
  wCtx.clearRect(0, 0, W, H);

  const g = wCtx.createLinearGradient(0, 0, W, 0);
  g.addColorStop(0,    "rgba(238,174,202,0)");
  g.addColorStop(0.15, "rgba(238,174,202,0.7)");
  g.addColorStop(0.5,  "rgba(182,226,229,1)");
  g.addColorStop(0.85, "rgba(238,174,202,0.7)");
  g.addColorStop(1,    "rgba(238,174,202,0)");

  const amp = 16 * Math.abs(Math.sin(speakT * .55)) + 4;
  wCtx.shadowBlur = 12; wCtx.shadowColor = "rgba(182,226,229,.55)";
  wCtx.beginPath();
  for (let x = 0; x <= W; x++) {
    const y = cy + Math.sin(x * .026 + speakT) * amp + Math.sin(x * .05 + speakT * 1.25) * (amp * .4);
    x === 0 ? wCtx.moveTo(x, y) : wCtx.lineTo(x, y);
  }
  wCtx.strokeStyle = g; wCtx.lineWidth = 2; wCtx.stroke();
  wCtx.shadowBlur = 0;
  speakT += .07;
  wRafId = requestAnimationFrame(drawSpeaking);
}

async function startMicWave(stream) {
  try {
    if (aCtx && aCtx.state === 'suspended') await aCtx.resume();
    
    if (!micSrcNode) { 
        micSrcNode = aCtx.createMediaStreamSource(stream); 
    }
    // Always disconnect old routing safely before reconnecting
    try { micSrcNode.disconnect(); } catch(e){}
    micSrcNode.connect(analyserNode);
    
    stopWave(); waveGlow.classList.add("on"); drawLive();
  } catch (e) { console.warn("Web Audio:", e); }
}

function stopMicWave() {
  if (micSrcNode) { 
      try { micSrcNode.disconnect(); } catch(e){} 
      // Do NOT set micSrcNode = null. Keep the wrapper alive to prevent Chrome audio crashes.
  }
  waveGlow.classList.remove("on");
  stopWave(); drawIdle();
}

function getAvgVolume() {
  if (!analyserNode) return 0;
  const data = new Uint8Array(analyserNode.frequencyBinCount);
  analyserNode.getByteFrequencyData(data);
  let sum = 0;
  for (let i = 0; i < data.length; i++) sum += data[i];
  return sum / data.length / 255;
}

/* ═══════════════════════════════════════════════════════════
   LIVE TRANSCRIPT ZONE HELPERS
   ═══════════════════════════════════════════════════════════ */
let liveWords       = [];
let interimSeen     = new Set();
let wordCount       = 0;
// Span cache for flicker-free incremental rendering
let _liveSpans      = [];

function showLiveZone() { liveZone.classList.add("active"); }
function hideLiveZone() {
  liveZone.classList.remove("active");
  liveText.innerHTML = "";
  liveWords = []; wordCount = 0; interimSeen.clear();
  _liveSpans = []; // clear span cache
  liveWordCount.textContent  = "";
  liveConfidence.textContent = "";
  interimAccum = "";
  _stopSilenceCountdown();
  // reset glow
  const liveInner = liveZone.querySelector('.live-zone-inner');
  if (liveInner) liveInner.classList.remove('has-speech', 'counting');
}

/**
 * Robust incremental live-word renderer.
 * Syncs an array of DOM spans to the finalWords array.
 * Updates text in-place to prevent layout thrashing and flicker.
 */
function renderLiveWords(finalText, interimText) {
  const finalWords = finalText.trim() ? finalText.trim().split(/\s+/) : [];
  const liveInner  = liveZone.querySelector('.live-zone-inner');

  // Active-speech glow
  if (liveInner) {
    liveInner.classList.toggle('has-speech', finalWords.length > 0 || !!interimText.trim());
  }

  // 1. Sync span elements to match the exact length of finalWords
  while (_liveSpans.length < finalWords.length) {
    const s = document.createElement("span");
    s.className = "live-word";
    // Insert before the interim span if it exists
    const interimSpan = document.getElementById('live-interim-span');
    liveText.insertBefore(s, interimSpan || null);
    _liveSpans.push(s);
  }
  while (_liveSpans.length > finalWords.length) {
    const s = _liveSpans.pop();
    s.remove();
  }

  // 2. Update text content of all final spans
  for (let i = 0; i < finalWords.length; i++) {
    const newText = finalWords[i] + " ";
    if (_liveSpans[i].textContent !== newText) {
      _liveSpans[i].textContent = newText;
    }
  }

  // 3. Update interim section (single element, updated in-place)
  let interimSpan   = document.getElementById('live-interim-span');
  const trimmedInt  = interimText.trim();
  if (trimmedInt) {
    if (!interimSpan) {
      interimSpan    = document.createElement("span");
      interimSpan.id = 'live-interim-span';
      liveText.appendChild(interimSpan);
    }
    interimSpan.textContent = trimmedInt + " ";
  } else if (interimSpan) {
    interimSpan.remove();
  }

  // 4. Update Word count & Scroll
  const intWordCount = trimmedInt ? trimmedInt.split(/\s+/).filter(Boolean).length : 0;
  wordCount = finalWords.length + intWordCount;
  liveWordCount.textContent = wordCount > 0 ? `${wordCount} word${wordCount !== 1 ? "s" : ""}` : "";

  const inner = liveZone.querySelector(".live-zone-inner");
  if (inner) inner.scrollTop = inner.scrollHeight;
}

// Show BOTH — interim as italic purple, final as solid white
function updateTranscriptUI(finalText, interimText) {
  if (finalText) {
    if (finalAccum && !finalAccum.endsWith(' ') && !finalText.startsWith(' ')) {
      finalAccum += ' ';
    }
    finalAccum += finalText;
    interimAccum = ""; // final supersedes interim for silence timer
  }
  if (interimText) {
    interimAccum = interimText; // keep latest interim for silence timer
  }
  // IMPORTANT: always pass the LIVE interimText (not interimAccum) so
  // words appear as the user speaks, not just after they finish a phrase
  renderLiveWords(finalAccum, interimText);
}

/* ═══════════════════════════════════════════════════════════
   REAL-TIME STT ENGINE
   ═══════════════════════════════════════════════════════════ */
let recognition        = null;
let manualStop         = false;
let restartCount       = 0;
let lastRestartWindow  = 0;
const MAX_RESTARTS     = 30;  // raised from 12 — prevents premature stop across multi-turn sessions
let finalAccum         = "";
let interimAccum       = "";         // tracks latest interim for silence timer
let silenceTimer       = null;
// Silence gate — short enough to feel snappy, long enough to avoid clipping
const SILENCE_MS_DEFAULT  = 1500;   // 1.5s — was 2.2s (saves ~700ms per turn)
const SILENCE_MS_ENGLISH  = 900;    // 0.9s — was 1.4s (English is faster-paced)
let sttStartTime          = 0;

// Track highest result index already accumulated as final (prevents duplicates)
let _maxSeenResultIdx = -1;

function getSilenceMs() {
  // Sentence-ending punctuation → fire faster, but not so fast that it cuts off natural pauses (was 700ms)
  const text = (finalAccum + " " + interimAccum).trim();
  if (/[.!?।॥]$/.test(text)) return 1400;
  return SESS_LANG === "English" ? SILENCE_MS_ENGLISH : SILENCE_MS_DEFAULT;
}

/* ── Countdown bar animation ── */
function _startSilenceCountdown(durationMs) {
  const bar   = document.getElementById('liveCountdownBar');
  const inner = liveZone.querySelector('.live-zone-inner');
  if (!bar || !inner) return;
  inner.classList.add('counting');
  bar.style.transition = 'none';
  bar.style.transform  = 'scaleX(1)';
  bar.offsetHeight; // force reflow
  bar.style.transition = `transform ${durationMs}ms linear`;
  bar.style.transform  = 'scaleX(0)';
}
function _stopSilenceCountdown() {
  const bar   = document.getElementById('liveCountdownBar');
  const inner = liveZone.querySelector('.live-zone-inner');
  if (bar)   { bar.style.transition = 'none'; bar.style.transform = 'scaleX(1)'; }
  if (inner) inner.classList.remove('counting');
}

function clearSilenceTimer() {
  if (silenceTimer) { clearTimeout(silenceTimer); silenceTimer = null; }
  _stopSilenceCountdown();
}

function submitVisibleTranscript() {
  const textToSend = getCurrentTranscript();
  if (!textToSend) {
    stopListening();
    return;
  }
  if (backendSTTActive) stopBackendSTT(false, false);
  finalizeSpeech(textToSend);
}

function armSilenceTimer() {
  clearSilenceTimer();
  // ★ Arm on EITHER final OR interim text — Chrome often never fires isFinal for short phrases
  const textToSend = getCurrentTranscript();
  if (!textToSend) return;
  const ms = getSilenceMs();
  _startSilenceCountdown(ms);
  silenceTimer = setTimeout(() => finalizeSpeech(textToSend), ms);
}

function getCurrentTranscript() {
  return (liveText?.textContent || finalAccum || interimAccum || "").trim();
}

function finalizeSpeech(text) {
  clearSilenceTimer();
  interimAccum = ""; // always clear on finalize
  if (!text.trim()) { hideLiveZone(); return; }
  const sttMs = Date.now() - sttStartTime;
  stopListening();
  // Clean transcript
  const clean = text
    .replace(/\|+/g, " ")             // pipe chars → space
    .replace(/[।॥]+/g, " ")           // Devanagari danda artefacts
    .replace(/\s{2,}/g, " ")          // collapse multiple spaces
    .trim();
  // Auto-capitalize: STT engines return lowercase first letters (e.g. "now what we'll do")
  // Only capitalize when first char is a letter — don't alter Indic scripts or numbers
  const exactTranscript = clean;

  const detectedScript = (!_CODE_SWITCHED.has(SESS_LANG) && getSTTProvider(SESS_LANG) === 'backend')
    ? (STT_LANG_MAP[SESS_LANG] || null)
    : null;

  if (!exactTranscript) { hideLiveZone(); return; }
  hideLiveZone();
  textInput.value = exactTranscript;
  composerWrap.classList.remove("voice-fill"); void composerWrap.offsetWidth;
  composerWrap.classList.add("voice-fill");
  processMessage(exactTranscript, sttMs, true, detectedScript);
  setTimeout(() => {
    textInput.value = ""; composerWrap.classList.remove("voice-fill");
  }, 450);
}

function buildRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;
  const r = new SR();
  r.continuous      = true;        // keep listening
  r.interimResults  = true;        // live updates as user speaks
  r.maxAlternatives = 1;           // use top-1 hypothesis; alternatives add noise

  // Capture in native script for maximum STT accuracy
  r.lang = STT_LANG_MAP[SESS_LANG] || 'en-IN';
  console.log(`[STT] Recognition built for lang=${r.lang} (SESS_LANG=${SESS_LANG})`);

  // Reset dedup tracker & span cache per recognition session
  _maxSeenResultIdx = -1;
  _liveSpans        = [];

  r.onstart = () => { sttStartTime = Date.now(); };

  r.onresult = (event) => {
    sttStartTime = Date.now(); // Reset latency timer while user is still speaking
    let interim = "";
    let final   = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        // Only accumulate each result index once — Chrome can re-fire finals
        if (i > _maxSeenResultIdx) {
          final += transcript;
          _maxSeenResultIdx = i;
        }
      } else {
        interim += transcript;
      }
    }

    // ★ CRITICAL: Transliterate to Normal English so the transcript box NEVER shows native scripts!
    updateTranscriptUI(final, interim);

    // Confidence display
    const lastResult = event.results[event.results.length - 1];
    const displayConf = lastResult[0].confidence || 0;
    if (displayConf > 0) {
      liveConfidence.textContent = `${Math.round(displayConf * 100)}% confidence`;
      liveConfidence.style.color = displayConf > 0.85 ? "var(--ok)" : displayConf > 0.65 ? "var(--warn)" : "var(--err)";
    }
    armSilenceTimer();
  };

  r.onerror = (e) => {
    if (e.error === "aborted" || manualStop) return;
    if (e.error === "not-allowed") { setMsg("Microphone permission denied.", "error"); stopListening(); return; }
    if (e.error === "no-speech") { safeRestart(); return; }
    safeRestart();
  };
  // Guard: do not restart recognition while TTS audio is playing, or if it's a stale instance
  r.onend = () => { 
    if (r !== recognition) return;
    if (!isListening || manualStop || isSpeaking) return; 
    safeRestart(); 
  };
  return r;
}

/* ═══════════════════════════════════════════════════════════
   TRANSCRIPT MERGER
   ═══════════════════════════════════════════════════════════ */
class TranscriptMerger {
  constructor() {
    this.reset();
  }

  reset() {
    this.webSpeechFinal = "";
    this.webSpeechInterim = "";
    this.backendFinal = "";
    this.backendInterim = "";
  }

  pushBackendSentence(sentenceObj) {
    if (sentenceObj.final) {
      if (sentenceObj.text) {
        this.backendFinal += (this.backendFinal ? " " : "") + sentenceObj.text;
      }
      this.backendInterim = ""; // clear interim
    } else {
      // It's an interim sentence, update backendInterim
      if (sentenceObj.text) {
        this.backendInterim = sentenceObj.text;
      }
    }
  }
  
  pushBackendWord(w) {
    // Only append to interim if we are still building word by word (legacy support)
    // Actually, with the new interim sentence, we can just replace backendInterim
    // But let's leave it as is, or maybe not needed if we use sentence for interim
    this.backendInterim += (this.backendInterim ? " " : "") + w.word;
  }

  updateWebSpeech(finalTxt, interimTxt) {
    if (finalTxt) this.webSpeechFinal += (this.webSpeechFinal ? " " : "") + finalTxt;
    this.webSpeechInterim = interimTxt;
  }

  getDisplayState() {
    // If backend has finalized text, we MUST use backend entirely to avoid overlap,
    // because backend chunks and web-speech chunks finalize at different times.
    // If backend hasn't finalized anything yet, we can show Web Speech.
    if (this.backendFinal) {
        return {
            final: this.backendFinal,
            interim: this.backendInterim
        };
    } else {
        return {
            final: this.webSpeechFinal,
            interim: this.webSpeechInterim || this.backendInterim
        };
    }
  }
}

const transcriptMerger = new TranscriptMerger();

/* ═══════════════════════════════════════════════════════════
   VAD HANDLER
   ═══════════════════════════════════════════════════════════ */
class VADHandler {
  constructor() {
    this.node = null;
    this.onSpeechStart = null;
    this.onSpeechEnd = null;
    this.onVolume = null;
    this.moduleLoaded = false;
  }

  async setup(aCtx, stream) {
    if (this.node) return;
    
    try {
      if (!this.moduleLoaded) {
        await aCtx.audioWorklet.addModule('./vad-processor.js');
        this.moduleLoaded = true;
      }
      // Re-use the globally created micSrcNode instead of creating a 3rd instance
      // which would trigger an InvalidStateError in WebKit/Blink browsers.
      this.node = new AudioWorkletNode(aCtx, 'vad-processor');
      
      this.node.port.onmessage = (event) => {
        const data = event.data;
        if (data.type === 'speech_start' && this.onSpeechStart) {
          this.onSpeechStart();
        } else if (data.type === 'speech_end' && this.onSpeechEnd) {
          this.onSpeechEnd();
        } else if (data.type === 'volume' && this.onVolume) {
          this.onVolume(data.rms);
        }
      };
      
      if (typeof micSrcNode !== 'undefined' && micSrcNode) {
        micSrcNode.connect(this.node);
      } else {
        const source = aCtx.createMediaStreamSource(stream);
        source.connect(this.node);
      }
      // Do NOT connect this.node to aCtx.destination to prevent feedback
    } catch (e) {
      console.warn('[VAD] Setup failed:', e);
    }
  }

  disconnect() {
    if (this.node) {
      try { this.node.port.close(); } catch(e){}
      this.node.disconnect();
      this.node = null;
    }
  }
}

const vadHandler = new VADHandler();

function safeRestart() {
  // ★ CRITICAL: Never restart recognition while TTS is playing — this is the
  // root cause of the mic cutting into the AI's voice output.
  if (manualStop || !isListening || isSpeaking) return;
  const now = Date.now();
  if (now - lastRestartWindow > 30000) { restartCount = 0; lastRestartWindow = now; }
  if (++restartCount > MAX_RESTARTS) { setMsg("Recognition stopped.", "error"); stopListening(); return; }

  // BUG FIX: Reset sttStartTime on restart so we don't show cumulative 18s latency
  sttStartTime = Date.now();

  setTimeout(() => {
    // Double-check isSpeaking inside the timeout too — audio may still be going
    if (!isListening || manualStop || isSpeaking) return;
    try { recognition.start(); } catch (_) {}
  }, 250);
}

function startListening() {
  if (isListening) return;
  // ★ INTERRUPT MODE: if AI is thinking or speaking, abort it immediately and listen.
  if (isSpeaking || isProcessingMessage) {
    if (currentAbortController) {
       currentAbortController.abort();
       currentAbortController = null;
    }
    audioQueue.stop();
    isSpeaking = false;
    _resetProcessingLock();
    setMsg("");
  }
  
  // Track latency pipeline
  const lat_vad = document.getElementById('dbgVad');
  const lat_web = document.getElementById('dbgWeb');
  const lat_bend = document.getElementById('dbgBend');
  const lat_merge = document.getElementById('dbgMerge');
  if(lat_vad) lat_vad.textContent = '0ms';
  if(lat_web) lat_web.textContent = '—';
  if(lat_bend) lat_bend.textContent = '—';
  if(lat_merge) lat_merge.textContent = '—';

  finalAccum = ""; interimAccum = ""; manualStop = false; isListening = true;
  restartCount = 0; lastRestartWindow = Date.now();
  _maxSeenResultIdx = -1;
  _liveSpans        = [];
  transcriptMerger.reset();
  renderLiveWords("", ""); showLiveZone(); setAppState("listening"); setMsg("Listening… speak now");

  // Watchdog: ONLY for backend STT (Indian langs). If stuck in listening state
  // with MediaRecorder no longer active for 12s, something went wrong — reset cleanly.
  // CRITICAL: must NOT run for English/Web Speech path where backendSTTActive is always false.
  if (getSTTProvider(SESS_LANG) === 'backend') {
    setTimeout(() => {
      if (isListening && !backendSTTActive && !isProcessingMessage) {
        console.warn('[Watchdog] Backend STT stuck without active recorder — force resetting');
        stopListening();
      }
    }, 12000);
  }

  // CRITICAL FIX: To satisfy Chrome's strict Autoplay Policy, the AudioContext
  // MUST be instantiated or resumed *synchronously* in the click event stack frame.
  if (!aCtx) {
      aCtx = new (window.AudioContext || window.webkitAudioContext)();
      // ★ CRITICAL: Expose on window so AudioQueue._ctx() can share THIS unlocked
      // context instead of creating a new one that starts in 'suspended' state.
      window.aCtx = aCtx;
      analyserNode = aCtx.createAnalyser();
      analyserNode.fftSize = 2048;
      analyserNode.smoothingTimeConstant = 0.80;
  }
  // Keep window.aCtx in sync (in case aCtx was created before we added this line)
  if (!window.aCtx) window.aCtx = aCtx;
  if (aCtx.state === 'suspended') { try{ aCtx.resume(); } catch(_) {} }

  const provider = getSTTProvider(SESS_LANG);
  const langCode = STT_LANG_MAP[SESS_LANG] || 'en-IN';

  // ★ KEY FIX: Reuse existing mic stream across turns instead of calling getUserMedia each time.
  // This prevents Chrome from silently failing/returning broken tracks on repeated calls.
  const _existingStream = micStreamRef && micStreamRef.getTracks().every(t => t.readyState === 'live')
    ? Promise.resolve(micStreamRef)
    : navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
      });

  _existingStream
    .then(async stream => {
      micStreamRef = stream;
      await startMicWave(stream);
      sttStartTime = Date.now(); // Reset every turn
      
      // Setup Dual-Stream pipeline
      if (provider === 'backend') {
        startBackendSTT(stream, langCode);
        backendWsHandler.connect(langCode);
        
        await vadHandler.setup(aCtx, stream);
        vadHandler.onSpeechStart = () => {
          if (lat_vad && lat_vad.textContent === '0ms') lat_vad.textContent = `${Date.now() - sttStartTime}ms`;
        };
        vadHandler.onSpeechEnd = () => {
           submitVisibleTranscript();
        };

        // Wire WS updates to UI
        backendWsHandler.onWord = (w) => {
          if (lat_bend && lat_bend.textContent === '—') lat_bend.textContent = `${Date.now() - sttStartTime}ms`;
          transcriptMerger.pushBackendWord(w);
          const state = transcriptMerger.getDisplayState();
          
          renderLiveWords(state.final, state.interim);
          interimAccum = state.interim;
        };
        backendWsHandler.onSentence = (s) => {
          if (lat_merge) lat_merge.textContent = `${Date.now() - sttStartTime}ms`;
          transcriptMerger.pushBackendSentence(s);
          const state = transcriptMerger.getDisplayState();
          
          renderLiveWords(state.final, state.interim);
          finalAccum = state.final;
          interimAccum = state.interim;
          
          // Guard: only finalize once — backendWsHandler fires onSentence for
          // every intermediate sentence. Only fire when we're still listening
          // to avoid a double-processMessage call from a stale WS message.
          if (s.final && finalAccum.trim() && isListening && !isProcessingMessage && !backendFinalizing && !backendSTTActive) {
            finalizeSpeech(finalAccum.trim());
          }
        };
      } else {
        recognition = buildRecognition();
        // FIX: Delay start by 120ms so Chrome can finish cleaning up the previous
        // session. Calling start() immediately after stop() throws InvalidStateError
        // (caught silently), which leaves isListening=true but recognition never running.
        setTimeout(() => {
          if (!isListening || manualStop || isSpeaking) return;
          try { recognition.start(); } catch (e) {
            console.warn('[STT] start() failed, retrying in 300ms:', e.message);
            setTimeout(() => {
              if (!isListening || manualStop || isSpeaking) return;
              try { recognition.start(); } catch (_) {}
            }, 300);
          }
        }, 120);
      }
    }).catch(err => {
      isListening = false; setAppState("ready"); hideLiveZone(); setMsg(`Mic error: ${err.message}`, "error");
    });
}

function stopListening() {
  if (!isListening) return;
  isListening = false; manualStop = true; clearSilenceTimer();
  setAppState("ready"); hideLiveZone();
  // FIX: Use abort() instead of stop() — abort() is synchronous and prevents the
  // delayed onend event that causes a stale safeRestart() call on the next turn.
  try { recognition?.abort(); } catch (_) {}
  stopBackendSTT();
  backendWsHandler.disconnect();
  vadHandler.disconnect();
  // Keep micStreamRef alive across turns (don't stop tracks) to prevent Chrome
  // from returning broken tracks on repeated getUserMedia calls.
  stopMicWave();
}

/* ═══════════════════════════════════════════════════════════
   DUAL-STREAM ARCHITECTURE CLASSES (VAD & WEBSOCKET)
   ═══════════════════════════════════════════════════════════ */

class BackendStreamHandler {
  constructor() {
    this.ws = null;
    this.onWord = null;
    this.onSentence = null;
    this.onError = null;
    this.reconnectAttempts = 0;
    // FIX: generation counter prevents stale onclose handlers from a previous
    // connection from firing callbacks after a new connection is already open.
    this._generation = 0;
  }

  connect(langCode) {
    // FIX: Also block on CLOSING state — prevents creating a new WS while the
    // old one is mid-close, which causes two instances fighting for the same session.
    if (this.ws && (this.ws.readyState === WebSocket.CONNECTING ||
                    this.ws.readyState === WebSocket.OPEN ||
                    this.ws.readyState === WebSocket.CLOSING)) {
      return;
    }
    
    const gen = ++this._generation; // capture this connection's generation
    const wsUrl = `${WS_BASE}/ws/stt`;
    
    try {
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        if (this._generation !== gen) return; // stale, ignore
        console.log('[WebSocket STT] Connected');
        this.reconnectAttempts = 0;
        if (langCode) {
          this.ws.send(`language:${langCode}`);
        }
      };
      
      this.ws.onmessage = (event) => {
        if (this._generation !== gen) return; // stale, ignore
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'word' && this.onWord) {
            this.onWord(data);
          } else if (data.type === 'sentence' && this.onSentence) {
            this.onSentence(data);
          } else if (data.type === 'error' && this.onError) {
            this.onError(data.message);
          }
        } catch (e) {
          console.warn('[WebSocket STT] Error parsing message', e);
        }
      };
      
      this.ws.onclose = () => {
        if (this._generation !== gen) return; // stale close from old connection — ignore
        console.log('[WebSocket STT] Disconnected');
        // CASE 1: Normal reconnect — only when actively listening and recording
        if (isListening && backendSTTActive && !isProcessingMessage && this.reconnectAttempts < 3) {
          this.reconnectAttempts++;
          setTimeout(() => this.connect(langCode), 1000 * this.reconnectAttempts);
          return;
        }
        // CASE 2: WS closed after forceStop() — waiting for sentence but WS died
        if (!backendSTTActive && isListening && !isProcessingMessage) {
          console.warn('[WebSocket STT] Closed after forceStop with no sentence — recovering');
          if (finalAccum.trim()) {
            finalizeSpeech(finalAccum.trim());
          } else {
            stopListening();
          }
          return;
        }
        // CASE 3: WS closed while thinking with no transcript
        if (isProcessingMessage && !finalAccum.trim()) {
          console.warn('[WebSocket STT] Closed with no transcript while thinking — resetting state');
          _resetProcessingLock();
          isSpeaking = false;
          setAppState('ready');
          setMsg('Ready — tap mic to speak again.');
          if (isListening) stopListening();
          return;
        }
        // CASE 4: Reconnects exhausted — give up and reset fully
        if (isListening && !isProcessingMessage && this.reconnectAttempts >= 3) {
          console.warn('[WebSocket STT] Reconnects exhausted — resetting state');
          stopListening();
        }
      };
      
    } catch (e) {
      console.error('[WebSocket STT] Connection failed', e);
      if (this.onError) this.onError(e.message);
    }
  }

  sendAudioChunk(blob) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN && blob.size > 0) {
      this.ws.send(blob);
    }
  }

  forceStop() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send('stop');
    }
  }

  disconnect() {
    // Bump generation so any in-flight onclose/onmessage from the old connection are ignored
    this._generation++;
    this.reconnectAttempts = 0;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

const backendWsHandler = new BackendStreamHandler();

/* ── Debug Latency Overlay Toggle ── */
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key.toLowerCase() === 'd') {
    e.preventDefault();
    const overlay = document.getElementById('debugOverlay');
    if (overlay) overlay.classList.toggle('hidden');
  }
});

/* ═══════════════════════════════════════════════════════════
   BACKEND STT — MediaRecorder path for Indian languages
   (kn-IN, mr-IN, bn-IN, te-IN, ta-IN)
   ═══════════════════════════════════════════════════════════ */
/** @type {MediaRecorder|null} */
let backendMediaRecorder = null;
/** @type {SpeechRecognition|null} Parallel Web Speech instance for live display during backend STT */
let _displayRecognition = null;
/** @type {number|null} Timer ID for silence-detection polling */
let backendChunkTimer    = null;
/** @type {Blob[]} Audio chunks buffered since last finalization */
let backendAudioChunks   = [];
/** @type {string} BCP-47 language code for the current backend session */
let backendLangCode      = 'kn-IN';
/** @type {boolean} True while startBackendSTT() has an active recorder */
let backendSTTActive     = false;
/** @type {boolean} True while final Sarvam/Whisper HTTP transcript is pending */
let backendFinalizing    = false;
const FINAL_STT_TIMEOUT_MS = 3500;
/** @type {number|null} Safety timeout — resets isProcessingMessage if onend never fires */
let _processingLockTimeout = null;

/**
 * Reset the isProcessingMessage lock safely from any code path.
 * Cancels the safety timer and restores the ready state.
 */
function _resetProcessingLock() {
  isProcessingMessage = false;
  if (_processingLockTimeout) { clearTimeout(_processingLockTimeout); _processingLockTimeout = null; }
}

/**
 * Arm a 30-second safety timeout so the UI is never permanently locked
 * if audioQueue.onend never fires (e.g. TTS returned no audio chunks).
 */
function _armProcessingLockTimeout() {
  if (_processingLockTimeout) clearTimeout(_processingLockTimeout);
  _processingLockTimeout = setTimeout(() => {
    if (isProcessingMessage) {
      // Only fires when a turn is genuinely stuck (server crash, network failure).
      // Normal TTS can take up to ~20s for long responses — do NOT fire earlier.
      console.warn('[Lock] Safety timeout (45s) fired — resetting stuck turn');
      _resetProcessingLock();
      isSpeaking = false;
      audioQueue.stop();
      setAppState('ready');
      setMsg('Ready — tap Mic to speak or type below.');
      // Do NOT call startListening() here — onTurnComplete() handles that.
      // If we start listening now the mic opens while audio may still be generating.
    }
  }, 45000);  // 45s — only trips on a truly stuck turn, not slow TTS
}

/**
 * ★ Unified turn-completion handler for ALL voice turns.
 * Called from audioQueue.onend (audio path) AND from processMessage
 * when 'done' arrives with no audio (text-only / TTS fallback).
 * Resets all locks, restores state, and auto-restarts listening.
 */
function onTurnComplete() {
  isSpeaking = false;
  _resetProcessingLock();
  // Remove speaking highlight from all AI bubbles
  document.querySelectorAll('.message-ai.is-speaking').forEach(el => el.classList.remove('is-speaking'));
  setAppState('ready');
  setMsg('Done — tap mic to speak again.');
  // ★ FIX: Add a 400ms buffer after audio ends so the LAST syllable of the AI
  // response is fully played out before the mic re-opens.
  // The previous 650ms was enough for restart scheduling but didn't prevent
  // recognition.onend from firing and calling safeRestart() mid-audio.
  setTimeout(() => {
    if (!isListening && !isProcessingMessage && !isSpeaking) startListening();
  }, 400);  // was 900ms — shorter gap between AI finishing and mic re-opening
}

/**
 * Starts MediaRecorder-based audio capture and streams 2-second chunks to
 * POST /stt/stream for Sarvam ASR (Tier 1) / faster-whisper (Tier 2).
 *
 * The 800/1200ms silence timer (armSilenceTimer) still gates the final
 * transcript dispatch — we only accumulate interim results here.
 *
 * Falls back to Web Speech API if MediaRecorder is not supported.
 *
 * @param {MediaStream} stream - Already-acquired getUserMedia stream.
 * @param {string}      langCode - BCP-47 code, e.g. 'kn-IN'.
 */
function startBackendSTT(stream, langCode) {
  if (!window.MediaRecorder) {
    showToast('⚠️ MediaRecorder not supported — switching to browser STT (reduced accuracy)', 'info', 5000);
    console.warn('[BackendSTT] MediaRecorder unsupported, falling back to Web Speech API');
    recognition = buildRecognition();
    try { recognition.start(); } catch (_) {}
    return;
  }

  backendLangCode    = langCode;
  backendAudioChunks = [];
  backendSTTActive   = true;

  // The mic stream is already connected to AnalyserNode inside startMicWave().
  // Doing it again here would throw an InvalidStateError and break VAD.
  const mimeType = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/ogg',
  ].find(t => MediaRecorder.isTypeSupported(t)) || '';

  console.log(`[BackendSTT] Starting MediaRecorder lang=${langCode} mime=${mimeType || 'default'}`);

  backendMediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});

  backendMediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) {
      backendAudioChunks.push(e.data);
      // Dual-stream: send chunk immediately to WebSocket for faster-whisper
      backendWsHandler.sendAudioChunk(e.data);
    }
  };

  let silenceFrames   = 0;
  let speakingFrames  = 0; // track how long the user has spoken
  const MIN_SPEAKING_FRAMES = 8; // require at least 0.8s of speech before finalizing

  // Polling fallback if VADWorklet fails
  backendChunkTimer = setInterval(() => {
    if (!backendSTTActive) return;
    const vol = getAvgVolume();
    if (vol > 0.02) {
      silenceFrames = 0;
      speakingFrames++;
    } else if (backendAudioChunks.length > 0) {
      silenceFrames++;
      // Only finalize after confirmed speech + confirmed silence
      if (silenceFrames >= 20 && speakingFrames >= MIN_SPEAKING_FRAMES) {
        console.log(`[BackendSTT] Silence detected after ${speakingFrames} speaking frames. Finalizing.`);
        silenceFrames = 0; speakingFrames = 0;
        submitVisibleTranscript();
      }
    }
  }, 100);

  backendMediaRecorder.start(250); // 250ms timeslice for good chunk frequency

  // ── Parallel Web Speech for live interim display (universal en-IN mode) ─────
  // Chrome only has reliable interim-result support for a handful of languages.
  // kn-IN / bn-IN / ta-IN / te-IN / ml-IN / gu-IN / pa-IN return nothing or crash.
  //
  // Solution: always run the DISPLAY recognition in en-IN (or hi-IN for Hindi).
  // en-IN captures the romanized form of ANY language as the user speaks:
  //   Kannada  → "hegiddira matte"   Bengali → "kemon acho tumi"
  //   Tamil    → "enna panra nee"    Telugu  → "ela unnav meeru"
  //   Marathi  → "aahe ka tula"      Punjabi → "ki haal hai"
  // The accurate native-script transcript arrives from Sarvam at end of utterance
  // and replaces whatever was shown in the green box.
  //
  // Chrome natively supports: en-IN, hi-IN, es-ES, fr-FR, de-DE, ja-JP, zh-CN, ko-KR, ar-SA, ru-RU, pt-BR, it-IT
  const _CHROME_NATIVE = new Set([
    'en-IN','en-US','en-GB','hi-IN','es-ES','fr-FR','de-DE','it-IT',
    'pt-BR','ja-JP','zh-CN','ko-KR','ar-SA','ru-RU','nl-NL','pl-PL','tr-TR',
  ]);
  const _SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (_SR) {
    _displayRecognition = new _SR();
    _displayRecognition.continuous     = true;
    _displayRecognition.interimResults = true;

    // Use native lang if Chrome supports it; otherwise en-IN for universal romanized capture
    let _dispLang = _CHROME_NATIVE.has(langCode) ? langCode : 'en-IN';
    _displayRecognition.lang = _dispLang;

    _displayRecognition.onresult = (ev) => {
      if (!backendSTTActive) return;
      let interimNow = '';
      let finalNow = '';
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        if (!ev.results[i].isFinal) interimNow += ev.results[i][0].transcript;
        else finalNow += ev.results[i][0].transcript;
      }
      
      // Dual-stream: update merger with browser's fast interim
      transcriptMerger.updateWebSpeech(finalNow, interimNow);
      const state = transcriptMerger.getDisplayState();
      
      // Update latency tracker for Web Speech
      const lat_web = document.getElementById('dbgWeb');
      if (lat_web && lat_web.textContent === '—' && interimNow) lat_web.textContent = `${Date.now() - sttStartTime}ms`;
      
      // Update accumulated text so we can finalize if manually stopped
      finalAccum = state.final || state.interim;
      
      renderLiveWords(state.final, state.interim);
    };

    _displayRecognition.onerror = (err) => {
      // If the native code is unsupported at runtime, fall back to en-IN immediately
      if (err.error === 'language-not-supported' || err.error === 'service-not-allowed') {
        _dispLang = 'en-IN';
        console.log(`[Display STT] ${langCode} not supported by browser → fallback to en-IN`);
      }
    };

    _displayRecognition.onend = () => {
      // ★ FIX: Capture local reference to prevent stale closure from restarting a
      // NEWER _displayRecognition instance created in the next turn.
      if (backendSTTActive && _displayRecognition === capturedDisplayRec) {
        capturedDisplayRec.lang = _dispLang;
        try { capturedDisplayRec.start(); } catch(_) {}
      }
    };

    try { _displayRecognition.start(); } catch(_) {}
    const capturedDisplayRec = _displayRecognition; // capture after start
  }

  sttStartTime = Date.now();
  showToast(`🎤 Sarvam ASR active (${langCode})`, 'info', 2000);
}

async function finalizeBackendTranscript(fromRecorder = false) {
  if (backendFinalizing && !fromRecorder) return;
  backendFinalizing = true;

  const chunks = backendAudioChunks.slice();
  const fallbackText = (finalAccum || interimAccum || "").trim();

  if (!chunks.length) {
    backendFinalizing = false;
    if (fallbackText) finalizeSpeech(fallbackText);
    else stopListening();
    return;
  }

  const blobType = chunks.find(Boolean)?.type || "audio/webm";
  const audioBlob = new Blob(chunks, { type: blobType });
  let timeoutId = null;

  try {
    setAppState("thinking");
    setMsg("Transcribing...");

    const controller = new AbortController();
    timeoutId = setTimeout(() => controller.abort(), FINAL_STT_TIMEOUT_MS);
    const resp = await fetch(`${API_BASE}/stt/stream?language=${encodeURIComponent(backendLangCode)}`, {
      method: "POST",
      headers: {
        "Content-Type": audioBlob.type || "audio/webm",
        "Bypass-Tunnel-Reminder": "true",
      },
      body: audioBlob,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    const data = await resp.json().catch(() => ({}));
    const transcript = (data.transcript || "").trim();

    if (transcript) {
      renderLiveWords(transcript, "");
      finalAccum = transcript;
      interimAccum = "";
      finalizeSpeech(transcript);
      return;
    }

    if (fallbackText) {
      finalizeSpeech(fallbackText);
      return;
    }

    stopListening();
    setAppState("ready");
    setMsg(data.error ? `Transcription failed: ${data.error}` : "No speech detected.", "error");
  } catch (err) {
    console.warn("[BackendSTT] Final transcription failed:", err);
    if (fallbackText) {
      setMsg("Using live transcript...");
      finalizeSpeech(fallbackText);
    } else {
      stopListening();
      setAppState("ready");
      setMsg("Transcription failed. Please try again.", "error");
    }
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
    backendFinalizing = false;
    backendAudioChunks = [];
  }
}

/**
 * Stops the MediaRecorder, flushes the final audio chunk, and cleans up.
 * Called from stopListening() for both manual stop and after silence timeout.
 * @param {boolean} forceFinalize - if true, unconditionally stop the listening state.
 */
function stopBackendSTT(forceFinalize = false, transcribeFinal = false) {
  if (!backendSTTActive) return;
  backendSTTActive = false;
  if (transcribeFinal) backendFinalizing = true;

  // Stop the parallel display recognition
  if (_displayRecognition) {
    try { _displayRecognition.stop(); } catch(_) {}
    _displayRecognition = null;
  }

  if (backendChunkTimer) { clearInterval(backendChunkTimer); backendChunkTimer = null; }

  if (backendMediaRecorder && backendMediaRecorder.state !== 'inactive') {
    const recorder = backendMediaRecorder;
    recorder.onstop = () => {
      if (transcribeFinal) finalizeBackendTranscript(true);
    };
    backendMediaRecorder.requestData();
    backendMediaRecorder.stop();
    // Final transcript is posted to /stt/stream; WebSocket remains live preview/fallback.
  } else if (transcribeFinal) {
    finalizeBackendTranscript(true);
  }
  backendMediaRecorder = null;
  
  if (forceFinalize) {
    stopListening();
  }
}

/**
 * Mic button: start listening, or stop and finalize any accumulated speech.
 *
 * Manual-stop finalization is handled HERE (not inside stopListening) to avoid
 * the re-entrancy loop: finalizeSpeech→stopListening→finalizeSpeech.
 * The silence timer is the only other path that calls finalizeSpeech.
 */
micBtn.addEventListener("click", () => {
  if (isListening) {
    // Manual stop — finalize whatever we have (final OR interim)
    const textToSend = finalAccum.trim() || interimAccum.trim();
    if (backendSTTActive) {
      // ★ BUG FIX: MUST stop the MediaRecorder BEFORE sending forceStop to WS.
      // Without this, the recorder kept streaming audio to a closing WebSocket,
      // causing the WS to stay open and the UI to freeze in 'Thinking...' forever.
      submitVisibleTranscript();
    } else if (textToSend) {
      finalizeSpeech(textToSend);
    } else {
      stopListening();
    }
  } else {
    // ★ Tapping mic while AI speaks → interrupt + listen (handled inside startListening)
    startListening();
  }
});

/* ═══════════════════════════════════════════════════════════
   APP STATE & UI HELPERS
   ═══════════════════════════════════════════════════════════ */
function setAppState(state) {
  micBtn.classList.toggle("recording",      state === "listening");
  micBtn.classList.toggle("speaking-state", state === "speaking");
  micHint.classList.toggle("rec",   state === "listening");
  micHint.classList.toggle("speak", state === "speaking");
  micHint.textContent = {
    listening: "Tap to stop",
    thinking:  "Processing…",
    speaking:  "Tap to interrupt",
    ready:     "Tap to speak"
  }[state] || "Tap to speak";

  // Drive body class → CSS strip + other state-specific styles
  document.body.className = document.body.className.replace(/\bstate-\S+/g, "").trim();
  if (state !== "ready") document.body.classList.add(`state-${state}`);

  const map = {
    ready:     ["● Ready",     "state-ready"],
    listening: ["● Listening", "state-listening"],
    thinking:  ["● Thinking",  "state-thinking"],
    speaking:  ["● Speaking",  "state-speaking"],
  };
  const [txt, cls] = map[state] || map.ready;
  stateBadge.textContent = txt; stateBadge.className = `state-badge ${cls}`;

  if (state === "speaking")  { stopWave(); drawSpeaking(); }
  else if ((state === "ready" || state === "thinking") && !analyserNode) { stopWave(); drawIdle(); }
}

function setMsg(html, type = "normal") { systemMessage.innerHTML = html; systemMessage.className = "system-msg" + (type === "error" ? " error" : ""); }
function setLangBadge(lang) { 
  if (!lang) return; 
  langBadge.textContent = `🌐 ${lang}`; 
  statLang.textContent = lang; 
  if (SESS_LANG !== lang) {
    SESS_LANG = lang;
    // FIX: Only restart STT for a language switch when we are ACTIVELY listening
    // and NOT mid-turn (isProcessingMessage). Restarting mid-turn corrupts state.
    if (isListening && !isProcessingMessage && STT_LANG_MAP[lang]) {
      const newProvider = getSTTProvider(lang);
      const newCode     = STT_LANG_MAP[lang];
      // Abort (not stop) existing paths for clean synchronous teardown
      try { recognition?.abort(); } catch (_) {}
      stopBackendSTT();

      if (newProvider === 'backend') {
        if (micStreamRef) startBackendSTT(micStreamRef, newCode);
      } else {
        recognition = buildRecognition();
        setTimeout(() => {
          if (!isListening || manualStop || isSpeaking) return;
          try { recognition.start(); } catch (_) {}
        }, 120);
      }
      console.log(`[STT] Language switched to ${lang} → provider=${newProvider} code=${newCode}`);
    }
  }
}

function colorMi(el, ms) {
  el.classList.remove("good","warn","slow");
  if (ms < 1000) el.classList.add("good"); else if (ms < 2000) el.classList.add("warn"); else el.classList.add("slow");
}
function setMi(el, val) {
  if (!el) return;
  if (!val && val !== 0) { el.textContent = "—"; el.classList.remove("good","warn","slow"); return; }
  el.textContent = String(val); const ms = parseFloat(String(val)); if (!isNaN(ms)) colorMi(el, ms);
}
function updateMetrics({ stt, ttft, tts, total, model }) {
  if (stt !== undefined) setMi(sttLatEl, stt); if (ttft !== undefined) setMi(llmLatEl, ttft);
  if (tts !== undefined) setMi(ttsLatEl, tts); if (total !== undefined) { setMi(totLatEl, total); const ms = parseFloat(String(total)); if (!isNaN(ms)) colorMi(totLatEl, ms); }
  if (model !== undefined && modelNameEl) { modelNameEl.textContent = model || "—"; statModel.textContent = (model || "—").split("/").pop(); }
}
function showTtftBadge(ms) {
  ttftBadge.textContent = `⚡ ${Math.round(ms)} ms`; ttftBadge.classList.remove("hidden","good","warn","slow");
  ttftBadge.classList.add(ms < 1000 ? "good" : ms < 2000 ? "warn" : "slow"); setTimeout(() => ttftBadge.classList.add("hidden"), 5500);
}
function updateProviderChip(provider, model) {
  if (!provider) return;
  providerLabel.textContent = provider; 
  if (model) statModel.textContent = model;
}

let lastActiveProvider = null;
function notifyProviderSwitch(newProvider) {
  if (!lastActiveProvider) { lastActiveProvider = newProvider; return; }
  if (lastActiveProvider === newProvider) return;
  // Only notify when falling back to Ollama (all Gemini keys exhausted)
  if (newProvider === "Ollama") {
    showToast("⚠️ Gemini unavailable — using local Ollama AI", "error", 5000);
  } else if (newProvider === "Gemini" && lastActiveProvider === "Ollama") {
    showToast("✅ Gemini restored", "info", 3000);
  }
  lastActiveProvider = newProvider;
}

function showToast(message, type = "info", duration = 3000) {
  if (!toastContainer) return;
  const t = document.createElement("div");
  t.className = `toast toast-${type}`;
  t.innerHTML = `<span>${message}</span>`;
  toastContainer.appendChild(t);
  setTimeout(() => {
    t.classList.add("hide");
    t.addEventListener("animationend", () => t.remove());
  }, duration);
}

async function pollHealth() {
  try {
    const r = await fetch(`${API_BASE}/health/keys`, { signal: AbortSignal.timeout(4000) });
    if (!r.ok) return;
    const d = await r.json();
    const setDot = (dot, keyEl, info) => {
      if (!dot) return; // null-safe: openaiDot is null
      const ok = (info?.active_keys ?? 0) > 0;
      dot.className = `api-dot ${ok ? "ok" : "err"}`;
      if (keyEl) keyEl.textContent = `${info?.active_keys ?? 0}/${info?.total_keys ?? 0}`;
    };
    // OpenAI removed — only poll gemini, sarvam, ollama
    setDot(geminiDot, geminiKeys, d.gemini);
    setDot(sarvamDot, sarvamKeys, d.sarvam);
    setDot(ollamaDot, ollamaKeys, d.ollama);
  } catch (_) {}
}
pollHealth(); setInterval(pollHealth, 15000);

sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("open"));
document.addEventListener("click", e => { if (window.innerWidth <= 680 && !sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) sidebar.classList.remove("open"); });

function hideWelcome() {
  const el = document.getElementById("welcomeState"); if (!el) return;
  el.style.cssText = "opacity:0;transform:scale(.95);transition:opacity .22s,transform .22s;pointer-events:none"; setTimeout(() => el?.remove(), 230);
}

/* ═══════════════════════════════════════════════════════════
   CHAT MESSAGES
   ═══════════════════════════════════════════════════════════ */
function addMessage(role, text, meta = {}) {
  hideWelcome(); msgCount++; statMessages.textContent = String(msgCount);
  const wrap = document.createElement("div"); wrap.className = `message message-${role}`; wrap.id = `msg-${msgCount}`;
  const av = document.createElement("div"); av.className = "message-avatar"; av.textContent = role === "user" ? "\uD83E\uDDD1" : "\u25C8"; wrap.appendChild(av);
  const bubble = document.createElement("div"); bubble.className = "message-bubble";
  const textEl = document.createElement("p"); textEl.className = "message-text"; textEl.textContent = text || ""; bubble.appendChild(textEl);
  
  const mm = document.createElement("div"); mm.className = "msg-meta";
  if (meta.language) { const b = document.createElement("span"); b.className = "badge b-lang"; b.textContent = meta.language; mm.appendChild(b); }
  if (meta.provider) { const b = document.createElement("span"); b.className = "badge b-provider"; b.textContent = meta.provider; mm.appendChild(b); }
  if (meta.ttft != null) {
    const ms = parseFloat(meta.ttft); const b = document.createElement("span");
    b.className = `badge b-lat ${ms < 1000 ? "good" : ms < 2000 ? "warn" : "slow"}`;
    b.textContent = `\u26A1 ${Math.round(ms)} ms`; b.id = `ttft-b-${msgCount}`; mm.appendChild(b);
  }
  if (role === "ai") {
    const spk = document.createElement("button"); spk.className = "speaker-btn"; spk.title = "Play TTS"; spk.textContent = "\uD83D\uDD0A";
    spk.addEventListener("click", () => onSpeakerClick(spk, textEl, meta.language)); mm.appendChild(spk);
  }
  bubble.appendChild(mm);

  // Timestamp — shown on hover via CSS
  const now = new Date();
  const ts = document.createElement("span"); ts.className = "msg-time";
  ts.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  bubble.appendChild(ts);

  wrap.appendChild(bubble); chatArea.appendChild(wrap); chatArea.scrollTop = chatArea.scrollHeight;
  return { wrap, textEl, msgId: msgCount };
}

function addTyping() {
  hideWelcome(); const el = document.createElement("div"); el.className = "message message-ai"; el.id = "typing-ind";
  el.innerHTML = `<div class="message-avatar">◈</div><div class="message-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
  chatArea.appendChild(el); chatArea.scrollTop = chatArea.scrollHeight;
}
const removeTyping = () => document.getElementById("typing-ind")?.remove();

async function onSpeakerClick(btn, textEl, language) {
  if (btn.dataset.loading === "true") return;
  btn.dataset.loading = "true"; btn.disabled = true; const prev = btn.textContent; btn.textContent = "⏳";
  const bubble = btn.closest(".message-bubble");
  try {
    const r = await fetch(`${API_BASE}/tts/generate`, {
      method: "POST", headers: { 
        "Content-Type": "application/json",
        "Bypass-Tunnel-Reminder": "true" 
      },
      body: JSON.stringify({ text: textEl.textContent.trim(), language: language || SESS_LANG }),
    });
    const ct = r.headers.get("content-type") || "";
    if (ct.includes("application/json")) { const j = await r.json(); if (!j.success) { throw new Error(j.error || "unavailable"); } }
    const blob = await r.blob(); if (!blob?.size) throw new Error("Empty audio");
    // iOS Safari fix: use a pre-existing audio context or create object url
    const url = URL.createObjectURL(blob); 
    const audio = new Audio(url);
    btn.textContent = "⏸️"; bubble?.classList.add("audio-playing");

    isSpeaking = true;
    let wasListening = isListening;
    if (isListening) stopListening();

    audio.onended = () => { 
      btn.textContent = "🔊"; btn.disabled = false; btn.dataset.loading = "false"; 
      bubble?.classList.remove("audio-playing"); URL.revokeObjectURL(url); 
      isSpeaking = false;
      if (wasListening && !isListening) startListening();
    };
    audio.onerror = () => { 
      btn.textContent = prev; btn.disabled = false; btn.dataset.loading = "false"; 
      bubble?.classList.remove("audio-playing"); 
      isSpeaking = false;
      if (wasListening && !isListening) startListening();
    };
    await audio.play(); 
    btn.onclick = () => {
      if (audio.paused) {
        if (isListening) { wasListening = true; stopListening(); }
        isSpeaking = true;
        audio.play();
      } else {
        audio.pause();
        isSpeaking = false;
        if (wasListening && !isListening) startListening();
      }
    };
  } catch (e) {
    btn.textContent = prev; btn.disabled = false; btn.dataset.loading = "false";
    bubble?.classList.remove("audio-playing"); setMsg(`TTS: ${e.message}`, "error");
  }
}

class AudioQueue {
  constructor() { this.ctx=null; this.q=[]; this.playing=false; this.next=0; this.nodes=[]; this.onstart=null; this.onend=null; this._sealed=false; }
  /** Call after all audio chunks have been enqueued (on SSE 'done' event). */
  seal() {
    this._sealed = true;
    // If queue already drained before seal arrived, fire onend now
    if (!this.playing && !this.q.length && this.onend) this.onend();
  }
  _ctx() {
    if (window.aCtx) {
      if (window.aCtx.state === "suspended") window.aCtx.resume();
      return window.aCtx;
    }
    if (!this.ctx || this.ctx.state === "closed") this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (this.ctx.state === "suspended") this.ctx.resume();
    return this.ctx;
  }
  async addChunk(b64) {
    const c=this._ctx(); const bin=atob(b64); const bytes=new Uint8Array(bin.length);
    for(let i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i);
    try { const buf=await c.decodeAudioData(bytes.buffer); this.q.push(buf); if(!this.playing) this._play(); } catch(e){console.warn("decode:",e);}
  }
  _play() {
    if(!this.q.length){this.playing=false;return;} this.playing=true;
    const c=this._ctx(); const buf=this.q.shift(); const src=c.createBufferSource(); const g=c.createGain();
    src.buffer=buf; src.connect(g); g.connect(c.destination);
    if(this.onstart&&this.next===0) this.onstart();
    const now=c.currentTime; if(this.next<now) this.next=now+.04;
    g.gain.setValueAtTime(0,this.next); g.gain.linearRampToValueAtTime(1,this.next+.003);
    const e=this.next+buf.duration; g.gain.setValueAtTime(1,e-.003); g.gain.linearRampToValueAtTime(0,e);
    try {
      src.start(this.next); this.nodes.push(src); this.next+=buf.duration-.004;
      src.onended=()=>{ this.nodes=this.nodes.filter(n=>n!==src); if(!this.q.length&&this.nodes.length===0){this.next=0;this.playing=false;if(this._sealed&&this.onend)this.onend();} this._play(); };
    } catch (err) {
      console.warn("AudioQueue _play skip chunk:", err);
      if(!this.q.length&&this.nodes.length===0){this.next=0;this.playing=false;if(this._sealed&&this.onend)this.onend();} else { this._play(); }
    }
  }
  // FIX: Null out callbacks on stop() so that stopped nodes' asynchronous onended
  // events cannot accidentally trigger a stale onend from a previous turn.
  stop(){this.q=[];this.next=0;this._sealed=false;this.onstart=null;this.onend=null;this.nodes.forEach(n=>{try{n.stop();}catch(_){}});this.nodes=[];this.playing=false;}
}
const audioQueue = new AudioQueue();

async function processMessage(text, sttMs = 0, isVoice = false, detectedScript = null) {
  const clean = text.trim(); if (!clean) return;
  // Abort any existing turn completely before starting a new one
  if (isProcessingMessage && currentAbortController) {
      currentAbortController.abort();
  }
  isProcessingMessage = true;
  currentAbortController = new AbortController();
  
  audioQueue._sealed = false; // Reset seal for this new turn
  _armProcessingLockTimeout(); // Safety: auto-reset after 30s if onend never fires

  addMessage("user", clean, {});
  addTyping(); setAppState("thinking"); setMsg("Thinking…");

  const reqStart  = performance.now();
  let firstTok = null, ttsStartT = null, fullText = "";
  let currentEl = null, currentMsgId = null, ttftMs = null;
  let provName = "Gemini", detectedLang = SESS_LANG;

  try {
    const resp = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST", headers: { 
        "Content-Type": "application/json",
        "Bypass-Tunnel-Reminder": "true" 
      },
      signal: currentAbortController.signal,
      body: JSON.stringify({
        text:            clean,
        session_id:      SESSION_ID,
        stt_latency_ms:  sttMs,
        detected_script: detectedScript || null,
      }),
    });
    if (!resp.ok) throw new Error(`Server ${resp.status}`);
    if (isVoice) {
      audioQueue.onstart = () => {
        isSpeaking = true;
        // ★ FIX: Immediately hard-stop recognition when TTS audio begins.
        // This prevents recognition.onend from firing and calling safeRestart()
        // which could re-open the mic while the AI is still speaking.
        if (recognition) { try { recognition.abort(); } catch(_) {} }
        if (isListening) stopListening();
        setAppState('speaking'); setMsg('Speaking…');
        stopWave(); drawSpeaking();
        // Highlight the AI bubble that's currently speaking
        document.querySelectorAll('.message-ai').forEach(el => el.classList.remove('is-speaking'));
        const lastAi = chatArea.querySelector('.message-ai:last-child');
        if (lastAi) lastAi.classList.add('is-speaking');
      };
      // ★ Use unified onTurnComplete — handles both audio and no-audio (TTS fallback) paths
      audioQueue.onend = onTurnComplete;
    }
    const reader = resp.body.getReader(); const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      for (const line of decoder.decode(value).split("\n")) {
        if (!line.startsWith("data: ")) continue;
        let ev; try { ev = JSON.parse(line.slice(6)); } catch { continue; }

        if (ev.type === "meta") {
          const ml = ev.language || "English";
          setLangBadge(ml);
          detectedLang = ml;
          // Sync Web Speech STT language to backend-detected language
          updateSTTLanguage(ml);
          console.log(`[STT] Language synced after AI response → ${ml}`);
        }
        else if (ev.type === "model") {
          const m = ev.content.toLowerCase();
          // OpenAI removed — only Gemini and Ollama are possible providers
          if (m.includes("ollama") || m.includes("llama") || m.includes("local")) {
            provName = "Ollama";
          } else {
            provName = "Gemini"; // default: any gemini-* model name
          }
          updateProviderChip(provName, ev.content);
          notifyProviderSwitch(provName);
        }
        else if (ev.type === "ttft") {
          if (!firstTok) {
            firstTok = performance.now(); ttftMs = Math.round(firstTok - reqStart); showTtftBadge(ttftMs);
            updateMetrics({ ttft: `${ttftMs} ms`, stt: sttMs ? `${Math.round(sttMs)} ms` : "—" });
            totalTtft += ttftMs; ttftCount++; statAvgTtft.textContent = `${Math.round(totalTtft/ttftCount)} ms`;
          }
        }
        else if (ev.type === "text") {
          removeTyping();
          if (!firstTok) {
            firstTok = performance.now(); ttftMs = Math.round(firstTok - reqStart); showTtftBadge(ttftMs);
            updateMetrics({ ttft:`${ttftMs} ms`, stt: sttMs ? `${Math.round(sttMs)} ms` : "—" });
            totalTtft += ttftMs; ttftCount++; statAvgTtft.textContent = `${Math.round(totalTtft/ttftCount)} ms`;
          }
          if (!currentEl) {
            const { textEl, msgId } = addMessage("ai", "", { language: detectedLang, provider: provName, ttft: ttftMs });
            currentEl = textEl; currentMsgId = msgId; currentEl.classList.add("streaming");
          }
          fullText += ev.content; currentEl.textContent = fullText; chatArea.scrollTop = chatArea.scrollHeight;
        }
        else if (ev.type === "audio" && isVoice) { if (!ttsStartT) ttsStartT = performance.now(); audioQueue.addChunk(ev.content); }
        else if (ev.type === "done") {
          if (currentEl) currentEl.classList.remove("streaming");
          const model = ev.model || "Gemini";
          const resolvedProvider = ev.provider || (/gpt|openai/i.test(model) ? "GPT-4o" : "Gemini");
          provName = resolvedProvider;
          updateProviderChip(resolvedProvider, model);
          notifyProviderSwitch(resolvedProvider);
          const totalMs  = Math.round(performance.now() - reqStart);
          const ttsMs    = ttsStartT ? Math.round(ttsStartT - reqStart) : null;
          const responseMs = ttftMs ?? totalMs;
          updateMetrics({ stt: sttMs ? `${Math.round(sttMs)} ms` : "—", ttft: ttftMs ? `${ttftMs} ms` : "—", tts: ttsMs ? `${ttsMs} ms` : "—", total: `${responseMs} ms`, model });
          const lb = document.getElementById(`ttft-b-${currentMsgId}`);
          if (lb && ttftMs) { lb.textContent = `⚡ ${ttftMs} ms`; lb.className = `badge b-lat ${ttftMs<1000?"good":ttftMs<2000?"warn":"slow"}`; }
          if (isVoice) {
            audioQueue.seal(); // triggers onend → onTurnComplete if no audio chunks
          } else {
            // Text-only turn: just reset state, no auto-listen restart
            setAppState("ready"); setMsg("Response ready ✓");
          }
        }
        else if (ev.type === "error") {
          _resetProcessingLock(); // FIX: was isProcessingMessage=false, now also cancels safety timer
          removeTyping(); addMessage("ai", "Something went wrong. Please try again.", {});
          setAppState("ready"); setMsg(`Error: ${ev.content}`, "error");
          if (isVoice && !manualStop) {
            setTimeout(() => {
              if (!manualStop && !isListening && !isSpeaking) {
                console.log("[Auto-Resume] Resuming mic after error.");
                startListening();
              }
            }, 2500);
          } else { stopMicWave(); }
        }
      }
    }
    if (!isVoice) _resetProcessingLock();
  } catch (err) {
    if (err.name === 'AbortError') {
      console.log('Turn interrupted by user.');
      removeTyping();
      return;
    }
    removeTyping(); console.error("Stream error:", err);
    _resetProcessingLock(); // FIX: always reset lock on any caught error
    const { wrap } = addMessage("ai", "Network error — is the server running?", {});
    const btn = document.createElement("button"); btn.style.cssText = "margin-top:8px;padding:5px 12px;border-radius:8px;background:rgba(187,162,232,.14);border:1px solid rgba(187,162,232,.28);color:var(--c-purple);font-size:12px;cursor:pointer;font-family:var(--font)";
    btn.textContent = "🔄 Retry"; btn.onclick = () => { wrap.remove(); processMessage(text, sttMs, isVoice); };
    wrap.querySelector(".message-bubble").appendChild(btn);
    setAppState("ready"); setMsg("Network error.", "error"); stopMicWave();
  }
}

async function sendText() { const v = textInput.value.trim(); if (!v) return; textInput.value = ""; await processMessage(v, 0, false); }
sendBtn.addEventListener("click", sendText);
textInput.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendText(); } });

clearBtn.addEventListener("click", async () => {
  chatArea.innerHTML = `<div class="welcome-state" id="welcomeState"><div class="welcome-orb"><div class="orb-ring r1"></div><div class="orb-ring r2"></div><div class="orb-ring r3"></div><span class="orb-icon">◈</span></div><h2 class="welcome-title">Start a conversation</h2><p class="welcome-sub">Speak or type in any language. AI responds naturally.</p></div>`;
  msgCount = 0; statMessages.textContent = "0"; totalTtft = 0; ttftCount = 0; statAvgTtft.textContent = "—";
  updateMetrics({ stt:null,ttft:null,tts:null,total:null,model:null });
  lastActiveProvider = null;
  try { await fetch(`${API_BASE}/chat/clear?session_id=${SESSION_ID}`, { method: "POST" }); } catch (_) {}
  stopListening();
  // Release the persistent mic stream fully on a deliberate chat clear
  if (micStreamRef) { micStreamRef.getTracks().forEach(t => t.stop()); micStreamRef = null; }
  setAppState("ready"); setMsg("Conversation cleared.");
});

// Release mic when page is closed so the OS doesn't show the mic indicator indefinitely
window.addEventListener('beforeunload', () => {
  if (micStreamRef) { micStreamRef.getTracks().forEach(t => t.stop()); micStreamRef = null; }
});

drawIdle();
if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
  micBtn.disabled = true; micBtn.title = "Use Chrome or Edge for speech recognition";
  setMsg("\u26A0 Microphone requires Chrome or Edge. Text input works in all browsers.", "error");
}

// ── Mic amplitude ring — updates CSS var(--mic-vol) on the mic button ────────────────
// This drives the ::before pseudo-element amplitude ring in styles.css.
// Runs at 60fps only while the user is listening to keep CPU usage near zero.
(function micAmplitudeLoop() {
  const updateRing = () => {
    if (isListening && analyserNode) {
      const vol = getAvgVolume(); // 0–1 normalized
      // Map to visible pixel range: 0 = no ring, 1 = 14px expansion
      const px  = Math.round(vol * 14);
      micBtn.style.setProperty('--mic-vol',     `${px}px`);
      micBtn.style.setProperty('--mic-vol-raw', String(vol.toFixed(2)));
    } else {
      micBtn.style.setProperty('--mic-vol',     '0px');
      micBtn.style.setProperty('--mic-vol-raw', '0');
    }
    requestAnimationFrame(updateRing);
  };
  requestAnimationFrame(updateRing);
})();

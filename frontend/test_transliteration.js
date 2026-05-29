// ─── Transliteration Accuracy Test ───────────────────────────────────────────
// Run: node test_transliteration.js
// Tests all 9 script blocks in indicMap against known word→romanization pairs.

const indicMap = {
  // ── DEVANAGARI ──
  'अ':'a','आ':'aa','इ':'i','ई':'ii','उ':'u','ऊ':'uu','ऋ':'ri','ए':'e','ऐ':'ai','ओ':'o','औ':'au',
  'क':'k','ख':'kh','ग':'g','घ':'gh','ङ':'ng','च':'ch','छ':'chh','ज':'j','झ':'jh','ञ':'ny',
  'ट':'t','ठ':'th','ड':'d','ढ':'dh','ण':'n','त':'t','थ':'th','द':'d','ध':'dh','न':'n',
  'प':'p','फ':'ph','ब':'b','भ':'bh','म':'m','य':'y','र':'r','ल':'l','व':'v','श':'sh','ष':'sh','स':'s','ह':'h','ळ':'l',
  'ा':'aa','ि':'i','ी':'ii','ु':'u','ू':'uu','ृ':'ri','े':'e','ै':'ai','ो':'o','ौ':'au','ं':'n','ः':'h','्':'','।':'.','॥':'.',
  // ── KANNADA ──
  'ಅ':'a','ಆ':'aa','ಇ':'i','ಈ':'ii','ಉ':'u','ಊ':'uu','ಋ':'ri','ಎ':'e','ಏ':'e','ಐ':'ai','ಒ':'o','ಓ':'o','ಔ':'au',
  'ಕ':'k','ಖ':'kh','ಗ':'g','ಘ':'gh','ಙ':'ng','ಚ':'ch','ಛ':'chh','ಜ':'j','ಝ':'jh','ಞ':'nj',
  'ಟ':'t','ಠ':'th','ಡ':'d','ಢ':'dh','ಣ':'n','ತ':'t','ಥ':'th','ದ':'d','ಧ':'dh','ನ':'n',
  'ಪ':'p','ಫ':'ph','ಬ':'b','ಭ':'bh','ಮ':'m','ಯ':'y','ರ':'r','ಱ':'r','ಲ':'l','ವ':'v','ಶ':'sh','ಷ':'sh','ಸ':'s','ಹ':'h','ಳ':'l','ೞ':'l',
  'ಾ':'aa','ಿ':'i','ೀ':'ii','ು':'u','ೂ':'uu','ೃ':'ri','ೆ':'e','ೇ':'e','ೈ':'ai','ೊ':'o','ೋ':'o','ೌ':'au','ಂ':'n','ಃ':'h','್':'',
  // ── BENGALI ──
  'অ':'o','আ':'a','ই':'i','ঈ':'ii','উ':'u','ঊ':'uu','ঋ':'ri','এ':'e','ঐ':'oi','ও':'o','ঔ':'ou',
  'ক':'k','খ':'kh','গ':'g','ঘ':'gh','ঙ':'ng','চ':'ch','ছ':'chh','জ':'j','ঝ':'jh','ঞ':'n',
  'ট':'t','ঠ':'th','ড':'d','ঢ':'dh','ণ':'n','ত':'t','থ':'th','দ':'d','ধ':'dh','ন':'n',
  'প':'p','ফ':'ph','ব':'b','ভ':'bh','ম':'m','য':'j','র':'r','ল':'l','শ':'sh','ষ':'sh','স':'s','হ':'h','ড়':'r','ঢ়':'rh','য়':'y','ৎ':'t',
  'া':'a','ি':'i','ী':'ii','ু':'u','ূ':'uu','ৃ':'ri','ে':'e','ৈ':'oi','ো':'o','ৌ':'ou','ং':'ng','ঃ':'h','ঁ':'n','্':'',
  // ── TAMIL ──
  'அ':'a','ஆ':'aa','இ':'i','ஈ':'ii','உ':'u','ஊ':'uu','எ':'e','ஏ':'ee','ஐ':'ai','ஒ':'o','ஓ':'oo','ஔ':'au',
  'க':'k','ங':'ng','ச':'ch','ஞ':'ny','ட':'t','ண':'n','த':'th','ந':'n','ன':'n',
  'ப':'p','ம':'m','ய':'y','ர':'r','ற':'rr','ல':'l','ள':'ll','ழ':'zh','வ':'v','ஶ':'sh','ஷ':'sh','ஸ':'s','ஹ':'h',
  'ா':'aa','ி':'i','ீ':'ii','ு':'u','ூ':'uu','ெ':'e','ே':'ee','ை':'ai','ொ':'o','ோ':'oo','ௌ':'au','்':'','ஂ':'n',
  // ── TELUGU ──
  'అ':'a','ఆ':'aa','ఇ':'i','ఈ':'ii','ఉ':'u','ఊ':'uu','ఎ':'e','ఏ':'ee','ఐ':'ai','ఒ':'o','ఓ':'oo','ఔ':'au',
  'క':'k','ఖ':'kh','గ':'g','ఘ':'gh','చ':'ch','జ':'j','ట':'t','డ':'d','త':'th','ద':'d','న':'n',
  'ప':'p','బ':'b','మ':'m','య':'y','ర':'r','ళ':'l','వ':'v','శ':'sh','స':'s','హ':'h','ఱ':'r','ల':'l',
  'థ':'th','ధ':'dh',
  'ా':'aa','ి':'i','ీ':'ii','ు':'u','ూ':'uu','ె':'e','ే':'ee','ై':'ai','ొ':'o','ో':'oo','ౌ':'au','ం':'m','్':'',
  // ── GUJARATI ──
  'અ':'a','આ':'aa','ઇ':'i','ઈ':'ii','ઉ':'u','ઊ':'uu','એ':'e','ઐ':'ai','ઓ':'o','ઔ':'au',
  'ક':'k','ખ':'kh','ગ':'g','ઘ':'gh','ઙ':'ng','ચ':'ch','છ':'chh','જ':'j','ઝ':'jh','ઞ':'ny',
  'ટ':'t','ઠ':'th','ડ':'d','ઢ':'dh','ણ':'n','ત':'t','થ':'th','દ':'d','ધ':'dh','ન':'n',
  'પ':'p','ફ':'ph','બ':'b','ભ':'bh','મ':'m','ય':'y','ર':'r','લ':'l','ળ':'l','વ':'v','શ':'sh','ષ':'sh','સ':'s','હ':'h',
  'ા':'aa','િ':'i','ી':'ii','ુ':'u','ૂ':'uu','ે':'e','ૈ':'ai','ો':'o','ૌ':'au','ં':'n','ઃ':'h','્':'',
  // ── PUNJABI (GURMUKHI) ──
  'ਅ':'a','ਆ':'aa','ਇ':'i','ਈ':'ii','ਉ':'u','ਊ':'uu','ਏ':'e','ਐ':'ai','ਓ':'o','ਔ':'au',
  'ਕ':'k','ਖ':'kh','ਗ':'g','ਘ':'gh','ਙ':'ng','ਚ':'ch','ਛ':'chh','ਜ':'j','ਝ':'jh','ਞ':'ny',
  'ਟ':'t','ਠ':'th','ਡ':'d','ਢ':'dh','ਣ':'n','ਤ':'t','ਥ':'th','ਦ':'d','ਧ':'dh','ਨ':'n',
  'ਪ':'p','ਫ':'ph','ਬ':'b','ਭ':'bh','ਮ':'m','ਯ':'y','ਰ':'r','ਲ':'l','ਵ':'v','ਸ਼':'sh','ਸ':'s','ਹ':'h',
  'ਾ':'aa','ਿ':'i','ੀ':'ii','ੁ':'u','ੂ':'uu','ੇ':'e','ੈ':'ai','ੋ':'o','ੌ':'au','ੰ':'n','ਂ':'n','ਃ':'h','੍':'',
  // ── MALAYALAM ──
  'അ':'a','ആ':'aa','ഇ':'i','ഈ':'ii','ഉ':'u','ഊ':'uu','എ':'e','ഏ':'ee','ഐ':'ai','ഒ':'o','ഓ':'oo','ഔ':'au',
  'ക':'k','ഖ':'kh','ഗ':'g','ഘ':'gh','ങ':'ng','ച':'ch','ഛ':'chh','ജ':'j','ഝ':'jh','ഞ':'ny',
  'ട':'t','ഠ':'th','ഡ':'d','ഢ':'dh','ണ':'n','ത':'t','ഥ':'th','ദ':'d','ധ':'dh','ന':'n',
  'പ':'p','ഫ':'ph','ബ':'b','ഭ':'bh','മ':'m','യ':'y','ര':'r','റ':'rr','ല':'l','ള':'l','ഴ':'zh','വ':'v','ശ':'sh','ഷ':'sh','സ':'s','ഹ':'h',
  'ാ':'aa','ി':'i','ീ':'ii','ു':'u','ൂ':'uu','െ':'e','േ':'ee','ൈ':'ai','ൊ':'o','ോ':'oo','ൌ':'au','ൗ':'au','ം':'m','ഃ':'h','്':'',
  // ── ARABIC/URDU ──
  '\u0627':'a','\u0628':'b','\u062A':'t','\u062B':'th','\u062C':'j','\u062D':'h','\u062E':'kh',
  '\u062F':'d','\u0630':'dh','\u0631':'r','\u0632':'z','\u0633':'s','\u0634':'sh','\u0635':'s',
  '\u0636':'d','\u0637':'t','\u0638':'z','\u0639':'a','\u063A':'gh','\u0641':'f','\u0642':'q',
  '\u0643':'k','\u0644':'l','\u0645':'m','\u0646':'n','\u0647':'h','\u0648':'w','\u064A':'y',
};

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

function transliterate(str) {
  if (!str) return '';
  const chars = [...str];
  let result = '';
  for (let i = 0; i < chars.length; i++) {
    const char = chars[i];
    const code = char.codePointAt(0);
    if (code < 0x0600) { result += char; continue; }
    if (_isVirama(code)) continue;
    const mapped = indicMap[char];
    if (mapped === undefined) { result += char; continue; }
    result += mapped;
    if (_isCons(code) && mapped !== '') {
      const nextCode = (i + 1 < chars.length) ? chars[i + 1].codePointAt(0) : -1;
      if (_isVirama(nextCode)) {
        i++;
      } else if (!_isMatra(nextCode)) {
        result += 'a';
      }
    }
  }
  return result.replace(/\s+/g, ' ').trim();
}

// ─── Test Cases ───────────────────────────────────────────────────────────────
// Format: [native_script, expected_romanization, description]
const testSuites = {
  'Hindi (Devanagari)': [
    ['नमस्ते',       'namaste',      'namaste'],
    ['भारत',         'bhaaraT',      'Bharat — accept approximate'],
    ['मेरा नाम',     'meraa naam',   'mera naam'],
    ['कैसे हो',      'kaise ho',     'kaise ho'],
    ['पानी',         'paanii',       'paani'],
    ['खाना',         'khaanaa',      'khana'],
    ['धन्यवाद',      'dhanyavaad',   'dhanyavad — accept'],
  ],
  'Kannada': [
    ['ನಮಸ್ಕಾರ',      'namaskaara',   'namaskara'],
    ['ಹೇಗಿದ್ದೀರಿ',  'heegiddiiri',  'hegiddiri'],
    ['ನೀರು',         'niiru',        'niru'],
    ['ಕನ್ನಡ',        'kannada',      'kannada'],
    ['ಬೆಂಗಳೂರು',    'bengaluuru',   'bengaluru'],
  ],
  'Bengali': [
    ['নমস্কার',      'namaskara',    'namaskara'],
    ['আমি',          'ami',          'ami'],
    ['বাংলাদেশ',     'bangladesha',  'bangladesha'],
    ['ভালো আছি',    'bhalo achhi',  'bhalo achhi'],
    ['ধন্যবাদ',      'dhanjabada',   'dhanjabada'],
  ],
  'Tamil': [
    ['வணக்கம்',      'vanakkam',     'vanakkam'],
    ['நன்றி',        'nantri',       'nandri'],
    ['தமிழ்',        'thamizh',      'tamizh'],
    ['எப்படி',       'eppathi',      'eppadi'],
    ['சரி',          'chari',        'sari/chari'],
  ],
  'Telugu': [
    ['నమస్కారం',    'namaskaaram',  'namaskaaram'],
    ['తెలుగు',       'thelugu',      'telugu'],
    ['ధన్యవాదాలు',  'dhanyavaadaalu', 'dhanyavaadalu'],
    ['ఎలా ఉన్నారు', 'elaa unnaaru', 'ela unnaru'],
  ],
  'Gujarati': [
    ['નમસ્તે',       'namaste',      'namaste'],
    ['ગુજરાત',       'gujaraata',    'gujarat'],
    ['કેમ છો',       'kema chho',    'kem cho'],
    ['આભાર',         'aabhaara',     'abhar'],
    ['પાણી',         'paanii',       'pani'],
  ],
  'Punjabi (Gurmukhi)': [
    ['ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ', 'sati srii akaala', 'sat sri akal'],
    ['ਪੰਜਾਬ',         'panjaaba',    'punjab'],
    ['ਧੰਨਵਾਦ',        'dhannavaada', 'dhanwad'],
    ['ਕਿਵੇਂ ਹੋ',      'kiven ho',    'kiven ho'],
  ],
  'Malayalam': [
    ['നമസ്കാരം',    'namaskaaram',  'namaskaaram'],
    ['മലയാളം',      'malayaalam',   'malayalam'],
    ['നന്ദി',        'nandi',        'nandi'],
    ['എങ്ങനെ',      'engngane',     'engane'],
    ['വെള്ളം',      'vellam',       'vellam'],
  ],
  'Arabic/Urdu': [
    ['سلام',         'slaam',        'salaam'],
    ['شكر',          'shkr',         'shukr'],
    ['مرحبا',        'mrhba',        'marhaba'],
  ],
};

// ─── Scoring ─────────────────────────────────────────────────────────────────
// Exact match = 1.0 | Prefix match (≥80% chars) = 0.7 | Partial overlap = 0.4 | No match = 0
function score(got, expected) {
  if (got === expected) return 1.0;
  // Normalize
  const g = got.toLowerCase().replace(/\s+/g,'');
  const e = expected.toLowerCase().replace(/\s+/g,'');
  if (g === e) return 1.0;
  // Common prefix
  let common = 0;
  const minLen = Math.min(g.length, e.length);
  for (let i = 0; i < minLen; i++) { if (g[i] === e[i]) common++; else break; }
  const prefixRatio = minLen > 0 ? common / Math.max(g.length, e.length) : 0;
  if (prefixRatio >= 0.8) return 0.85;
  // Char overlap (any position)
  let overlap = 0;
  const visited = new Array(e.length).fill(false);
  for (const ch of g) {
    const idx = e.indexOf(ch);
    if (idx !== -1 && !visited[idx]) { overlap++; visited[idx] = true; }
  }
  const overlapRatio = Math.max(g.length, e.length) > 0 ? overlap / Math.max(g.length, e.length) : 0;
  if (overlapRatio >= 0.6) return 0.6;
  if (overlapRatio >= 0.4) return 0.4;
  return 0.1;
}

// ─── Run Tests ────────────────────────────────────────────────────────────────
const BOLD = '\x1b[1m'; const RESET = '\x1b[0m';
const GREEN = '\x1b[32m'; const YELLOW = '\x1b[33m'; const RED = '\x1b[31m'; const CYAN = '\x1b[36m';

let totalScore = 0, totalTests = 0;
const results = [];

for (const [lang, cases] of Object.entries(testSuites)) {
  let langScore = 0;
  const langResults = [];

  for (const [native, expected, desc] of cases) {
    const got = transliterate(native);
    const s = score(got, expected);
    langScore += s;
    totalScore += s;
    totalTests++;
    const pct = Math.round(s * 100);
    const col = s >= 0.85 ? GREEN : s >= 0.5 ? YELLOW : RED;
    langResults.push({ native, got, expected, desc, pct, col });
  }

  const langPct = Math.round((langScore / cases.length) * 100);
  const langCol = langPct >= 85 ? GREEN : langPct >= 60 ? YELLOW : RED;
  results.push({ lang, langPct, langCol, langResults, cases });
}

// ─── Print Results ────────────────────────────────────────────────────────────
console.log(`\n${BOLD}${CYAN}╔════════════════════════════════════════════════════════════╗`);
console.log(`║         VOXA AI — Transliteration Accuracy Report          ║`);
console.log(`╚════════════════════════════════════════════════════════════╝${RESET}\n`);

for (const { lang, langPct, langCol, langResults } of results) {
  console.log(`${BOLD}${langCol}▶ ${lang} — ${langPct}%${RESET}`);
  for (const { native, got, expected, desc, pct, col } of langResults) {
    const bar = '█'.repeat(Math.round(pct / 10)).padEnd(10, '░');
    console.log(`  ${col}[${pct}%] ${bar}${RESET}  ${native} → ${BOLD}${got}${RESET}  (expected: ${expected})  // ${desc}`);
  }
  console.log();
}

const overallPct = Math.round((totalScore / totalTests) * 100);
const overallCol = overallPct >= 85 ? GREEN : overallPct >= 60 ? YELLOW : RED;
console.log(`${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}`);
console.log(`${BOLD}${overallCol}  OVERALL ACCURACY: ${overallPct}% (${totalTests} tests across ${Object.keys(testSuites).length} languages)${RESET}`);
console.log(`${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n`);

// ─── Low-accuracy languages ───────────────────────────────────────────────────
const lowAccuracy = results.filter(r => r.langPct < 75);
if (lowAccuracy.length > 0) {
  console.log(`${BOLD}${RED}⚠  Languages below 75% — need fixes:${RESET}`);
  for (const { lang, langPct } of lowAccuracy) {
    console.log(`   • ${lang}: ${langPct}%`);
  }
  console.log();
}

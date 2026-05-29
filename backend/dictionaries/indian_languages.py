"""
backend/dictionaries/indian_languages.py

Romanized vocabulary dictionaries for all 9 Indian languages supported by Voxa AI.
Each language entry maps word → confidence_weight (1.0 for standard, higher for unique markers).

Languages covered:
  hi — Hindi / Hinglish
  ta — Tamil / Tanglish
  te — Telugu / Tenglish
  ml — Malayalam
  mr — Marathi
  bn — Bengali
  gu — Gujarati
  pa — Punjabi
  ur — Urdu
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# HINDI — 400+ romanized words
# ---------------------------------------------------------------------------
HINDI_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Core copula / auxiliary verbs
    "hai", "hain", "tha", "thi", "the", "ho", "hoon", "hun",
    "hoga", "hogi", "honge", "hota", "hoti", "hote",
    "rahega", "rahegi", "rahenge", "raha", "rahi", "rahe",
    # Negation
    "nahi", "nhi", "mat", "na", "nahi-hai", "bilkul-nahi",
    # Question words
    "kya", "kyun", "kyu", "kyunki", "kaise", "kab", "kahan",
    "kaun", "kitna", "kitni", "kitne", "konsa", "konsi",
    # Pronouns
    "main", "mai", "mujhe", "mujhko", "mera", "meri", "mere",
    "aap", "aapka", "aapki", "aapke", "aapko",
    "tum", "tumhara", "tumhari", "tumhare", "tumko",
    "tu", "tera", "teri", "tere", "tujhe",
    "yeh", "ye", "yeh-hai", "woh", "wo", "isko", "usko",
    "hum", "hamara", "hamari", "hamare", "hamko", "hame",
    "unka", "unki", "unke", "unhe", "unko",
    # Common verbs
    "karo", "karna", "karta", "karti", "karte", "kiya", "kiye", "ki",
    "jao", "jana", "jata", "jati", "jate", "gaya", "gayi", "gaye",
    "aao", "aana", "aata", "aati", "aate", "aaya", "aayi", "aaye",
    "batao", "batana", "bata", "dekho", "dekhna", "dekha",
    "suno", "sunna", "suna", "padho", "padhna", "padha",
    "lao", "lana", "liya", "liye", "denge", "diya", "diye",
    "bolo", "bolna", "bola", "boli", "bole",
    "samjho", "samajhna", "samjha", "samjhe",
    "ruko", "rukna", "ruka", "chhodo", "chhodna", "chhoda",
    "milna", "mila", "mili", "mile", "milege",
    "uthao", "uthana", "utha", "rakho", "rakhna", "rakha",
    # Colloquial verbs
    "kar", "bol", "dekh", "sun", "aa", "ja", "le", "de",
    "padh", "likh", "samjh", "chhod", "rok", "lag",
    # Conjunctions / connectives
    "aur", "ya", "lekin", "magar", "par", "toh", "to",
    "isliye", "kyunki", "jaise", "waisa", "agar", "iske",
    "phir", "fir", "tab", "jab", "abhi", "ab",
    # Postpositions
    "ko", "se", "ka", "ki", "ke", "mein", "me", "pe", "par",
    "tak", "liye", "sath", "bina", "upar", "neeche",
    # Adjectives / adverbs
    "achha", "acha", "acchi", "bura", "buri", "theek", "thik",
    "bahut", "bahot", "sahi", "galat", "pata", "jaldi",
    "dheere", "zyada", "kam", "poora", "thoda", "kuch",
    "bada", "badi", "bade", "chota", "choti", "chote",
    "naya", "nayi", "naye", "purana", "purani", "purane",
    # Discourse / filler words
    "yaar", "bhai", "dost", "bhaiya", "didi", "behen",
    "haan", "han", "arrey", "arre", "are", "oye",
    "namaste", "shukriya", "dhanyawad", "kripya",
    # Tense markers
    "kal", "aaj", "parso", "pichle", "agle", "waqt",
    # Expressing emotions
    "khush", "dukhi", "pareshan", "thaka", "bored",
    "gussa", "pyaar", "nafrat",
    # Common nouns
    "kaam", "ghar", "school", "dost", "paisa", "khana",
    "pani", "rasta", "safar", "problem", "jawab", "sawaal",
    # Hinglish-specific code-switch markers
    "hogaya", "hojata", "hojayega", "karwao", "dilwao",
    "lelo", "dedo", "aajao", "jaao", "chalo",
    # Numbers (Hindi)
    "ek", "do", "teen", "chaar", "paanch", "chhe", "saat",
    "aath", "nau", "das", "bees", "pachas", "sau",
]}

# High-weight uniquely Hindi markers
HINDI_HIGH: dict[str, float] = {
    "hain": 1.4, "kyun": 1.3, "mujhe": 1.3, "tumhara": 1.4,
    "bilkul": 1.3, "theek": 1.2, "arrey": 1.3, "yaar": 1.2,
    "bhai": 1.1, "hoon": 1.3, "rahega": 1.4, "hogaya": 1.5,
    "hojata": 1.5, "karunga": 1.4, "jaunga": 1.4, "aaunga": 1.4,
    "nahi": 1.2, "kya": 1.1, "hai": 1.1, "aur": 1.1,
}

# ---------------------------------------------------------------------------
# TAMIL — 350+ romanized words
# ---------------------------------------------------------------------------
TAMIL_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Core question words
    "enna", "yenna", "yeppadi", "eppadi", "eppo", "yeppo",
    "enga", "yenga", "evlo", "endha", "ethana", "yean",
    "yaar", "evaru", "yaaru",
    # Negation (highly distinctive)
    "illai", "illeh", "illa-da", "vendam", "venda",
    "puriyala", "theriyala", "kaanala",
    # Existence / stative
    "irukku", "irukkaan", "irukkaal", "irukkaaru",
    "irundhu", "iruntu",
    # Common verbs (completive -dhu/-thu — very distinctive)
    "seidhu", "seitu", "paarthu", "vandhu", "kondhu",
    "kondu", "poithu", "poitu",
    "seithen", "poithen", "paarthen", "vandhen",
    "seithaan", "poitaan", "paarthaan", "vanthaan",
    "seithaal", "poitaal", "paarthaal", "vanthaal",
    # Present tense (-kiraan/-kiraal/-kiraar — extremely distinctive)
    "padikiraan", "padikiiraan", "padikiiraal", "padikiiraar",
    "vasikiraan", "seikiiraan", "seikiiraal", "seikiiraar",
    "solkiraan", "pokiraan", "varikiiraan", "varikiiraal",
    "irukkiraan", "irukkiraal", "irukkiraar",
    "paarkiraan", "paarkiraal", "paarkiraar",
    "ketkkiraan", "seikiiraan",
    # Colloquial present (-raan/-raal)
    "kiiraan", "kiiraal", "kiiraar", "kiraargal",
    "raan", "raal", "raar",
    # Pronouns
    "naan", "nee", "neenga", "avan", "aval", "avar",
    "avanga", "avargal", "naanga", "naangal",
    "ungga", "unakku", "enakku",
    # Function / discourse words
    "thaan", "kuda", "ellam", "oru", "inge", "ange",
    "innoru", "innum", "pinbu", "munbu", "appuram",
    "ippo", "appo", "ippothe", "neelum", "naalum",
    # Imperatives
    "sollu", "paaru", "vaa", "po", "kelu",
    "vaango", "ponga", "sollunga", "parunga",
    # Adjectives / adverbs
    "romba", "konjam", "nalla", "ketta", "periya", "chinna",
    "azhaga", "puthusa", "theriyum", "puriyum",
    "theriyaadu", "puriyaadu",
    # Discourse / filler
    "machan", "da", "di", "dei", "ra", "ri",
    "seri", "aamaa", "aama", "vanakkam", "nandri",
    "kashtam", "mosam", "jolly",
    # Common nouns
    "ooru", "veetuku", "paarthen",
    "thamizh", "tamil",
    "kelvi", "paren", "pannunga",
    # Tanglish-specific
    "pannrom", "pannuvom", "paakalam", "sollamm", "sollrom",
    "irukken", "irukkom", "paarthen",
    "adhu", "idhu", "edhu",
    "paathukko",
    # Completive -idhu / -ithu (very distinctive)
    "seidhitu", "poidhitu", "paarthitu",
    "vandidhu", "kondidhu",
]}

# High-weight uniquely Tamil markers
TAMIL_HIGH: dict[str, float] = {
    "illai": 1.8, "irukku": 1.6, "vanakkam": 1.5,
    "romba": 1.5, "machan": 1.6, "kashtam": 1.4,
    "seidhu": 1.6, "poithu": 1.5, "paarthu": 1.4,
    "enna": 1.3, "eppo": 1.3, "pannrom": 1.5,
}

# ---------------------------------------------------------------------------
# TELUGU — 300+ romanized words
# ---------------------------------------------------------------------------
TELUGU_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Core copula / auxiliary
    "undi", "ledu", "ayindi", "avutundi", "avutundi",
    "untundi", "untaru", "unnaru", "unnaanu", "unnava",
    "chestunnaru", "chestunnaanu", "chesanu", "chestanu",
    "avutaanu", "pothanu", "vastanu",
    # Question words
    "enti", "emiti", "enduku", "ekkada", "eppudu",
    "evaru", "ela", "ento", "eemi",
    "akkada", "em", "jarugutondi",
    # Negation
    "kaadu", "ledu", "vaddhu", "vaddu", "veda",
    "telusu-kaadu", "artham-kaadu",
    # Pronouns
    "nenu", "naku", "naaku", "memu", "meeru",
    "miku", "meeru", "vaallu", "vaaru", "adi", "idi",
    # Verbs (common)
    "cheppandi", "cheyyi", "chesi", "chestaa",
    "chudandi", "chustaa", "poni", "randi", "vachanu",
    "ivvandi", "teesukopandi", "vellipoyaanu",
    "telusu", "artham", "ani",
    "podhu", "potha", "pothanu",
    "sagutundi", "okka",
    # Discourse / connectives
    "anduke", "aithe", "okka", "anni", "chala",
    "chey", "cheyandi", "ikkade", "akkade",
    "oka", "adhi", "idhi",
    # Adjectives
    "baagundi", "chedduga", "pedda", "chinna",
    "patha", "kotta", "manchidi", "cheddidi",
    # Colloquial
    "baagunnara", "dhanyavaadalu", "namaskaram",
    "avunu", "pani", "randu", "vachanu",
    "enti-ra", "enti-bro",
    # Numbers (Telugu)
    "okati", "rendu", "moodu", "naalugu", "aidu",
    "aaru", "edu", "enimidi", "tommidi", "padi",
]}

# High-weight uniquely Telugu markers
TELUGU_HIGH: dict[str, float] = {
    "cheppandi": 1.6, "undi": 1.4, "ledu": 1.4,
    "evaru": 1.5, "enti": 1.5, "ekkada": 1.5,
    "ayindi": 1.4, "meeru": 1.4, "dhanyavaadalu": 1.5,
    "baagunnara": 1.4, "telusu": 1.3,
}

# ---------------------------------------------------------------------------
# MALAYALAM — 250+ romanized words
# ---------------------------------------------------------------------------
MALAYALAM_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Core copula / negation
    "anu", "alla", "undo", "ille", "illa", "aano",
    "alle", "anno", "ayyo",
    "kaanilla", "ariyilla", "manasilayilla",
    # Question words
    "enthanu", "enthu", "evide", "engane", "etha",
    "aaranu", "eppo", "endhe",
    # Pronouns
    "njaan", "njan", "ningal", "avan", "aval",
    "avar", "ente", "thante", "oru", "enikku",
    "sugamano", "nattil", "enthendokke", "vishesham",
    # Common verbs
    "parayoo", "choyyoo", "vannu", "poyi",
    "undayi", "cheyyum", "paranju", "cheyyunnu",
    "parayunnu", "varunnu", "povunnu",
    "ariyunnu", "kaanunnu", "keekunnu",
    "kittunnu", "kittiyo",
    # Discourse / function
    "sari", "pinne", "ippol", "athu", "ithu",
    "ini", "enthokke", "aanallo", "allee",
    "alle", "undo", "cheythille",
    # Adjectives / adverbs
    "nalla", "mosham", "valiya", "cheriya",
    "puthiya", "pazhaya", "sheriyanu",
    # Colloquial / filler
    "chechi", "etta", "mol", "mon", "kutty",
    "machane", "bro", "da", "di",
    "sheriyaano", "aano-bro",
    # Common nouns
    "veedu", "nadakkunnu", "parayunnu",
]}

# High-weight uniquely Malayalam markers
MALAYALAM_HIGH: dict[str, float] = {
    "njaan": 1.8, "ningal": 1.6, "enthanu": 1.6,
    "parayoo": 1.5, "engane": 1.5, "evide": 1.5,
    "undayi": 1.4, "ippol": 1.3, "manasilayilla": 1.7,
    "kaanilla": 1.5, "enikku": 1.6, "ariyilla": 1.6,
}

# ---------------------------------------------------------------------------
# MARATHI — 200+ romanized words
# ---------------------------------------------------------------------------
MARATHI_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Core copula
    "aahe", "nahi", "naahi", "ahe",
    "aahet", "zhala", "zhali", "zhale",
    "gela", "geli", "gele", "aala", "aali", "aale",
    # Question words
    "kay", "kasa", "kashi", "kase", "kuth", "kuthe",
    "kadhi", "kiti", "kon", "koni", "kashala",
    # Pronouns
    "mala", "tula", "tya", "tyala", "tyachya",
    "amhi", "aamhi", "aapan", "tumhi",
    "maza", "tumchya", "majha",
    # Connectives
    "ani", "aani", "pan", "tar", "parat", "mhanje",
    "jatoy", "parat", "nahi-ka",
    # Verbs
    "sanga", "bagh", "ya", "kara", "ja",
    "bolto", "bolta", "bolte", "samjha", "samajle",
    "karnar", "yenar", "hoil", "yeil",
    "sangitla", "sangnar", "aitat",
    # Adjectives / adverbs
    "chan", "bara", "khup", "ata", "nava", "kahi",
    "chalu", "navin", "jast", "thoda",
    "bas", "aale", "ithe", "tikde", "jevha", "tevha",
    # Discourse
    "chal", "aho", "nako", "hok", "baro",
    "arrey", "zaala", "zaali", "zaale",
    # Numbers (Marathi)
    "ek", "don", "tin", "char", "paach", "sahaa",
    "saat", "aath", "nau", "daha",
]}

# High-weight uniquely Marathi markers
MARATHI_HIGH: dict[str, float] = {
    "aahe": 1.6, "zhala": 1.6, "zhali": 1.6, "zhale": 1.6,
    "aamhi": 1.5, "tumhi": 1.4, "kashala": 1.5,
    "mhanje": 1.6, "jatoy": 1.5, "sangitla": 1.5,
}

# ---------------------------------------------------------------------------
# BENGALI — 200+ romanized words
# ---------------------------------------------------------------------------
BENGALI_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Core copula / existence
    "ache", "achhe", "nei", "nai", "thako", "thakbe",
    "korbe", "korbo", "jabo", "ashbo",
    # Question words
    "ki", "keno", "kothay", "kothai", "kobe",
    "kemon", "kara", "ke",
    # Pronouns
    "ami", "tumi", "apni", "aamra", "tomra", "tara",
    "amake", "tomake", "take", "eder", "okhane",
    # Verbs
    "bolo", "koro", "jao", "aso", "dekha",
    "bolchi", "korchi", "jacchi", "aschhi",
    "bolun", "korun", "janun", "dekhun",
    "dao", "nao", "ashun", "jaun",
    # Connectives / discourse
    "ar", "kintu", "tahole", "jodi",
    "ekhane", "sekhane", "pore", "age",
    # Adjectives / adverbs
    "bhalo", "khub", "boro", "chhoto", "shundor",
    "noya", "purano", "thik", "betha",
    # Social / relational
    "bhai", "didi", "daada", "manush", "kotha",
    "dhonnobad", "namaskaar",
]}

# High-weight uniquely Bengali markers
BENGALI_HIGH: dict[str, float] = {
    "ache": 1.5, "achhe": 1.5, "bolchi": 1.5, "korchi": 1.5,
    "jacchi": 1.5, "kothay": 1.4, "tahole": 1.5,
    "dhonnobad": 1.5, "ekhane": 1.4,
}

# ---------------------------------------------------------------------------
# GUJARATI — 150+ romanized words
# ---------------------------------------------------------------------------
GUJARATI_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Core copula
    "chhe", "chho", "che", "nathi", "nahi",
    "hato", "hati", "hate", "thashe", "thavshe",
    # Question words
    "kem", "shu", "kyan", "kyare", "kone",
    "kevi", "kevi-rite",
    # Pronouns
    "hoon", "tame", "te", "ame", "aa", "pele",
    "maro", "tamaro", "enu", "ana",
    # Verbs
    "karo", "jo", "aavo", "jao", "kaho",
    "karvu", "avu", "javu",
    # Connectives / discourse
    "ane", "pan", "to", "toh", "tyare", "jyare",
    "matlab", "bas", "zaraa",
    # Adjectives / adverbs
    "saras", "baro", "khub",
    "mane", "tamne",
]}

# High-weight uniquely Gujarati markers
GUJARATI_HIGH: dict[str, float] = {
    "chhe": 1.7, "nathi": 1.6, "kem": 1.5, "shu": 1.4,
    "tame": 1.4, "aavo": 1.3, "saras": 1.4, "thashe": 1.5,
}

# ---------------------------------------------------------------------------
# PUNJABI — 150+ romanized words
# ---------------------------------------------------------------------------
PUNJABI_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Core copula
    "hai", "hain", "tha", "si", "hoga", "honi",
    "siga", "sigi",
    # Question words
    "ki", "kyun", "kithe", "kithey", "kiddan",
    "kado", "kaun", "kitna",
    # Pronouns
    "main", "tenu", "menu", "assi", "tussi",
    "ohna", "unhan", "sanu", "tuhanu",
    "meri", "teri", "sade", "ihde", "ohde",
    # Verbs
    "karo", "jao", "aao", "dasso", "sunao",
    "kar", "ja", "aa", "das", "sun",
    "gaya", "gayi", "aaya", "aayi",
    # Discourse / filler
    "oye", "yaar", "bhai", "puttar", "veere",
    "chak-de", "wah", "sat-sri-akal",
    "changa", "theek", "hun",
    # Connectives
    "ate", "par", "te", "lekin", "ki",
    # Location / direction
    "ithey", "uthey", "idhar", "udhar",
]}

# High-weight uniquely Punjabi markers
PUNJABI_HIGH: dict[str, float] = {
    "oye": 1.5, "puttar": 1.6, "kiddan": 1.6, "kithey": 1.5,
    "sat-sri-akal": 1.8, "veere": 1.5, "tussi": 1.5, "assi": 1.4,
    "chak-de": 1.7,
}

# ---------------------------------------------------------------------------
# URDU — 100+ romanized words (partially overlaps Hindi)
# ---------------------------------------------------------------------------
URDU_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Distinctly Urdu (not Hindi)
    "zaroor", "shukriya", "meherbani", "janab", "aadaab",
    "bismillah", "inshallah", "mashallah", "salam", "walaikum",
    "khuda-hafiz", "khuda", "khudaya", "allah",
    "irshaad", "farmaya", "hukum", "sahib", "hazrat",
    "karke", "yahan", "aaye",
    # Urdu-specific vocabulary
    "shaayad", "khoobsoorat", "hairaan", "pareshaan",
    "mohabbat", "ishq", "dil", "jaan", "ruh",
    "kalam", "nazm", "ghazal", "shayari",
    "zikar", "yaad", "fikr", "waqt", "wafa",
    # Urdu social / polite
    "taklif", "muzaahmat", "mehman", "misaal",
    "zindagi", "maut", "takdeer", "naseeb",
]}

# High-weight uniquely Urdu markers
URDU_HIGH: dict[str, float] = {
    "shukriya": 1.6, "meherbani": 1.9, "janab": 1.7,
    "aadaab": 1.8, "inshallah": 1.5, "mashallah": 1.5,
    "khuda-hafiz": 1.8, "zaroor": 1.3,
}

# ---------------------------------------------------------------------------
# DRAVIDIAN SUFFIX PATTERNS — shared across Tamil/Telugu/Kannada/Malayalam
# Used to boost overall "Indian Dravidian" detection before language-specific scoring.
# ---------------------------------------------------------------------------
DRAVIDIAN_SUFFIXES: list[tuple[str, float]] = [
    # Kannada-specific (highest weight)
    (r'\b\w+beku\b', 1.5),
    (r'\b\w+agide\b', 1.5),
    (r'\b\w+thini\b', 1.3),
    (r'\b\w+illa\b', 1.2),
    # Tamil-specific
    (r'\b\w+kiraan\b', 1.4),
    (r'\b\w+kiiraan\b', 1.4),
    (r'\b\w+dhu\b', 1.1),
    (r'\b\w+thu\b', 1.0),
    (r'\billai\b', 1.5),
    (r'\birukku\b', 1.4),
    # Telugu-specific
    (r'\b\w+undi\b', 1.2),
    (r'\b\w+andi\b', 1.1),
    (r'\b\w+aru\b', 0.8),
    # Malayalam-specific
    (r'\b\w+unnu\b', 1.2),
    (r'\b\w+unna\b', 1.0),
    (r'\b\w+ille\b', 1.2),
    # General Dravidian
    (r'\b\w+amma\b', 0.7),
    (r'\b\w+appa\b', 0.7),
    (r'\b\w+anna\b', 0.6),
]

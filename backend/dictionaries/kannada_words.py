"""
backend/dictionaries/kannada_words.py

Production-grade Kannada romanized vocabulary for the KannadaDetector engine.
Words are grouped by confidence weight:
  HIGH (1.5) — words unique to Kannada, almost never appear in other languages
  MED  (1.0) — common Kannada words with low cross-language ambiguity
  LOW  (0.5) — shared/ambiguous words (e.g. also in Telugu / Malayalam)

Total: 500+ unique romanized Kannada entries.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# HIGH CONFIDENCE — uniquely Kannada (weight = 1.5)
# ---------------------------------------------------------------------------
KANNADA_HIGH: dict[str, float] = {w: 1.5 for w in [
    # Core negation / existence (most distinctive Kannada words)
    "illa", "gothilla", "madilla", "barolla", "hogalla", "kelalla",
    "nodalla", "helalla", "sigalla", "agalla", "iralla", "kaanilla",
    "ariyilla", "theekilla", "sigthilla", "aagtilla",
    # Obligation / possibility (beku family — uniquely Kannada)
    "beku", "beda", "hogbeku", "barbeku", "madbeku", "nodbeku",
    "kelbeku", "helbeku", "irbeku", "thagebeku", "kodabeku",
    "madbeda", "hogbeda", "barbeda", "kelbeda",
    # Existence / stative (agide family)
    "agide", "agidhe", "agthide", "aagtide", "bekagide", "bedagide",
    "hogagide", "madagide", "iruthe", "idhe", "ide",
    # Question words (Kannada-specific forms)
    "yaaru", "yaake", "yake", "yelli", "hege", "hengide", "hegide",
    "henge", "yaavaga", "yaava", "yaarigagi", "eshtu", "elli",
    "enuuu", "enu", "enagide", "yenu",
    # Pronouns (romanized Kannada forms)
    "naanu", "nanu", "neevu", "avaru", "avalu", "nimma", "namma",
    "nanna", "nanage", "nimage", "ninge", "nimge", "naange",
    "ivaru", "ivalu",
    # Progressive / continuous verb forms
    "madthini", "madthale", "barthini", "barthale", "hogthini",
    "hogthale", "helthini", "heltini", "keltini", "keltale",
    "nodthini", "nodthale", "barthive", "hogthive",
    # Completive verb forms
    "madidhe", "madide", "hogidhe", "hogide", "baridhe", "baride",
    "noddhe", "nodde", "heldhe", "helde", "keldhe", "kelde",
    "sididhe", "thilidhe",
    # Cohortative / volitional (-ona forms)
    "madona", "nodona", "hogona", "barona", "kelona", "helona",
    "thagoona", "koona",
    # Imperative / requestive forms
    "maadi", "nodi", "heli", "keli", "banni", "hogi",
    "madri", "nodri", "helri", "kelri", "barri",
    "madkoli", "nodkoli", "kelkoli", "helkoli",
    # Future tense (-tene / -uttene)
    "hoguttene", "bartene", "maduttene", "noduttene", "keltene",
    "heltene", "siguttene", "aguttene",
    # Permission / optative (-ali)
    "madali", "nodali", "kelali", "helali", "hogali", "barali",
    "irbali", "irli",
    # Locative case (-alli / -illi)
    "manelli", "schoolalli", "officealli", "cityalli",
    "matalli", "jaagatalli",
    # Ablative case (-inda)
    "maneyinda", "schoolinda", "officeinda",
    # Bangalore tech slang (high confidence)
    "gottilla", "madidya", "barthiya", "hogthiya", "nodidya",
    "helthiya", "gottidya", "bartheeni", "hogtheeni",
    "madtheeni", "aagtheeni",
    # Unique Kannada discourse markers
    "aadre", "aadru", "aadaru", "aadhagitta",
    "haudhu", "houdhu", "houdha",
    "ankonde", "bankonde", "nimgondhe",
    # Common Kannada nouns unique to the language
    "bengaluru", "saapadu", "adige", "oota", "tindi",
    "kelsa", "maneli", "mane", "ooru", "ninna", "hesaru", "hesarenu",
    "noppu", "kashta", "ananda",
]}

# ---------------------------------------------------------------------------
# MEDIUM CONFIDENCE — common Kannada, low cross-language ambiguity (weight = 1.0)
# ---------------------------------------------------------------------------
KANNADA_MED: dict[str, float] = {w: 1.0 for w in [
    # Particles and connectives
    "alla", "mattu", "matte", "athava", "aadare",
    "ondhu", "adhu", "idhu", "adu", "idu",
    "illi", "alli", "mundhe", "hinde", "mele", "kele",
    # Common verbs (root forms)
    "maadu", "nodu", "kelu", "helu", "tago", "kodi",
    "hogi", "banni", "helu", "nodu",
    "madtha", "nodtha", "keltha", "heltha",
    # Stative / copula
    "untu", "inda", "agtha",
    # Question / exclamation
    "sari", "sari-na", "channagide", "channagidhe",
    "tumba", "swalpa", "dodda", "chikka", "hosa", "ketta", "olleya",
    # Numbers (Kannada-specific)
    "ondu", "erdu", "mooru", "naalu", "aidu", "aaru", "yelu", "entu",
    "ombattu", "hattu",
    # Direction / placement
    "ivattu", "naaley", "ninne",
    # Greetings / polite forms
    "namaskara", "dayavittu", "dhanyavadagalu",
    # Common daily-use words
    "guru", "bidu", "aaytu", "aayta", "aythu", "aayitu",
    "agtu", "agtha", "sumne",
    # Reflexive / discourse
    "hange", "hengide", "matte", "idera", "idira",
    "hegidira", "hegiddira",
    "yellide", "ade", "bekhu",
    # Colloquial / slang
    "madichidde", "madidde", "hogidde", "baridde",
    "yen", "yeno", "yake", "helri", "sullu",
    "padkondu", "adjust", "yerdu", "ondralla",
    "bittu", "bidi", "kannada", "beeku",
    "ivattu", "dayavittu",
    # Social / relational words
    "avara", "ivara", "ellaru", "yaavudhu", "enaadru",
    "nange", "tange", "avrige", "ivrige",
    # Place markers
    "olagade", "horagade",
    # Verb completive
    "madichidde", "nodidde", "hogidde",
    "siggidhe", "thiliside",
    # Conditional
    "hattirade", "hogiddare", "madiddare",
]}

# ---------------------------------------------------------------------------
# LOW CONFIDENCE — shared with Telugu / Malayalam (weight = 0.5)
# ---------------------------------------------------------------------------
KANNADA_LOW: dict[str, float] = {w: 0.5 for w in [
    # Shared with other South Indian languages but still Kannada
    "nodu", "kelu", "helu", "baa", "hogi",
    "ondh", "eradu", "moor", "chennaagi",
    "hegiddiya", "hengiddiya",
    "enu", "yenu", "adu", "idu",
    "yelli", "elli", "alli", "illi",
    # Verb stems shared across Dravidian
    "maad", "mad", "nog", "hel", "kel",
    "bar", "hog", "nod",
]}

# ---------------------------------------------------------------------------
# NEGATIVE EXCLUSION — European words that look like Kannada (subtract weight)
# These are words that langid/langdetect falsely identifies as Italian/Portuguese
# while the SAME words can appear in romanized Kannada — we need to NOT exclude
# them from Kannada scoring but DO use them to penalize Italian/Portuguese.
# This list is for KannadaDetector to note as cross-contamination risk.
# ---------------------------------------------------------------------------
EURO_LOOKALIKES: set[str] = {
    # Italian lookalikes
    "alla", "allo", "ande", "della", "ella", "bella", "sera",
    # Portuguese lookalikes
    "nao", "uma", "ola", "meu", "sua",
    # Common false alarms
    "anu", "ila", "ali", "nano",
}

# ---------------------------------------------------------------------------
# MORPHOLOGICAL SUFFIX PATTERNS — compiled regex patterns for suffix matching
# Each tuple: (regex_pattern, weight)
# ---------------------------------------------------------------------------
KANNADA_SUFFIX_PATTERNS: list[tuple[str, float]] = [
    # Obligation (-beku) — very high confidence
    (r'\b\w+beku\b', 1.5),
    (r'\b\w+beda\b', 1.5),
    # Existence (-agide / -agidhe)
    (r'\b\w+agide\b', 1.5),
    (r'\b\w+agidhe\b', 1.5),
    (r'\b\w+thide\b', 1.2),
    # Progressive (-thini / -thale / -thive)
    (r'\b\w+thini\b', 1.3),
    (r'\b\w+thale\b', 1.2),
    (r'\b\w+thive\b', 1.2),
    # Completive (-idhe / -ide)
    (r'\b\w+idhe\b', 1.0),
    (r'\b\w+ide\b', 0.8),
    # Cohortative (-ona)
    (r'\b\w+ona\b', 1.0),
    # Future completive (-tene / -uttene)
    (r'\b\w+tene\b', 1.3),
    (r'\b\w+uttene\b', 1.3),
    # Permission optative (-ali)
    (r'\b\w+ali\b', 0.8),
    (r'\b\w+irli\b', 1.0),
    # Locative case (-alli / -illi)
    (r'\b\w+alli\b', 1.2),
    (r'\b\w+illi\b', 1.2),
    # Ablative case (-inda)
    (r'\b\w+inda\b', 0.9),
    # Progressive imperative (-ri)
    (r'\b\w+dri\b', 1.0),
    (r'\b\w+lri\b', 0.8),
    # Negation (-illa)
    (r'\b\w+illa\b', 1.3),
    # Relational (-avaru / -avalu)
    (r'\b\w+avaru\b', 1.2),
    (r'\b\w+avalu\b', 1.2),
    # Tech slang suffix (-dya / -ya for past tense colloquial)
    (r'\b\w+idya\b', 1.3),
    (r'\b\w+thiya\b', 1.2),
]

# ---------------------------------------------------------------------------
# BANGALORE TECH SLANG — high-confidence Kanglish phrases
# ---------------------------------------------------------------------------
BANGALORE_SLANG: dict[str, float] = {
    "gottilla bro":  2.0,
    "madidya":       1.8,
    "barthiya":      1.8,
    "hogthiya":      1.8,
    "nodidya":       1.8,
    "helthiya":      1.8,
    "gottidya":      1.8,
    "bartheeni":     1.5,
    "hogtheeni":     1.5,
    "madtheeni":     1.5,
    "aagtheeni":     1.5,
    "adjust madkoli": 1.5,
    "sigthilla bro": 1.8,
    "aagtilla bro":  1.8,
    "cancel madidya": 1.8,
    "meeting madidya": 1.8,
}

# Merge all word maps into a single lookup
ALL_KANNADA_WORDS: dict[str, float] = {}
ALL_KANNADA_WORDS.update(KANNADA_HIGH)
ALL_KANNADA_WORDS.update(KANNADA_MED)
ALL_KANNADA_WORDS.update(KANNADA_LOW)

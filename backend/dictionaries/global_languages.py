"""
backend/dictionaries/global_languages.py

Vocabulary dictionaries for global (non-Indian) languages supported by Voxa AI.
Includes anti-Kannada/anti-Indian exclusion lists for Portuguese and Italian
to prevent European false-positives on romanized Indian text.

Languages: Spanish, French, German, Portuguese, Italian
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# SPANISH — 300+ words (including diacritics-stripped variants)
# ---------------------------------------------------------------------------
SPANISH_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Greetings / social
    "hola", "adios", "hasta", "luego", "buenos", "dias",
    "buenas", "tardes", "noches", "bienvenido", "gracias",
    "por", "favor", "de", "nada", "mucho", "gusto",
    "como", "estas", "como-estas", "bien", "mal",
    "soy", "estoy", "eres", "esta", "somos", "estamos",
    # Question words (diacritics stripped)
    "que", "quien", "cuando", "donde", "como",
    "cuanto", "cual", "cuales", "por-que", "para-que",
    # Pronouns
    "yo", "tu", "el", "ella", "nosotros", "nosotras",
    "vosotros", "ellos", "ellas", "usted", "ustedes",
    "me", "te", "se", "nos",
    "mi", "tu", "su", "nuestro", "nuestra",
    # Core verbs
    "ser", "estar", "tener", "hacer", "decir", "ir",
    "ver", "dar", "saber", "poder", "querer", "llegar",
    "hablar", "comer", "vivir", "trabajar", "buscar",
    "poner", "volver", "salir", "creer", "llevar",
    "esperar", "seguir", "conocer", "sentir", "pensar",
    "dejar", "parecer", "llamar", "encontrar",
    # Conjugated forms
    "tengo", "tienes", "tiene", "tenemos", "tienen",
    "hago", "haces", "hace", "hacemos", "hacen",
    "quiero", "quieres", "puede", "puedo",
    "voy", "vas", "va", "vamos", "van",
    "sé", "sabes", "se", "sabemos", "saben",
    # Negation / affirmation
    "no", "si", "tampoco", "nunca", "siempre",
    "tambien", "ya", "todavia", "aun",
    # Articles / determiners
    "el", "la", "los", "las", "un", "una",
    "unos", "unas", "este", "esta", "estos", "estas",
    "ese", "esa", "esos", "esas", "aquel",
    # Prepositions
    "de", "en", "con", "sin", "para", "por", "sobre",
    "entre", "hacia", "desde", "hasta", "ante",
    # Adjectives
    "bueno", "buena", "malo", "mala", "grande", "pequeno",
    "bonito", "bonita", "feo", "fea", "rapido", "lento",
    "mucho", "poco", "todo", "nada", "algo",
    # Common Spanish-only words
    "porque", "aunque", "mientras", "cuando", "donde",
    "aqui", "alli", "ahora", "hoy", "manana", "ayer",
    "noche", "dia", "semana", "mes", "ano",
    "trabajo", "casa", "coche", "amigo", "familia",
    "dinero", "tiempo", "gente", "ciudad", "pais",
    # Colloquisaml / informal
    "oye", "mira", "venga", "vale", "tio", "tia",
    "que-tal", "que-pasa", "fenomenal",
]}

# High-weight uniquely Spanish markers
SPANISH_HIGH: dict[str, float] = {
    "hola": 1.6, "gracias": 1.5, "como-estas": 1.8,
    "buenos-dias": 1.7, "estoy": 1.5, "tengo": 1.5,
    "porque": 1.4, "tambien": 1.4, "manana": 1.5,
    "quiero": 1.5, "puedo": 1.5, "nosotros": 1.5,
    "trabajar": 1.4, "hablar": 1.4, "bienvenido": 1.5,
}

# ---------------------------------------------------------------------------
# FRENCH — 250+ words
# ---------------------------------------------------------------------------
FRENCH_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Greetings
    "bonjour", "bonsoir", "bonne", "nuit", "merci", "beaucoup",
    "salut", "au-revoir", "coucou", "allô", "bienvenue",
    "comment", "allez", "vous", "bien", "mal",
    # Question words
    "qui", "que", "quoi", "quand", "ou", "combien", "pourquoi",
    "comment", "lequel", "laquelle",
    # Pronouns
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "me", "te", "se", "lui", "leur",
    "mon", "ton", "son", "notre", "votre", "leur",
    # Core verbs
    "etre", "avoir", "faire", "dire", "aller", "voir",
    "pouvoir", "vouloir", "venir", "devoir", "prendre",
    "savoir", "mettre", "trouver", "donner", "parler",
    "croire", "comprendre", "laisser", "demander",
    # Conjugated forms
    "est", "sont", "ai", "as", "avons", "avez", "ont",
    "suis", "sommes", "etes", "vais", "vas", "allons",
    "peux", "peut", "veux", "veut",
    "fais", "fait", "faites", "ferons",
    # Negation / affirmation
    "ne", "pas", "non", "oui", "jamais", "rien",
    "toujours", "encore", "deja", "maintenant",
    # Articles
    "le", "la", "les", "un", "une", "des",
    "ce", "cette", "ces", "mon", "ma", "mes",
    # Prepositions
    "de", "en", "avec", "sans", "pour", "sur", "sous",
    "entre", "chez", "vers", "depuis", "jusque",
    # Common words
    "maison", "voiture", "ami", "famille", "travail",
    "argent", "temps", "ville", "pays", "gens",
    "aujourd", "hui", "demain", "hier", "semaine",
    "mois", "annee", "jour", "nuit", "soir", "matin",
    "tres", "plus", "moins", "aussi", "trop", "bien",
    # Colloquial
    "super", "cool", "sympa", "bof", "quoi",
    "genre", "enfin", "voila", "alors",
]}

# High-weight uniquely French markers
FRENCH_HIGH: dict[str, float] = {
    "bonjour": 1.7, "merci": 1.5, "pourquoi": 1.5,
    "maintenant": 1.4, "beaucoup": 1.5, "toujours": 1.4,
    "aujourd": 1.6, "demain": 1.4, "voila": 1.5,
    "salut": 1.3, "bonsoir": 1.5,
}

# ---------------------------------------------------------------------------
# GERMAN — 200+ words
# ---------------------------------------------------------------------------
GERMAN_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Greetings
    "hallo", "guten", "morgen", "tag", "abend", "nacht",
    "danke", "schon", "bitte", "auf", "wiedersehen",
    "tschuss", "hei",
    # Question words
    "wie", "was", "wer", "wo", "wann", "warum", "welcher",
    "welche", "welches", "wohin", "woher", "wieviel",
    # Pronouns
    "ich", "du", "er", "sie", "wir", "ihr",
    "mich", "dich", "sich", "uns", "euch",
    "mein", "dein", "sein", "unser", "euer", "ihr",
    # Core verbs
    "sein", "haben", "werden", "konnen", "mussen",
    "sollen", "wollen", "durfen", "mogen",
    "machen", "sagen", "gehen", "sehen", "kommen",
    "wissen", "geben", "nehmen", "finden", "glauben",
    "halten", "denken", "heissen", "fragen", "zeigen",
    # Conjugated forms
    "ist", "sind", "war", "waren", "bin", "bist",
    "habe", "hat", "haben", "hatte", "hatten",
    "kann", "konnen", "muss", "mussen",
    "will", "wollen", "soll",
    "gehe", "geht", "gehen", "komme", "kommt",
    # Negation / affirmation
    "nicht", "nein", "ja", "kein", "keine",
    "niemals", "immer", "schon", "noch", "auch",
    # Articles / determiners
    "der", "die", "das", "ein", "eine", "einen",
    "dem", "den", "eines", "dieser", "dieses",
    # Prepositions
    "in", "an", "auf", "mit", "von", "zu",
    "bei", "aus", "nach", "vor", "uber",
    "unter", "zwischen", "durch", "fur",
    # Common words
    "haus", "auto", "freund", "familie", "arbeit",
    "geld", "zeit", "stadt", "land", "leute",
    "heute", "morgen", "gestern", "woche", "monat",
    "sehr", "mehr", "weniger", "auch", "nur",
    # Colloquial
    "krass", "geil", "echt", "alles", "klar", "alles-klar",
]}

# High-weight uniquely German markers
GERMAN_HIGH: dict[str, float] = {
    "hallo": 1.4, "danke": 1.5, "bitte": 1.4,
    "verstehen": 1.5, "wiedersehen": 1.7, "tschuss": 1.7,
    "konnen": 1.5, "mussen": 1.5, "heissen": 1.6,
    "ist-das": 1.5, "nicht": 1.3,
}

# ---------------------------------------------------------------------------
# PORTUGUESE — 200+ words
# IMPORTANT: Contains exclusion list for Kannada lookalikes
# ---------------------------------------------------------------------------
PORTUGUESE_WORDS: dict[str, float] = {w: 1.0 for w in [
    # Greetings
    "ola", "oi", "bom", "dia", "tarde", "noite",
    "obrigado", "obrigada", "de-nada", "por-favor",
    "tchau", "ate", "logo",
    # Question words
    "que", "quem", "quando", "onde", "como",
    "quanto", "qual", "quais", "porque", "para-que",
    # Pronouns
    "eu", "voce", "ele", "ela", "nos", "eles", "elas",
    "me", "te", "se",
    "meu", "minha", "seu", "sua", "nosso", "nossa",
    # Core verbs
    "ser", "estar", "ter", "fazer", "dizer", "ir",
    "ver", "dar", "saber", "poder", "querer",
    "falar", "comer", "morar", "trabalhar", "amar",
    # Conjugated forms
    "tenho", "tens", "tem", "temos", "tem",
    "faço", "faz", "fazemos", "fazem",
    "quero", "quer", "posso", "pode",
    "vou", "vai", "vamos", "vao",
    "estou", "esta", "estamos", "estao",
    "sei", "sabe", "sabemos", "sabem",
    # Negation / affirmation
    "nao", "sim", "nunca", "sempre", "tambem",
    "ja", "ainda", "mais", "menos",
    # Articles / determiners
    "o", "a", "os", "as", "um", "uma",
    "este", "esta", "estes", "estas",
    "esse", "essa", "isso", "aquele",
    # Prepositions
    "de", "em", "com", "sem", "para", "por",
    "sobre", "entre", "desde", "ate",
    # Common words
    "casa", "carro", "amigo", "familia", "trabalho",
    "dinheiro", "tempo", "cidade", "pais", "gente",
    "hoje", "amanha", "ontem", "semana", "mes",
    "muito", "pouco", "tudo", "nada", "algo",
    # Colloquial (Brazilian)
    "cara", "gente", "legal", "bacana", "saudade",
    "tudo-bem", "beleza", "show",
]}

# Words that look like Kannada but are Portuguese — used for anti-Kannada penalty
# These are Portuguese words that langid/langdetect might confuse with Kannada.
# When these appear WITH other Portuguese markers, we penalize Kannada score.
PORTUGUESE_KANNADA_EXCLUSIONS: set[str] = {
    # Portuguese words that happen to look like Kannada patterns
    "ola",  # could overlap with romanized Indian
    "ela",  # could look like Telugu
}

# High-weight uniquely Portuguese markers
PORTUGUESE_HIGH: dict[str, float] = {
    "obrigado": 1.7, "obrigada": 1.7, "saudade": 1.8,
    "tudo-bem": 1.7, "estou": 1.5, "voce": 1.5,
    "porque": 1.3, "tambem": 1.3, "nao": 1.4,
    "ola": 1.2, "tchau": 1.6,
}

# ---------------------------------------------------------------------------
# ITALIAN — for false-positive protection only
# (not a primary detection target but helps prevent misclassification)
# ---------------------------------------------------------------------------
ITALIAN_WORDS: dict[str, float] = {w: 1.0 for w in [
    "ciao", "come", "stai", "oggi", "bene", "grazie",
    "prego", "per", "favore", "buongiorno", "buonasera",
    "si", "no", "io", "tu", "lui", "lei", "noi", "voi",
    "essere", "avere", "fare", "dire", "potere",
    "volere", "sapere", "stare", "dovere", "vedere",
    "andare", "venire", "dare",
]}

# High-weight Italian markers
ITALIAN_HIGH: dict[str, float] = {
    "ciao": 1.6, "prego": 1.6, "buongiorno": 1.7,
    "buonasera": 1.7, "grazie": 1.5,
}

# ---------------------------------------------------------------------------
# ENGLISH — comprehensive list for code-switching detection
# (intentionally excludes ambiguous short words like 'in', 'on', 'a', 'an')
# ---------------------------------------------------------------------------
ENGLISH_WORDS: dict[str, float] = {w: 0.8 for w in [
    # High-frequency unambiguous English words
    "the", "is", "are", "was", "were", "have", "has", "had",
    "this", "that", "these", "those", "which", "what", "when",
    "where", "who", "how", "why",
    "please", "help", "thank", "thanks", "hello", "hey", "hi",
    "can", "you", "your", "will", "would", "should", "could",
    "with", "from", "they", "been", "for", "and", "not", "but",
    "she", "he", "we", "my", "our", "their", "its",
    "me", "them", "him", "her", "us",
    "his", "did", "do", "does",
    "english", "reply", "say", "talk", "speak", "voice",
    "want", "need", "like", "come", "know", "think",
    "also", "very", "much", "some",
    "just", "good", "nice", "okay", "ok", "yes", "so", "now",
    "let", "get", "got", "put", "set", "see", "try", "ask",
    "tell", "make", "use", "go", "up", "out",
    "wow", "cancel", "super", "office",
    # Common English discourse
    "bro", "dude", "man", "guys", "literally", "actually",
    "basically", "totally", "honestly", "obviously",
    "yeah", "yep", "nope", "sure", "cool", "great",
    "awesome", "amazing", "perfect", "exactly",
    "right", "wrong", "correct", "incorrect",
    "maybe", "probably", "definitely", "absolutely",
    "because", "although", "however", "therefore",
    "about", "after", "before", "between", "during",
    "through", "without", "within", "around",
]}

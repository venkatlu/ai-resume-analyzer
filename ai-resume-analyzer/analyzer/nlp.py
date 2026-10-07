"""Text extraction + lightweight NLP helpers (no model downloads needed)."""
import re
from collections import Counter

from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .skills import SKILL_ALIASES

ALL_SKILL_TERMS = {a for al in SKILL_ALIASES.values() for a in al}

STOPWORDS = set("""
a an the and or but if then else for to of in on at by with from as is are was were be been being it its this that these those
i you he she we they them our your their his her my me us not no yes do does did done have has had having will would can could
should may might must shall about above after again against all also am any because before below between both cannot down during
each few further here how into just more most other out over own same so some such than too very what when where which while who whom
why up under until off once only per via etc within across using use used able ability
""".split())

# Words common in every job post that carry no signal for matching
GENERIC = set("""
experience work working team teams skills skill strong required requirements preferred candidate candidates role job jobs
responsibilities responsibility years year looking join company position opportunity ideal excellent good knowledge understanding
including include includes related relevant plus bonus etc will need needs must well new build building help ensure
degree bachelor bachelors master masters equivalent employer equal duties qualifications qualification apply
write entry level remote maintain maintains develop develops design designs applications application services service queries
clearly independently production issues issue based based on-site hybrid full-time part-time fresher freshers salary benefits
collaborate collaborative communicate communication solve solving deliver delivering support supporting perform performing
seeking hiring responsible providing provide required plus preferred
""".split())

SECTION_PATTERNS = {
    "summary": r"\b(summary|objective|profile|about me)\b",
    "education": r"\b(education|academic|qualification)s?\b",
    "experience": r"\b(experience|internship|employment|work history)s?\b",
    "skills": r"\b(skills|technical skills|technologies|tech stack)\b",
    "projects": r"\b(projects?|academic projects?)\b",
    "certifications": r"\b(certifications?|certificates?|courses|licenses?)\b",
}

ACTION_VERBS = set("""
developed built designed implemented created led managed improved optimized deployed engineered automated analyzed integrated
launched delivered architected collaborated reduced increased achieved streamlined established maintained tested migrated
configured trained researched published presented coordinated
""".split())


def extract_text_from_pdf(path):
    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def extract_text_from_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.read()


def clean_text(text):
    text = text.replace("\u2022", " ").replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def tokenize(text):
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-/]*", text.lower())
    return [t.strip(".-/") for t in tokens if t.strip(".-/")]


def _skill_pattern(alias):
    return r"(?<![a-z0-9+#])" + re.escape(alias) + r"(?![a-z0-9+#])"


def extract_skills(text):
    """Return the set of canonical skills whose alias appears in the text."""
    low = text.lower()
    found = set()
    for canonical, aliases in SKILL_ALIASES.items():
        if any(re.search(_skill_pattern(a), low) for a in aliases):
            found.add(canonical)
    return found


def extract_keywords(text, top_n=25):
    """Frequency-ranked unigrams + bigrams (stop words / boilerplate removed)."""
    tokens = tokenize(text)
    good = [t for t in tokens if t not in STOPWORDS and t not in GENERIC and t not in ALL_SKILL_TERMS
            and len(t) > 2 and not t.isdigit()]
    counts = Counter(good)
    bigrams = Counter()
    for a, b in zip(tokens, tokens[1:]):
        if all(w not in STOPWORDS and w not in GENERIC and w not in ALL_SKILL_TERMS and len(w) > 2 for w in (a, b)):
            bigrams[f"{a} {b}"] += 1
    ranked = Counter()
    for w, c in counts.items():
        ranked[w] = c
    for bg, c in bigrams.items():
        if c >= 2:  # only keep recurring phrases
            ranked[bg] = c * 1.5
    return [w for w, _ in ranked.most_common(top_n)]


def keyword_in_text(keyword, text_low):
    return re.search(_skill_pattern(keyword), text_low) is not None


def tfidf_similarity(a, b):
    try:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        m = vec.fit_transform([a, b])
        return float(cosine_similarity(m[0], m[1])[0][0])
    except ValueError:
        return 0.0


def detect_sections(text):
    low = text.lower()
    found = {}
    for name, pat in SECTION_PATTERNS.items():
        # a heading = pattern on its own short line
        hit = False
        for line in low.splitlines():
            line = line.strip()
            if 0 < len(line) <= 40 and re.search(pat, line):
                hit = True
                break
        found[name] = hit
    return found


def contact_info(text):
    return {
        "email": bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)),
        "phone": bool(re.search(r"(\+?\d[\d\s\-()]{8,}\d)", text)),
        "linkedin": "linkedin.com" in text.lower(),
        "github": "github.com" in text.lower(),
    }


def action_verb_count(text):
    return sum(1 for t in tokenize(text) if t in ACTION_VERBS)


def quantified_count(text):
    return len(re.findall(r"\b\d+(?:\.\d+)?\s?(?:%|\+|x|k|m)\b|\b\d{2,}\b", text.lower()))

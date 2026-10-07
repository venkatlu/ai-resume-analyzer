"""Ties the NLP helpers + scorer together into one analysis result."""
from . import nlp
from .scorer import FEATURES, predict_score
from .skills import SOFT_SKILLS


def _ratio(a, b):
    return len(a) / len(b) if b else 0.0


def analyze(resume_text, jd_text):
    resume_text = nlp.clean_text(resume_text)
    jd_text = nlp.clean_text(jd_text)
    r_low, j_low = resume_text.lower(), jd_text.lower()

    # --- skills -----------------------------------------------------------
    r_skills = nlp.extract_skills(resume_text)
    j_skills = nlp.extract_skills(jd_text)
    matched = sorted(j_skills & r_skills)
    missing = sorted(j_skills - r_skills)
    extra = sorted(r_skills - j_skills)

    # --- keywords ---------------------------------------------------------
    j_keywords = nlp.extract_keywords(jd_text, top_n=25)
    kw_matched = [k for k in j_keywords if nlp.keyword_in_text(k, r_low)]
    kw_missing = [k for k in j_keywords if k not in kw_matched]

    # --- structure / quality ---------------------------------------------
    sections = nlp.detect_sections(resume_text)
    contact = nlp.contact_info(resume_text)
    words = len(nlp.tokenize(resume_text))
    verbs = nlp.action_verb_count(resume_text)
    quant = nlp.quantified_count(resume_text)
    sim = nlp.tfidf_similarity(resume_text, jd_text)

    core = ["education", "experience", "skills", "projects"]
    section_score = (sum(sections[s] for s in core) + 0.5 * sections["summary"]
                     + 0.5 * sections["certifications"]) / 5.0
    contact_score = (contact["email"] + contact["phone"]
                     + 0.5 * contact["linkedin"] + 0.5 * contact["github"]) / 3.0
    impact = min(1.0, verbs / 8.0) * 0.6 + min(1.0, quant / 6.0) * 0.4
    if words < 250:
        length_q = words / 250
    elif words > 1000:
        length_q = max(0.4, 1 - (words - 1000) / 1500)
    else:
        length_q = 1.0

    skill_ratio = _ratio(set(matched), j_skills) if j_skills else _ratio(set(kw_matched), set(j_keywords))
    kw_ratio = _ratio(set(kw_matched), set(j_keywords))

    features = [skill_ratio, kw_ratio, min(1.0, sim / 0.5), min(1.0, section_score),
                min(1.0, contact_score), impact, length_q]
    score, engine = predict_score(features)

    label = ("Excellent" if score >= 80 else "Good" if score >= 65
             else "Fair" if score >= 50 else "Needs Work")

    result = {
        "ats_score": score,
        "label": label,
        "engine": engine,
        "features": {n: round(float(v) * 100, 1) for n, v in zip(FEATURES, features)},
        "matched_skills": matched,
        "missing_skills": missing,
        "extra_skills": extra[:15],
        "keywords_matched": kw_matched,
        "keywords_missing": kw_missing,
        "sections": sections,
        "contact": contact,
        "stats": {"words": words, "action_verbs": verbs, "quantified_results": quant,
                  "similarity_pct": round(sim * 100, 1),
                  "jd_skills": len(j_skills), "resume_skills": len(r_skills)},
    }
    result["suggestions"] = build_suggestions(result)
    return result


def build_suggestions(res):
    tips = []
    hard_missing = [s for s in res["missing_skills"] if s not in SOFT_SKILLS]
    if hard_missing:
        top = ", ".join(hard_missing[:8])
        tips.append(f"Add these job-required skills where you genuinely have them (Skills section and project bullets): {top}.")
    soft_missing = [s for s in res["missing_skills"] if s in SOFT_SKILLS]
    if soft_missing:
        tips.append("Show soft skills through results, not lists: " + ", ".join(soft_missing) + ".")
    if res["keywords_missing"]:
        tips.append("Mirror recruiter language. Work these phrases into your summary/bullets if accurate: "
                    + ", ".join(res["keywords_missing"][:8]) + ".")
    missing_secs = [s.title() for s in ("summary", "education", "experience", "skills", "projects", "certifications")
                    if not res["sections"].get(s)]
    if missing_secs:
        tips.append("Add clearly labelled section headings ATS parsers look for: " + ", ".join(missing_secs) + ".")
    c = res["contact"]
    if not c["email"] or not c["phone"]:
        tips.append("Put a professional email and phone number at the top of the resume in plain text.")
    if not c["linkedin"] or not c["github"]:
        tips.append("Include LinkedIn and GitHub links; recruiters for developer roles check them.")
    st = res["stats"]
    if st["action_verbs"] < 6:
        tips.append("Start bullets with strong action verbs (Developed, Implemented, Designed, Optimized, Deployed).")
    if st["quantified_results"] < 4:
        tips.append("Quantify impact (e.g. 'reduced load time by 30%', 'served 500+ users', 'improved accuracy to 92%').")
    if st["words"] < 250:
        tips.append("Your resume is very short. Expand projects and internships with 2-3 concise bullets each.")
    elif st["words"] > 1000:
        tips.append("Your resume is long. Trim it to 1 page (fresher) or 2 pages maximum.")
    if res["stats"]["similarity_pct"] < 25:
        tips.append("Overall wording is far from the job description. Tailor the resume separately for each application.")
    if not tips:
        tips.append("Great match! Keep the resume in a simple single-column PDF layout and proofread once more.")
    return tips

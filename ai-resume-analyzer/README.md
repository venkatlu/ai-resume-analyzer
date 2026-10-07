# AI Resume Analyzer

Flask web app that scores a resume against a job description (ATS compatibility), extracts skills and
keywords with NLP, shows the skill gap and gives improvement tips. Includes login, MySQL storage,
REST APIs and a history dashboard.

**Stack:** Python, Flask, TensorFlow/Keras, NLP (scikit-learn TF-IDF + regex skill taxonomy), MySQL (SQLAlchemy),
HTML5, CSS3, JavaScript, REST APIs, Git.

## Project structure
```
ai-resume-analyzer/
├── app.py                 # Flask app, routes, REST API
├── config.py              # settings (.env)
├── models.py              # User, Resume, JobDescription, Analysis tables
├── train_model.py         # optional: retrain the TensorFlow scorer
├── schema.sql             # optional manual MySQL schema
├── requirements.txt
├── .env.example
├── analyzer/
│   ├── skills.py          # skill taxonomy (200+ skills + aliases)
│   ├── nlp.py             # PDF text, keywords, sections, TF-IDF similarity
│   ├── scorer.py          # TensorFlow neural ATS scorer (+ rule fallback)
│   └── engine.py          # combines everything, builds suggestions
├── templates/  static/  uploads/  samples/  models/
```

## Run in VS Code (Windows / macOS / Linux)

1. Install **Python 3.10 - 3.12** (TensorFlow does not support 3.13 yet) and VS Code with the *Python* extension.
2. `File > Open Folder...` and choose `ai-resume-analyzer`. Open the terminal (`Ctrl + ~`).
3. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows
   source venv/bin/activate       # macOS / Linux
   ```
   In VS Code: `Ctrl+Shift+P` > *Python: Select Interpreter* > pick the `venv` one.
4. Install packages (TensorFlow is large, ~500 MB):
   ```bash
   pip install -r requirements.txt
   ```
5. Configure the database. Copy `.env.example` to `.env`, then edit:
   * **MySQL:** set `DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/resume_analyzer`
     (MySQL server must be running; the app creates the database and tables itself).
   * **No MySQL yet?** use `DATABASE_URL=sqlite:///resume_analyzer.db` and switch later.
6. Start the app:
   ```bash
   python app.py
   ```
7. Open **http://127.0.0.1:5000**, sign up, click *New Analysis*, upload `samples/sample_resume.pdf`
   and paste / upload `samples/job_description_python_developer.txt`.

The first analysis takes ~10-15 s: TensorFlow loads and trains the small scoring model once, then saves it to `models/ats_model.keras`.

## Expected output (sample resume vs sample job description)
* **ATS score:** roughly 55 / 100, label *Fair* (the sample resume is short on purpose)
* **Matched skills:** python, flask, mysql, mongodb, react, javascript, html, css, git, github, rest api, pandas, linux
* **Missing skills:** django, docker, aws, azure, ci/cd, sql, pytest, tensorflow, scikit-learn, machine learning, nlp, oop, algorithms, data structures, agile
* **Breakdown bars:** skill match, keyword match, similarity, sections, contact info, impact language, length
* **Recommendations:** add missing skills you genuinely have, expand thin sections, tailor wording to the job post
* Dashboard shows total analyses, average/best score, a trend chart and history with View / Delete.

## REST API (login session cookie required)
| Method | URL | Description |
|---|---|---|
| POST | `/api/analyze` | multipart form: `resume` (PDF), `jd_text` or `jd_file`, `job_title` -> JSON result |
| GET | `/api/history` | list of your analyses |
| GET | `/api/analysis/<id>` | full result JSON |
| GET | `/report/<id>.txt` | downloadable text report |

## How the score works
1. Extract text from the PDF (pypdf) and clean it.
2. NLP: match a 200+ skill taxonomy, rank job-description keywords, TF-IDF cosine similarity, detect section headings, contact info, action verbs and quantified results.
3. Seven features (0-1) go into a Keras network (32-16-1, sigmoid) that outputs the 0-100 score.
   The network is trained on synthetic data generated from a transparent weighted rule, so treat the score as a
   guide, not an official ATS result. To improve it, replace `_synthetic_data()` in `analyzer/scorer.py` with real labelled resumes.
4. Rule-based tips are generated from the gaps.

## Troubleshooting
* `Could not connect to MySQL` : start the MySQL service, check user/password in `.env`, or use SQLite.
* `No module named ...` : the venv is not active or step 4 was skipped.
* TensorFlow install fails : use Python 3.10-3.12, or ignore it: the app falls back to the weighted rule automatically.
* "Very little text was found" : the PDF is a scanned image; export a text-based PDF from Word/Google Docs.
* Accented MySQL 8 auth error (`cryptography` required) : already in requirements.txt.

## Git
```bash
git init && git add . && git commit -m "AI Resume Analyzer"
```

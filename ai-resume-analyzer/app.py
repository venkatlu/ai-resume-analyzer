import os
import re
import uuid

from flask import (Flask, Response, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from werkzeug.utils import secure_filename

from analyzer import nlp
from analyzer.engine import analyze
from config import Config
from models import Analysis, JobDescription, Resume, User, db

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "info"


def ensure_mysql_database(uri):
    """Create the MySQL database if it does not exist yet."""
    url = make_url(uri)
    if not url.drivername.startswith("mysql"):
        return
    db_name = url.database
    server_url = url.set(database=None)
    engine = create_engine(server_url)
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4"))
        conn.commit()
    engine.dispose()


def allowed(filename, exts):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in exts


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    try:
        ensure_mysql_database(app.config["SQLALCHEMY_DATABASE_URI"])
    except Exception as exc:
        print("\n[!] Could not connect to MySQL:", exc)
        print("[!] Check DATABASE_URL in .env (or switch to sqlite:///resume_analyzer.db)\n")
        raise

    db.init_app(app)
    login_manager.init_app(app)
    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ------------------------------------------------------------------ helpers
    def run_analysis(resume_file, jd_text, jd_file, job_title):
        """Shared by the web form and the REST API. Returns (Analysis, error)."""
        if not resume_file or resume_file.filename == "":
            return None, "Please upload your resume as a PDF."
        if not allowed(resume_file.filename, app.config["ALLOWED_RESUME_EXT"]):
            return None, "Resume must be a PDF file."

        safe = secure_filename(resume_file.filename)
        stored = f"{uuid.uuid4().hex}_{safe}"
        path = os.path.join(app.config["UPLOAD_FOLDER"], stored)
        resume_file.save(path)
        try:
            resume_text = nlp.extract_text_from_pdf(path)
        except Exception:
            os.remove(path)
            return None, "Could not read that PDF. Is it corrupted or password protected?"
        if len(resume_text.split()) < 50:
            os.remove(path)
            return None, "Very little text was found. Scanned/image PDFs are not supported - export a text PDF."

        jd = (jd_text or "").strip()
        if jd_file and jd_file.filename:
            if not allowed(jd_file.filename, app.config["ALLOWED_JD_EXT"]):
                return None, "Job description file must be PDF or TXT."
            jd_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{uuid.uuid4().hex}_{secure_filename(jd_file.filename)}")
            jd_file.save(jd_path)
            try:
                jd = (nlp.extract_text_from_pdf(jd_path) if jd_file.filename.lower().endswith(".pdf")
                      else nlp.extract_text_from_txt(jd_path))
            finally:
                os.remove(jd_path)
        if len(jd.split()) < 15:
            return None, "Please paste or upload a job description (at least a few sentences)."

        result = analyze(resume_text, jd)

        resume = Resume(user_id=current_user.id, filename=safe, stored_path=stored, text_content=resume_text)
        job = JobDescription(user_id=current_user.id, title=job_title or "Untitled role", text_content=jd)
        db.session.add_all([resume, job])
        db.session.flush()
        analysis = Analysis(user_id=current_user.id, resume_id=resume.id, job_id=job.id,
                            ats_score=result["ats_score"], result_json=result)
        db.session.add(analysis)
        db.session.commit()
        return analysis, None

    def own_analysis_or_404(analysis_id):
        a = db.session.get(Analysis, analysis_id)
        if a is None or a.user_id != current_user.id:
            from flask import abort
            abort(404)
        return a

    # ------------------------------------------------------------------- pages
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not name or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                flash("Enter your name and a valid email.", "error")
            elif len(password) < 6:
                flash("Password must be at least 6 characters.", "error")
            elif User.query.filter_by(email=email).first():
                flash("That email is already registered. Please log in.", "error")
            else:
                user = User(name=name, email=email)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                login_user(user)
                flash("Welcome! Your account is ready.", "success")
                return redirect(url_for("dashboard"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(request.form.get("password", "")):
                login_user(user)
                return redirect(request.args.get("next") or url_for("dashboard"))
            flash("Invalid email or password.", "error")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out.", "info")
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        items = (Analysis.query.filter_by(user_id=current_user.id)
                 .order_by(Analysis.created_at.desc()).all())
        scores = [a.ats_score for a in items]
        stats = {"count": len(items),
                 "avg": round(sum(scores) / len(scores), 1) if scores else 0,
                 "best": max(scores) if scores else 0}
        chart = [{"label": a.created_at.strftime("%d %b"), "score": a.ats_score} for a in reversed(items[:10])]
        return render_template("dashboard.html", items=items, stats=stats, chart=chart)

    @app.route("/analyze", methods=["GET", "POST"])
    @login_required
    def analyze_page():
        if request.method == "POST":
            analysis, err = run_analysis(request.files.get("resume"), request.form.get("jd_text"),
                                         request.files.get("jd_file"), request.form.get("job_title", "").strip())
            if err:
                flash(err, "error")
            else:
                return redirect(url_for("result", analysis_id=analysis.id))
        return render_template("analyze.html")

    @app.route("/result/<int:analysis_id>")
    @login_required
    def result(analysis_id):
        a = own_analysis_or_404(analysis_id)
        return render_template("result.html", a=a, r=a.result_json)

    @app.route("/delete/<int:analysis_id>", methods=["POST"])
    @login_required
    def delete(analysis_id):
        a = own_analysis_or_404(analysis_id)
        resume, job = a.resume, a.job
        path = os.path.join(app.config["UPLOAD_FOLDER"], resume.stored_path)
        db.session.delete(a)
        db.session.delete(resume)
        db.session.delete(job)
        db.session.commit()
        if os.path.exists(path):
            os.remove(path)
        flash("Analysis deleted.", "info")
        return redirect(url_for("dashboard"))

    @app.route("/report/<int:analysis_id>.txt")
    @login_required
    def report(analysis_id):
        a = own_analysis_or_404(analysis_id)
        r = a.result_json
        lines = [f"AI RESUME ANALYZER REPORT", f"Role: {a.job.title}", f"Resume: {a.resume.filename}",
                 f"Date: {a.created_at:%Y-%m-%d %H:%M}", "", f"ATS SCORE: {r['ats_score']}/100 ({r['label']})", "",
                 "MATCHED SKILLS: " + (", ".join(r["matched_skills"]) or "-"),
                 "MISSING SKILLS: " + (", ".join(r["missing_skills"]) or "-"), "",
                 "MISSING KEYWORDS: " + (", ".join(r["keywords_missing"]) or "-"), "", "RECOMMENDATIONS:"]
        lines += [f"{i}. {t}" for i, t in enumerate(r["suggestions"], 1)]
        return Response("\n".join(lines), mimetype="text/plain",
                        headers={"Content-Disposition": f"attachment; filename=resume_report_{a.id}.txt"})

    # --------------------------------------------------------------- REST API
    @app.route("/api/analyze", methods=["POST"])
    @login_required
    def api_analyze():
        analysis, err = run_analysis(request.files.get("resume"), request.form.get("jd_text"),
                                     request.files.get("jd_file"), request.form.get("job_title", ""))
        if err:
            return jsonify({"error": err}), 400
        return jsonify({"id": analysis.id, **analysis.result_json}), 201

    @app.route("/api/history")
    @login_required
    def api_history():
        items = (Analysis.query.filter_by(user_id=current_user.id)
                 .order_by(Analysis.created_at.desc()).all())
        return jsonify([{"id": a.id, "job_title": a.job.title, "resume": a.resume.filename,
                         "ats_score": a.ats_score, "created_at": a.created_at.isoformat()} for a in items])

    @app.route("/api/analysis/<int:analysis_id>")
    @login_required
    def api_analysis(analysis_id):
        a = own_analysis_or_404(analysis_id)
        return jsonify({"id": a.id, "job_title": a.job.title, **a.result_json})

    @app.errorhandler(413)
    def too_large(_):
        flash("File too large (max 5 MB).", "error")
        return redirect(url_for("analyze_page"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

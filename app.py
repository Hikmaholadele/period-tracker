from flask import Flask, render_template, session, redirect, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

DB_PATH = os.environ.get("DATABASE", "periods.db")
FLOW_LEVELS = ["spotting", "light", "medium", "heavy"]
SYMPTOMS = [
    "cramps",
    "headache",
    "acne",
    "fatigue",
    "mood swings",
    "bloating",
    "tender breasts",
    "backache",
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date TEXT NOT NULL,
            end_date TEXT,
            flow TEXT NOT NULL,
            symptoms TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        )
        """
    )
    db.commit()


def get_periods():
    rows = get_db().execute(
        "SELECT * FROM periods ORDER BY start_date DESC, id DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def get_insights():
    periods = get_periods()
    starts = sorted(date.fromisoformat(p["start_date"]) for p in periods)

    cycle_lengths = [
        (later - earlier).days for earlier, later in zip(starts, starts[1:])
    ][-6:]

    period_lengths = [
        (
            date.fromisoformat(p["end_date"]) - date.fromisoformat(p["start_date"])
        ).days
        + 1
        for p in periods
        if p["end_date"]
    ][-6:]

    avg_cycle = round(mean(cycle_lengths)) if cycle_lengths else 28
    avg_period = round(mean(period_lengths)) if period_lengths else 5
    next_start = starts[-1] + timedelta(days=avg_cycle) if starts else None

    return {
        "avg_cycle": avg_cycle,
        "avg_period": avg_period,
        "cycles_logged": len(cycle_lengths),
        "last_start": starts[-1] if starts else None,
        "next_start": next_start,
    }


@app.route("/")
def home():
    return render_template(
        "index.html", periods=get_periods(), insights=get_insights()
    )


@app.route("/log-period", methods=["GET", "POST"])
def log_period():
    if request.method == "POST":
        start = request.form.get("start_date", "").strip()
        end = request.form.get("end_date", "").strip()
        flow = request.form.get("flow", "").strip()
        symptoms = request.form.getlist("symptoms")
        notes = request.form.get("notes", "").strip()
        if not start:
            flash("Start date is required.", "error")
        else:
            valid = True
            try:
                start_date = date.fromisoformat(start)
                end_date = date.fromisoformat(end) if end else None
            except ValueError:
                valid = False
                flash("Dates must be in YYYY-MM-DD format.", "error")

            if valid and end_date and end_date < start_date:
                valid = False
                flash("End date cannot be before the start date.", "error")
            if valid and flow not in FLOW_LEVELS:
                valid = False
                flash("Pick a valid flow level.", "error")

            if valid:
                db = get_db()
                db.execute(
                    """
                    INSERT INTO periods (start_date, end_date, flow, symptoms, notes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        start_date.isoformat(),
                        end_date.isoformat() if end_date else "",
                        flow,
                        ", ".join(sorted(set(symptoms))),
                        notes,
                    ),
                )
                db.commit()
                flash("Period logged.", "success")
                return redirect(url_for("log_period"))

    return render_template(
        "log_period.html",
        symptoms=SYMPTOMS,
        flow_levels=FLOW_LEVELS,
        periods=get_periods(),
        insights=get_insights(),
    )


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/history")
def history():
    return render_template("history.html")

app.run(debug=True)

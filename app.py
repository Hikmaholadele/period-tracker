import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-secret-change-me",
)

app.config["DATABASE"] = os.environ.get(
    "DATABASE",
    "periods.db",
)


# ============================================================
# APPLICATION CONSTANTS
# ============================================================

FLOW_LEVELS = [
    "spotting",
    "light",
    "medium",
    "heavy",
]

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

DEFAULT_CYCLE_LENGTH = 28
DEFAULT_PERIOD_LENGTH = 5


# ============================================================
# DATABASE
# ============================================================

def get_db():
    """Return the current database connection."""

    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row

    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """Close the database connection after each request."""

    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    """Create the application database tables."""

    db = get_db()

    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE,
            flow TEXT NOT NULL,
            symptoms TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users (id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            average_cycle_length INTEGER DEFAULT 28,
            average_period_length INTEGER DEFAULT 5,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users (id)
                ON DELETE CASCADE
        );
        """
    )

    db.commit()


# ============================================================
# AUTHENTICATION HELPERS
# ============================================================

def login_required(view):
    """Require the user to be signed in."""

    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("signin"))

        return view(**kwargs)

    return wrapped_view


def get_current_user():
    """Return the currently signed-in user."""

    user_id = session.get("user_id")

    if user_id is None:
        return None

    return get_db().execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()


# ============================================================
# CYCLE CALCULATIONS
# ============================================================

def calculate_cycle_length(previous_period, current_period):
    """Calculate the number of days between two period starts."""

    if not previous_period or not current_period:
        return None

    previous_start = date.fromisoformat(previous_period["start_date"])
    current_start = date.fromisoformat(current_period["start_date"])

    return (current_start - previous_start).days


def calculate_average_cycle(periods):
    """Calculate the user's average cycle length."""

    if len(periods) < 2:
        return DEFAULT_CYCLE_LENGTH

    cycle_lengths = []

    for index in range(1, len(periods)):
        current = periods[index - 1]
        previous = periods[index]

        length = calculate_cycle_length(previous, current)

        if length and 15 <= length <= 60:
            cycle_lengths.append(length)

    if not cycle_lengths:
        return DEFAULT_CYCLE_LENGTH

    return round(sum(cycle_lengths) / len(cycle_lengths))


def calculate_period_length(period):
    """Calculate the duration of a period."""

    if not period or not period["end_date"]:
        return None

    start = date.fromisoformat(period["start_date"])
    end = date.fromisoformat(period["end_date"])

    return (end - start).days + 1


def calculate_average_period_length(periods):
    """Calculate the user's average period length."""

    lengths = []

    for period in periods:
        length = calculate_period_length(period)

        if length and 1 <= length <= 15:
            lengths.append(length)

    if not lengths:
        return DEFAULT_PERIOD_LENGTH

    return round(sum(lengths) / len(lengths))


def predict_next_period(last_period, average_cycle_length):
    """Predict the next period start date."""

    if not last_period:
        return None

    last_start = date.fromisoformat(last_period["start_date"])

    return last_start + timedelta(days=average_cycle_length)


def calculate_cycle_day(last_period):
    """Calculate the current cycle day."""

    if not last_period:
        return None

    start = date.fromisoformat(last_period["start_date"])

    return (date.today() - start).days + 1


# ============================================================
# PUBLIC ROUTES
# ============================================================

@app.route("/")
def landing():
    """Landing page."""

    return render_template("landing.html")


# ============================================================
# AUTHENTICATION ROUTES
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user."""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate name
        if not name:
            flash("Please enter your name.", "error")
            return render_template("register.html")

        # Validate email
        if not email:
            flash("Please enter your email address.", "error")
            return render_template("register.html")

        # Validate password
        if len(password) < 8:
            flash(
                "Password must be at least 8 characters.",
                "error",
            )
            return render_template("register.html")

        # Confirm password
        if password != confirm_password:
            flash(
                "Passwords do not match.",
                "error",
            )
            return render_template("register.html")

        db = get_db()

        # Check whether email already exists
        existing_user = db.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        if existing_user:
            flash(
                "An account with this email already exists.",
                "error",
            )
            return render_template("register.html")

        # Hash password before storing it
        password_hash = generate_password_hash(password)

        # Create user
        cursor = db.execute(
            """
            INSERT INTO users (
                name,
                email,
                password_hash
            )
            VALUES (?, ?, ?)
            """,
            (
                name,
                email,
                password_hash,
            ),
        )

        user_id = cursor.lastrowid

        # Create default user settings
        db.execute(
            """
            INSERT INTO user_settings (
                user_id,
                average_cycle_length,
                average_period_length
            )
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                DEFAULT_CYCLE_LENGTH,
                DEFAULT_PERIOD_LENGTH,
            ),
        )

        db.commit()

        # Log the user in
        session.clear()
        session["user_id"] = user_id

        flash(
            "Your account has been created successfully!",
            "success",
        )

        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    """Sign in an existing user."""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash(
                "Please enter your email and password.",
                "error",
            )
            return render_template("signin.html")

        db = get_db()

        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        if user is None:
            flash(
                "Incorrect email or password.",
                "error",
            )
            return render_template("signin.html")

        if not check_password_hash(
            user["password_hash"],
            password,
        ):
            flash(
                "Incorrect email or password.",
                "error",
            )
            return render_template("signin.html")

        # Authentication successful
        session.clear()
        session["user_id"] = user["id"]

        flash(
            f"Welcome back, {user['name']}!",
            "success",
        )

        return redirect(url_for("dashboard"))

    return render_template("signin.html")

@app.post("/logout")
@login_required
def logout():
    """Sign the current user out."""

    session.clear()

    return redirect(url_for("landing"))


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():
    """Display the user's cycle dashboard."""

    user = get_current_user()

    return render_template(
        "dashboard.html",
        user=user,
    )


# ============================================================
# PERIOD ROUTES
# ============================================================

@app.route("/log-period", methods=["GET", "POST"])
@login_required
def log_period():
    """Log a new period."""

    return render_template("log_period.html")


@app.route("/history")
@login_required
def history():
    """Display the user's period history."""

    return render_template("history.html")


# ============================================================
# APPLICATION STARTUP
# ============================================================

with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
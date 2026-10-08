import calendar
import os
import sqlite3
from datetime import date, timedelta
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


app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-secret-change-me",
)

app.config["DATABASE"] = os.environ.get(
    "DATABASE",
    "periods.db",
)


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


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def get_db():
    """Return the current database connection."""

    if "db" not in g:
        g.db = sqlite3.connect(
            app.config["DATABASE"]
        )

        g.db.row_factory = sqlite3.Row

        g.db.execute(
            "PRAGMA foreign_keys = ON"
        )

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


# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------

def login_required(view):
    """Require the user to be signed in."""

    @wraps(view)
    def wrapped_view(**kwargs):

        if "user_id" not in session:
            flash(
                "Please sign in to continue.",
                "error",
            )

            return redirect(
                url_for("signin")
            )

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


# ---------------------------------------------------------
# CYCLE CALCULATIONS
# ---------------------------------------------------------

def calculate_cycle_length(
    previous_period,
    current_period,
):
    """Calculate the number of days between two period starts."""

    if not previous_period or not current_period:
        return None

    previous_start = date.fromisoformat(
        previous_period["start_date"]
    )

    current_start = date.fromisoformat(
        current_period["start_date"]
    )

    return (
        current_start - previous_start
    ).days


def calculate_average_cycle(periods):
    """Calculate the user's average cycle length."""

    if len(periods) < 2:
        return DEFAULT_CYCLE_LENGTH

    cycle_lengths = []

    for index in range(1, len(periods)):

        current = periods[index - 1]
        previous = periods[index]

        length = calculate_cycle_length(
            previous,
            current,
        )

        if length and 15 <= length <= 60:
            cycle_lengths.append(length)

    if not cycle_lengths:
        return DEFAULT_CYCLE_LENGTH

    return round(
        sum(cycle_lengths) / len(cycle_lengths)
    )


def calculate_period_length(period):
    """Calculate the duration of a period."""

    if not period or not period["end_date"]:
        return None

    start = date.fromisoformat(
        period["start_date"]
    )

    end = date.fromisoformat(
        period["end_date"]
    )

    return (
        end - start
    ).days + 1


def calculate_average_period_length(periods):
    """Calculate the user's average period length."""

    lengths = []

    for period in periods:

        length = calculate_period_length(
            period
        )

        if length and 1 <= length <= 15:
            lengths.append(length)

    if not lengths:
        return DEFAULT_PERIOD_LENGTH

    return round(
        sum(lengths) / len(lengths)
    )


def predict_next_period(
    last_period,
    average_cycle_length,
):
    """Predict the next period start date."""

    if not last_period:
        return None

    last_start = date.fromisoformat(
        last_period["start_date"]
    )

    return (
        last_start
        + timedelta(days=average_cycle_length)
    )


def calculate_cycle_day(last_period):
    """Calculate the current cycle day."""

    if not last_period:
        return None

    start = date.fromisoformat(
        last_period["start_date"]
    )

    return (
        date.today() - start
    ).days + 1


# ---------------------------------------------------------
# LANDING PAGE
# ---------------------------------------------------------

@app.route("/")
def landing():
    return render_template(
        "landing.html"
    )


# ---------------------------------------------------------
# REGISTER
# ---------------------------------------------------------

@app.route(
    "/register",
    methods=["GET", "POST"],
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            "",
        ).strip()

        email = request.form.get(
            "email",
            "",
        ).strip().lower()

        password = request.form.get(
            "password",
            "",
        )

        confirm_password = request.form.get(
            "confirm_password",
            "",
        )

        if not name:

            flash(
                "Please enter your name.",
                "error",
            )

            return render_template(
                "register.html"
            )

        if not email:

            flash(
                "Please enter your email address.",
                "error",
            )

            return render_template(
                "register.html"
            )

        if len(password) < 8:

            flash(
                "Password must be at least 8 characters.",
                "error",
            )

            return render_template(
                "register.html"
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error",
            )

            return render_template(
                "register.html"
            )

        db = get_db()

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

            return render_template(
                "register.html"
            )

        password_hash = generate_password_hash(
            password
        )

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

        session.clear()

        session["user_id"] = user_id

        flash(
            "Your account has been created successfully!",
            "success",
        )

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "register.html"
    )


# ---------------------------------------------------------
# SIGN IN
# ---------------------------------------------------------

@app.route(
    "/signin",
    methods=["GET", "POST"],
)
def signin():

    if request.method == "POST":

        email = request.form.get(
            "email",
            "",
        ).strip().lower()

        password = request.form.get(
            "password",
            "",
        )

        if not email or not password:

            flash(
                "Please enter your email and password.",
                "error",
            )

            return render_template(
                "signin.html"
            )

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

            return render_template(
                "signin.html"
            )

        if not check_password_hash(
            user["password_hash"],
            password,
        ):

            flash(
                "Incorrect email or password.",
                "error",
            )

            return render_template(
                "signin.html"
            )

        session.clear()

        session["user_id"] = user["id"]

        flash(
            f"Welcome back, {user['name']}!",
            "success",
        )

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "signin.html"
    )


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------

@app.post("/logout")
@login_required
def logout():

    session.clear()

    return redirect(
        url_for("landing")
    )


# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    """Display the user's cycle dashboard."""

    user = get_current_user()

    db = get_db()

    periods = db.execute(
        """
        SELECT *
        FROM periods
        WHERE user_id = ?
        ORDER BY start_date DESC
        """,
        (user["id"],),
    ).fetchall()

    average_cycle_length = (
        calculate_average_cycle(periods)
    )

    average_period_length = (
        calculate_average_period_length(periods)
    )

    last_period = (
        periods[0]
        if periods
        else None
    )

    next_period = predict_next_period(
        last_period,
        average_cycle_length,
    )

    cycle_day = calculate_cycle_day(
        last_period
    )

    days_until_next_period = None

    if next_period:

        days_until_next_period = (
            next_period - date.today()
        ).days

    # -----------------------------------------------------
    # Predictions
    # -----------------------------------------------------

    ovulation_date = None
    fertile_start = None
    fertile_end = None

    if next_period:

        ovulation_date = (
            next_period
            - timedelta(days=14)
        )

        fertile_start = (
            ovulation_date
            - timedelta(days=5)
        )

        fertile_end = ovulation_date

    # -----------------------------------------------------
    # Calendar
    # -----------------------------------------------------

    today = date.today()

    current_month = today.month
    current_year = today.year
    current_day = today.day

    month_calendar = calendar.monthcalendar(
        current_year,
        current_month,
    )

    # -----------------------------------------------------
    # Period dates
    # -----------------------------------------------------

    period_dates = set()

    for period in periods:

        start = date.fromisoformat(
            period["start_date"]
        )

        if period["end_date"]:

            end = date.fromisoformat(
                period["end_date"]
            )

        else:

            end = start

        current = start

        while current <= end:

            if (
                current.year == current_year
                and current.month == current_month
            ):

                period_dates.add(
                    current.day
                )

            current += timedelta(days=1)

    # -----------------------------------------------------
    # Fertile dates
    # -----------------------------------------------------

    fertile_dates = set()

    if fertile_start and fertile_end:

        current = fertile_start

        while current <= fertile_end:

            if (
                current.year == current_year
                and current.month == current_month
            ):

                fertile_dates.add(
                    current.day
                )

            current += timedelta(days=1)

    # -----------------------------------------------------
    # Ovulation day
    # -----------------------------------------------------

    ovulation_day = None

    if ovulation_date:

        if (
            ovulation_date.year == current_year
            and ovulation_date.month == current_month
        ):

            ovulation_day = (
                ovulation_date.day
            )

    # -----------------------------------------------------
    # Recent periods
    # -----------------------------------------------------

    recent_periods = []

    for period in periods[:3]:

        recent_periods.append(
            {
                "period": period,
                "duration": calculate_period_length(
                    period
                ),
            }
        )

    return render_template(
        "dashboard.html",
        user=user,
        periods=periods,
        last_period=last_period,
        next_period=next_period,
        cycle_day=cycle_day,
        average_cycle_length=average_cycle_length,
        average_period_length=average_period_length,
        days_until_next_period=days_until_next_period,
        ovulation_date=ovulation_date,
        fertile_start=fertile_start,
        fertile_end=fertile_end,
        month_calendar=month_calendar,
        current_month_name=calendar.month_name[
            current_month
        ],
        current_year=current_year,
        current_day=current_day,
        recent_periods=recent_periods,
        period_dates=period_dates,
        fertile_dates=fertile_dates,
        ovulation_day=ovulation_day,
    )


# ---------------------------------------------------------
# LOG PERIOD
# ---------------------------------------------------------

@app.route(
    "/log-period",
    methods=["GET", "POST"],
)
@login_required
def log_period():
    """Log a new period."""

    if request.method == "POST":

        start_date = request.form.get(
            "start_date",
            "",
        ).strip()

        end_date = request.form.get(
            "end_date",
            "",
        ).strip()

        flow = request.form.get(
            "flow",
            "",
        ).strip().lower()

        selected_symptoms = (
            request.form.getlist("symptoms")
        )

        symptoms = ", ".join(
            selected_symptoms
        )

        # -------------------------------------------------
        # Validate start date
        # -------------------------------------------------

        if not start_date:

            flash(
                "Please select the first day of your period.",
                "error",
            )

            return render_template(
                "log_period.html",
                flow_levels=FLOW_LEVELS,
                symptoms=SYMPTOMS,
            )

        try:

            start = date.fromisoformat(
                start_date
            )

        except ValueError:

            flash(
                "Please enter a valid start date.",
                "error",
            )

            return render_template(
                "log_period.html",
                flow_levels=FLOW_LEVELS,
                symptoms=SYMPTOMS,
            )

        # -------------------------------------------------
        # Validate end date
        # -------------------------------------------------

        end = None

        if end_date:

            try:

                end = date.fromisoformat(
                    end_date
                )

            except ValueError:

                flash(
                    "Please enter a valid end date.",
                    "error",
                )

                return render_template(
                    "log_period.html",
                    flow_levels=FLOW_LEVELS,
                    symptoms=SYMPTOMS,
                )

            if end < start:

                flash(
                    "The end date cannot be before the start date.",
                    "error",
                )

                return render_template(
                    "log_period.html",
                    flow_levels=FLOW_LEVELS,
                    symptoms=SYMPTOMS,
                )

        # -------------------------------------------------
        # Validate flow
        # -------------------------------------------------

        if flow not in FLOW_LEVELS:

            flash(
                "Please select your flow level.",
                "error",
            )

            return render_template(
                "log_period.html",
                flow_levels=FLOW_LEVELS,
                symptoms=SYMPTOMS,
            )

        # -------------------------------------------------
        # Save period
        # -------------------------------------------------

        db = get_db()

        db.execute(
            """
            INSERT INTO periods (
                user_id,
                start_date,
                end_date,
                flow,
                symptoms
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                start_date,
                end_date,
                flow,
                symptoms,
            ),
        )

        db.commit()

        flash(
            "Your period has been logged successfully.",
            "success",
        )

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "log_period.html",
        flow_levels=FLOW_LEVELS,
        symptoms=SYMPTOMS,
    )


# ---------------------------------------------------------
# HISTORY
# ---------------------------------------------------------

@app.route("/history")
@login_required
def history():
    """Display the user's period history."""

    user = get_current_user()

    db = get_db()

    periods = db.execute(
        """
        SELECT *
        FROM periods
        WHERE user_id = ?
        ORDER BY start_date DESC
        """,
        (user["id"],),
    ).fetchall()

    history_periods = []

    for period in periods:

        history_periods.append(
            {
                "period": period,
                "duration": calculate_period_length(
                    period
                ),
            }
        )

    return render_template(
        "history.html",
        user=user,
        periods=periods,
        history_periods=history_periods,
    )


# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------

with app.app_context():
    init_db()


# ---------------------------------------------------------
# RUN APPLICATION
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=True
    )
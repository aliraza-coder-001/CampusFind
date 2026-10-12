from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB_PATH = Path(__file__).with_name("campus_items.db")

CATEGORIES = ["ID Card", "Books/Notes", "Electronics", "Keys", "Wallet/Bag", "Clothing", "Other"]
ITEM_TYPES = ["Lost", "Found"]
STATUSES = ["Open", "Resolved"]


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                report_date TEXT NOT NULL,
                description TEXT NOT NULL,
                contact TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL
            )
        """)


@app.route("/")
def index():
    search = request.args.get("search", "").strip()
    item_type = request.args.get("type", "").strip()
    category = request.args.get("category", "").strip()

    sql = "SELECT * FROM reports WHERE 1=1"
    params = []
    if search:
        sql += " AND (item_name LIKE ? OR location LIKE ? OR description LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
    if item_type in ITEM_TYPES:
        sql += " AND item_type = ?"
        params.append(item_type)
    if category in CATEGORIES:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY id DESC"

    with get_db() as con:
        reports = con.execute(sql, params).fetchall()
        total = con.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        open_count = con.execute("SELECT COUNT(*) FROM reports WHERE status='Open'").fetchone()[0]
        resolved_count = con.execute("SELECT COUNT(*) FROM reports WHERE status='Resolved'").fetchone()[0]

    return render_template(
        "index.html",
        reports=reports,
        categories=CATEGORIES,
        search=search,
        selected_type=item_type,
        selected_category=category,
        total=total,
        open_count=open_count,
        resolved_count=resolved_count,
    )


@app.route("/add", methods=["GET", "POST"])
def add_report():
    if request.method == "POST":
        item_type = request.form.get("item_type", "")
        item_name = request.form.get("item_name", "").strip()
        category = request.form.get("category", "")
        location = request.form.get("location", "").strip()
        report_date = request.form.get("report_date", "")
        description = request.form.get("description", "").strip()
        contact = request.form.get("contact", "").strip()

        if (item_type not in ITEM_TYPES or category not in CATEGORIES or
                not item_name or not location or not report_date or
                not description or not contact):
            flash("Please complete all fields with valid information.", "error")
            return render_template("add.html", categories=CATEGORIES, item_types=ITEM_TYPES)

        with get_db() as con:
            con.execute("""
                INSERT INTO reports
                (item_type, item_name, category, location, report_date, description, contact, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Open', ?)
            """, (item_type, item_name, category, location, report_date, description,
                  contact, datetime.now().strftime("%Y-%m-%d %H:%M")))
        flash("Your report has been submitted.", "success")
        return redirect(url_for("index"))

    return render_template("add.html", categories=CATEGORIES, item_types=ITEM_TYPES)


@app.route("/resolve/<int:report_id>", methods=["POST"])
def resolve_report(report_id):
    with get_db() as con:
        con.execute("UPDATE reports SET status='Resolved' WHERE id=?", (report_id,))
    flash("Report status updated to Resolved.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/delete/<int:report_id>", methods=["POST"])
def delete_report(report_id):
    # Demonstration project: delete action is available for local administration.
    with get_db() as con:
        con.execute("DELETE FROM reports WHERE id=?", (report_id,))
    flash("Report deleted.", "success")
    return redirect(url_for("index"))


@app.route("/matches/<int:report_id>")
def matches(report_id):
    with get_db() as con:
        current = con.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
        if current is None:
            flash("Report not found.", "error")
            return redirect(url_for("index"))
        opposite_type = "Found" if current["item_type"] == "Lost" else "Lost"
        # Simple matching: same category and at least one shared word in item name.
        words = [w.lower() for w in current["item_name"].split() if len(w) > 2]
        candidates = con.execute("""
            SELECT * FROM reports
            WHERE item_type=? AND category=? AND status='Open' AND id != ?
            ORDER BY id DESC
        """, (opposite_type, current["category"], report_id)).fetchall()
        matches_found = []
        for candidate in candidates:
            candidate_text = (candidate["item_name"] + " " + candidate["description"] + " " + candidate["location"]).lower()
            if not words or any(word in candidate_text for word in words):
                matches_found.append(candidate)
    return render_template("matches.html", current=current, matches=matches_found)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

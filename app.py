import sqlite3
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, g

app = Flask(__name__)
DATABASE = "notes.db"

# ---------------- Database Setup ---------------- #

def get_db():
    """Open a database connection tied to the request context."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row   # rows behave like dicts
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Automatically close DB connection after each request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    """Create tables if they don't exist."""
    db = sqlite3.connect(DATABASE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            title     TEXT    UNIQUE NOT NULL,
            content   TEXT    NOT NULL,
            timestamp TEXT    NOT NULL
        )
    """)
    db.commit()
    db.close()

# ---------------- Helper ---------------- #

def note_to_dict(row):
    """Convert a sqlite3.Row to a plain dictionary."""
    return {
        "id":        row["id"],
        "title":     row["title"],
        "content":   row["content"],
        "timestamp": row["timestamp"]
    }

# ---------------- Routes ---------------- #

@app.route("/")
def index():
    return render_template("index.html")

# CREATE
@app.route("/api/notes", methods=["POST"])
def create_note():
    data    = request.get_json(silent=True) or {}
    title   = data.get("title",   "").strip()
    content = data.get("content", "").strip()

    if not title or not content:
        return jsonify({"error": "Title and content are required."}), 400

    if len(title) > 100:
        return jsonify({"error": "Title must be under 100 characters."}), 400

    try:
        db = get_db()
        db.execute(
            "INSERT INTO notes (title, content, timestamp) VALUES (?, ?, ?)",
            (title, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        db.commit()
        note = db.execute(
            "SELECT * FROM notes WHERE title = ?", (title,)
        ).fetchone()
        return jsonify({"message": f"Note '{title}' created successfully.", "note": note_to_dict(note)}), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "A note with this title already exists."}), 409

# READ ALL
@app.route("/api/notes", methods=["GET"])
def get_all_notes():
    db    = get_db()
    notes = db.execute("SELECT * FROM notes ORDER BY timestamp DESC").fetchall()
    return jsonify([note_to_dict(n) for n in notes]), 200

# READ ONE
@app.route("/api/notes/<int:note_id>", methods=["GET"])
def get_note(note_id):
    db   = get_db()
    note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        return jsonify({"error": "Note not found."}), 404
    return jsonify(note_to_dict(note)), 200

# UPDATE
@app.route("/api/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    data        = request.get_json(silent=True) or {}
    new_content = data.get("content", "").strip()

    if not new_content:
        return jsonify({"error": "Content is required."}), 400

    db     = get_db()
    result = db.execute(
        "UPDATE notes SET content = ?, timestamp = ? WHERE id = ?",
        (new_content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), note_id)
    )
    db.commit()

    if result.rowcount == 0:
        return jsonify({"error": "Note not found."}), 404

    note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    return jsonify({"message": "Note updated successfully.", "note": note_to_dict(note)}), 200

# DELETE
@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    db     = get_db()
    note   = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        return jsonify({"error": "Note not found."}), 404

    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    return jsonify({"message": f"Note '{note['title']}' deleted successfully."}), 200

# SEARCH
@app.route("/api/notes/search", methods=["GET"])
def search_notes():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([]), 200
    db    = get_db()
    notes = db.execute(
        "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY timestamp DESC",
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    return jsonify([note_to_dict(n) for n in notes]), 200

# ---------------- Entry Point ---------------- #

if __name__ == "__main__":
    init_db()
    app.run()

init_db()
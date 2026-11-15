import re
from functools import wraps
from flask import Flask, g, request, session, redirect, abort, flash, url_for, get_flashed_messages
from jinja2 import Environment, DictLoader
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
try:
    from config import SECRET_KEY
except ImportError:
    raise SystemExit("Missing config.py file - create config.py and set SECRET_KEY according to repository README.: .")

app.secret_key = SECRET_KEY # for safely storing cookies and session data by flask

LAUNCHER_EDITIONS = ["Java", "Bedrock"]
GAME_VERSIONS = ["1.21", "1.20", "1.19"]

# Database configuration

def database():
    if "database" not in g:
        g.database = sqlite3.connect("minecraft-seeds-db.sqlite")
        g.database.row_factory = sqlite3.Row
    return g.database

def database_query(sql, *args):
    return database().execute(sql, args).fetchall()

def run_database(sql, *args):
    database().execute(sql, args)
    database().commit()

@app.teardown_appcontext
def close_database(_):
    connection = g.pop("database", None)
    if connection:
        connection.close()

with app.app_context():
    database().executescript("""
        CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL);

        CREATE TABLE IF NOT EXISTS seeds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        title TEXT NOT NULL,
        seed TEXT NOT NULL,
        launcher_edition TEXT NOT NULL,
        game_version TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '');
    """)

# Form configurations and entered information validation

def form(name, label, type="text", **kwargs):
    return dict(name=name, label=label, type=type, **kwargs)

LOGIN_FORM = [form("username", "Username", max=32),
              form("password", "Password", "password", max=64)]

REGISTER_FORM = [form("username", "Username", max=32),
                 form("password", "Password", "password", min=4, max=64),
                 form("password_confirmation", "Confirm password", "password", max=64)]

SEED_FORM = [form("title", "Seed title", max=64),
             form("seed", "Seed number", max=64),
             form("launcher_edition", "Launcher edition", "select", options=LAUNCHER_EDITIONS),
             form("game_version", "Game version", "select", options=GAME_VERSIONS),
             form("description", "Description", "textarea", max=500, optional=True)]

SEED_FILTERS = [form("q", "Search", max=64, optional=True),
                form("launcher_edition", "Launcher edition", "select", options=LAUNCHER_EDITIONS, any_label="All", optional=True),
                form("game_version", "Game version", "select", options=GAME_VERSIONS, any_label="All", optional=True)]

def get_fields_from_forms(fields):
    return {f["name"]: request.form.get(f["name"], "") if f["type"] == "password"
            else request.form.get(f["name"], "").strip()
            for f in fields}

def check_field(fields, value):
    errors = []
    for f in fields:
        val, label = value.get(f["name"], ""), f["label"]
        if not val:
            if not f.get("optional"):
                errors.append(f"{label} is required.")
            continue
        lo, hi = f.get("min", 1), f.get("max", 100)
        if not lo <= len(val) <= hi:
            errors.append(f"{label} must be between {lo} and {hi} characters.")
        elif f["type"] == "select" and val not in f["options"]:
            errors.append(f"{label} must be one of: {', '.join(f['options'])}.")
        elif f.get("pattern") and not re.fullmatch(f["pattern"], val):
            errors.append(f"{label} has an invalid format.")
    return errors

def render(name, **context):
    return env.get_template(name).render(context)

def page(title, fields, submit, values, errors=(), alt=None):
    return render("form.html", title=title, fields=fields, submit=submit,
                  v=values, errors=errors, alt=alt)

def login_is_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return view(*args, **kwargs)
    return wrapper

# Routes of an app

@app.route("/")
def index():
    sql = ("SELECT seeds.*, users.username FROM seeds "
           "JOIN users ON users.id = seeds.user_id WHERE 1=1")
    args = []
    text = request.args.get("q", "").strip()
    if text:
        sql += " AND (title LIKE ? OR description LIKE ? OR seed LIKE ?)"
        args += [f"%{text}%"] * 3
    for key in ("launcher_edition", "game_version"):
        if request.args.get(key):
            sql += f" AND {key} = ?"
            args.append(request.args[key])
    seeds = database_query(sql + " ORDER BY seeds.id DESC", *args)
    return render("index.html", title="Minecraft Seeds Database", seeds=seeds, filters=SEED_FILTERS)

@app.route("/register", methods=["GET", "POST"])
def register():
    errors = []
    v = get_fields_from_forms(REGISTER_FORM) if request.method == "POST" else {}
    if request.method == "POST":
        errors = check_field(REGISTER_FORM, v)
        if not errors and v["password"] != v["password_confirmation"]:
            errors.append("Passwords do not match.")
        if not errors:
            try:
                run_database("INSERT INTO users (username, password) VALUES (?, ?)",
                             v["username"], generate_password_hash(v["password"]))
                flash("Account created successfully. You can now sign in.")
                return redirect("/login")
            except sqlite3.IntegrityError:
                errors.append("Username already exists.")
    return page("Create an account", REGISTER_FORM, "Create account", v, errors,
                ("Already have an account?", "Log in", "/login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    errors = []
    v = get_fields_from_forms(LOGIN_FORM) if request.method == "POST" else {}
    if request.method == "POST":
        errors = check_field(LOGIN_FORM, v)
        if not errors:
            rows = database_query("SELECT * FROM users WHERE username = ?", v["username"])
            if rows and check_password_hash(rows[0]["password"], v["password"]):
                session.clear()
                session["user_id"] = rows[0]["id"]
                session["username"] = rows[0]["username"]
                return redirect("/")
            errors.append("Invalid username or password.")
    return page("Sign in", LOGIN_FORM, "Sign in", v, errors,
                ("No account yet?", "Create one", "/register"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/seed/new", methods=["GET", "POST"])
@app.route("/seed/<int:seed_id>/edit", methods=["GET", "POST"])
@login_is_required
def seed_form(seed_id=None):
    row = None
    if seed_id:
        rows = database_query("SELECT * FROM seeds WHERE id = ?", seed_id)
        if not rows:
            abort(404)
        row = rows[0]
        if row["user_id"] != session["user_id"]:
            abort(403)

    errors = []
    if request.method == "POST":
        v = get_fields_from_forms(SEED_FORM)
        errors = check_field(SEED_FORM, v)
        if not errors:
            values = [v[f["name"]] for f in SEED_FORM]
            if seed_id:
                run_database("UPDATE seeds SET title=?, seed=?, launcher_edition=?, "
                             "game_version=?, description=? WHERE id = ?", *values, seed_id)
            else:
                run_database("INSERT INTO seeds (title, seed, launcher_edition, game_version, "
                             "description, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                             *values, session["user_id"])
            return redirect("/")
    else:
        v = dict(row) if row else {}

    heading = "Edit seed" if seed_id else "Add seed"
    return page(heading, SEED_FORM, heading, v, errors)

@app.route("/seed/<int:seed_id>/delete", methods=["POST"])
@login_is_required
def delete_seed(seed_id):
    run_database("DELETE FROM seeds WHERE id = ? AND user_id = ?", seed_id, session["user_id"])
    return redirect("/")

# Minimal template for the app

TEMPLATES = {

    "base.html": """<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MSDB</title>
</head>
<body>
    <header>
        <h1><a href="/">MSDB</a></h1>
        <nav>
            <a href="/">Browse seeds</a>
            {% if session.user_id %}
                <a href="/seed/new">Add seed</a>
                <a href="/logout">Sign out ({{ session.username }})</a>
            {% else %}
                <a href="/login">Sign in</a>
                <a href="/register">Create new account</a>
            {% endif %}
        </nav>
    </header>
    <br>
    <main>
        {% for m in get_flashed_messages() %}<p>{{ m }}</p>{% endfor %}
        {% block content %}{% endblock %}
    </main>
</body>
</html>""",

    "macros.html": """{% macro field(f, v) %}
<div>
    <label for="{{ f.name }}">{{ f.label }}</label><br>
    {% if f.type == 'select' %}
        <select id="{{ f.name }}" name="{{ f.name }}">
            {% if f.any_label %}<option value="">{{ f.any_label }}</option>{% endif %}
            {% for o in f.options %}
                <option value="{{ o }}" {{ 'selected' if v.get(f.name) == o }}>{{ o }}</option>
            {% endfor %}
        </select>
    {% elif f.type == 'textarea' %}
        <textarea id="{{ f.name }}" name="{{ f.name }}" rows="4" maxlength="{{ f.max }}">{{ v.get(f.name, '') }}</textarea>
    {% else %}
        <input type="{{ f.type }}" id="{{ f.name }}" name="{{ f.name }}"
               value="{{ '' if f.type == 'password' else v.get(f.name, '') }}"
               {% if f.max %}maxlength="{{ f.max }}"{% endif %}
               {% if f.min %}minlength="{{ f.min }}"{% endif %}
               {% if f.pattern %}pattern="{{ f.pattern }}"{% endif %}
               {% if not f.optional %}required{% endif %}>
    {% endif %}
</div>
<br>
{% endmacro %}""",

    "form.html": """{% extends "base.html" %}
{% from "macros.html" import field %}
{% block content %}
<section>
    <h1>{{ title }}</h1>
    {% for e in errors %}<p>{{ e }}</p>{% endfor %}
    <form method="post">
        {% for f in fields %}{{ field(f, v) }}{% endfor %}
        <button type="submit">{{ submit }}</button>
    </form>
    <br>
    {% if alt %}<p>{{ alt[0] }} <a href="{{ alt[2] }}">{{ alt[1] }}</a></p>{% endif %}
</section>
{% endblock %}""",

    "index.html": """{% extends "base.html" %}
{% from "macros.html" import field %}
{% block content %}
<section>
    <h1>MSDB: small collection of good Minecraft seeds.</h1>
</section>
<br>

<form method="get">
    {% for f in filters %}{{ field(f, request.args) }}{% endfor %}
    <button type="submit">Search</button>
</form>
<br>

<section>
    {% for s in seeds %}
    <article>
        <p><h4>{{ s.launcher_edition }}</h4> | <h4>{{ s.game_version }}</h4> | <h4>{{ s.seed }}</h4></p>
        <h2>{{ s.title }}</h2>
        <p>{{ s.description }}</p>
        <p>by {{ s.username }}</p>
        {% if s.user_id == session.user_id %}
        <div>
            <a href="/seed/{{ s.id }}/edit">Edit</a>
            <form method="post" action="/seed/{{ s.id }}/delete">
                <button type="submit">Delete</button>
            </form>
        </div>
        {% endif %}
    </article>
    <br>
    {% else %}
    <p>No seeds found.</p>
    {% endfor %}
</section>
{% endblock %}""",
}

env = Environment(loader=DictLoader(TEMPLATES), autoescape=True)
env.globals.update(session=session, request=request, url_for=url_for,
                   get_flashed_messages=get_flashed_messages)

if __name__ == "__main__":
    app.run(debug=True)
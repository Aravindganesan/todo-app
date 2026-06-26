import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aravindganesan@localhost:5432/todoapp")


def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_steps (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL
                )
                """
            )

            for step_name in ("backlog", "in_progress", "completed"):
                cur.execute(
                    "INSERT INTO workflow_steps (name) SELECT %s WHERE NOT EXISTS (SELECT 1 FROM workflow_steps WHERE name = %s)",
                    (step_name, step_name),
                )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS todos (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    username TEXT NOT NULL,
                    workflow_step_id INTEGER,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    last_moved_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )

            cur.execute("ALTER TABLE todos ADD COLUMN IF NOT EXISTS workflow_step_id INTEGER")
            cur.execute("ALTER TABLE todos ADD COLUMN IF NOT EXISTS last_moved_at TIMESTAMPTZ")

            cur.execute(
                "UPDATE todos SET workflow_step_id = (SELECT id FROM workflow_steps WHERE name = 'backlog') WHERE workflow_step_id IS NULL"
            )
            cur.execute(
                "UPDATE todos SET last_moved_at = COALESCE(updated_at, created_at, NOW()) WHERE last_moved_at IS NULL"
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS todo_history (
                    id SERIAL PRIMARY KEY,
                    todo_id INTEGER NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
                    workflow_step_id INTEGER NOT NULL REFERENCES workflow_steps(id),
                    changed_at TIMESTAMPTZ DEFAULT NOW(),
                    changed_by TEXT NOT NULL
                )
                """
            )


init_db()


@app.get("/")
def index():
    return send_file("index.html")


@app.get("/api/todos")
def list_todos():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    t.id,
                    t.title,
                    t.username,
                    t.created_at,
                    t.updated_at,
                    t.last_moved_at,
                    t.workflow_step_id,
                    ws.name AS workflow_step
                FROM todos t
                JOIN workflow_steps ws ON ws.id = t.workflow_step_id
                ORDER BY t.created_at DESC
                """
            )
            rows = cur.fetchall()
            return jsonify([dict(row) for row in rows])


@app.get("/api/todos/<int:todo_id>/history")
def todo_history(todo_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    th.changed_at,
                    th.changed_by,
                    ws.name AS workflow_step
                FROM todo_history th
                JOIN workflow_steps ws ON ws.id = th.workflow_step_id
                WHERE th.todo_id = %s
                ORDER BY th.changed_at ASC
                """,
                (todo_id,),
            )
            rows = cur.fetchall()
            return jsonify([dict(row) for row in rows])


@app.post("/api/todos")
def create_todo():
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    username = (payload.get("username") or "anonymous").strip() or "anonymous"
    workflow_step_name = (payload.get("workflow_step") or "backlog").strip().lower() or "backlog"

    if not title:
        return jsonify({"error": "Title is required"}), 400

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM workflow_steps WHERE name = %s", (workflow_step_name,))
            step_row = cur.fetchone()
            if not step_row:
                cur.execute("INSERT INTO workflow_steps (name) VALUES (%s) RETURNING id", (workflow_step_name,))
                step_row = cur.fetchone()
            step_id = step_row["id"]

            cur.execute(
                """
                INSERT INTO todos (title, username, workflow_step_id, last_moved_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id, title, username, workflow_step_id, created_at, updated_at, last_moved_at
                """,
                (title, username, step_id),
            )
            row = cur.fetchone()
            cur.execute(
                "INSERT INTO todo_history (todo_id, workflow_step_id, changed_by) VALUES (%s, %s, %s)",
                (row["id"], step_id, username),
            )
            cur.execute(
                """
                SELECT
                    t.id,
                    t.title,
                    t.username,
                    t.created_at,
                    t.updated_at,
                    t.last_moved_at,
                    t.workflow_step_id,
                    ws.name AS workflow_step
                FROM todos t
                JOIN workflow_steps ws ON ws.id = t.workflow_step_id
                WHERE t.id = %s
                """,
                (row["id"],),
            )
            created_row = cur.fetchone()
            return jsonify(dict(created_row)), 201


@app.post("/api/todos/<int:todo_id>/move")
def move_todo(todo_id):
    payload = request.get_json(silent=True) or {}
    workflow_step_name = (payload.get("workflow_step") or "backlog").strip().lower() or "backlog"
    changed_by = (payload.get("username") or "anonymous").strip() or "anonymous"

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM workflow_steps WHERE name = %s", (workflow_step_name,))
            step_row = cur.fetchone()
            if not step_row:
                cur.execute("INSERT INTO workflow_steps (name) VALUES (%s) RETURNING id", (workflow_step_name,))
                step_row = cur.fetchone()
            step_id = step_row["id"]

            cur.execute(
                """
                UPDATE todos
                SET workflow_step_id = %s, updated_at = NOW(), last_moved_at = NOW()
                WHERE id = %s
                RETURNING id, title, username, workflow_step_id, created_at, updated_at, last_moved_at
                """,
                (step_id, todo_id),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Todo not found"}), 404

            cur.execute(
                "INSERT INTO todo_history (todo_id, workflow_step_id, changed_by) VALUES (%s, %s, %s)",
                (todo_id, step_id, changed_by),
            )

            cur.execute(
                """
                SELECT
                    t.id,
                    t.title,
                    t.username,
                    t.created_at,
                    t.updated_at,
                    t.last_moved_at,
                    t.workflow_step_id,
                    ws.name AS workflow_step
                FROM todos t
                JOIN workflow_steps ws ON ws.id = t.workflow_step_id
                WHERE t.id = %s
                """,
                (todo_id,),
            )
            updated_row = cur.fetchone()
            return jsonify(dict(updated_row))


@app.delete("/api/todos/<int:todo_id>")
def delete_todo(todo_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM todos WHERE id = %s RETURNING id", (todo_id,))
            deleted = cur.fetchone()
            if not deleted:
                return jsonify({"error": "Todo not found"}), 404
            return jsonify({"deleted": True, "id": todo_id})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)

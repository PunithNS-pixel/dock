import os
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.environ["DB_NAME"],
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
    "connect_timeout": 5,
}


def connect_db():
    return psycopg.connect(**DB_CONFIG, row_factory=dict_row)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                title TEXT NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)
    yield


app = FastAPI(title="Docker Task Manager", lifespan=lifespan)


class TaskCreate(BaseModel):
    title: str
    completed: bool = False


@app.get("/")
def home():
    return {"message": "Task Manager API with PostgreSQL"}


@app.get("/health")
def health():
    try:
        with connect_db() as conn:
            conn.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.get("/tasks")
def get_tasks():
    with connect_db() as conn:
        rows = conn.execute(
            "SELECT id, title, completed FROM tasks ORDER BY id"
        ).fetchall()
    return rows


@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    with connect_db() as conn:
        row = conn.execute(
            """
            INSERT INTO tasks (title, completed)
            VALUES (%s, %s)
            RETURNING id, title, completed
            """,
            (task.title, task.completed),
        ).fetchone()
    return row

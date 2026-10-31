"""Idempotent schema upgrade: adds the few columns/tables the app needs on top of Task.sql.
Runs automatically at backend start-up, so no manual SQL step is required."""
from sqlalchemy import inspect, text
from database import engine, Base
import models  # noqa: F401


def run():
    from seed import ensure_database, seed_if_empty
    ensure_database()
    Base.metadata.create_all(bind=engine)  # creates task_history if missing
    insp = inspect(engine)
    with engine.begin() as c:
        task_cols = {x["name"] for x in insp.get_columns("tasks")}
        if "estimated_hours" not in task_cols:
            c.execute(text("ALTER TABLE tasks ADD COLUMN estimated_hours FLOAT DEFAULT 0"))
        if "created_at" not in task_cols:
            c.execute(text("ALTER TABLE tasks ADD COLUMN created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP"))
        b_cols = {x["name"] for x in insp.get_columns("bottlenecks")}
        if "task_id" not in b_cols:
            c.execute(text("ALTER TABLE bottlenecks ADD COLUMN task_id INT NULL"))
    seed_if_empty()

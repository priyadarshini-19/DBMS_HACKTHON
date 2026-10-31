"""Auto-creates the database and loads the 50-record dataset from Task.sql
when the database is empty, so no manual SQL import is needed."""
import os
import re
from pathlib import Path

from sqlalchemy import text

from database import engine

SQL_FILE = Path(__file__).with_name("Task.sql")
TABLES = ["replies", "bottlenecks", "planner", "task_history", "task_skills", "tasks", "projects",
          "skill_logs", "user_skills", "notifications", "skills", "users"]


def ensure_database():
    """Create the MySQL database if it does not exist yet."""
    if engine.dialect.name != "mysql":
        return
    import pymysql
    conn = pymysql.connect(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "3306")),
                           user=os.getenv("DB_USER", "root"), password=os.getenv("DB_PASSWORD", ""))
    try:
        with conn.cursor() as c:
            c.execute(f"CREATE DATABASE IF NOT EXISTS `{os.getenv('DB_NAME', 'task_mgmt')}`")
        conn.commit()
    finally:
        conn.close()


def _statements(sql):
    sql = re.sub(r"(?m)^\s*--.*$", "", sql)
    out, cur, q = [], [], False
    for ch in sql:
        if ch == "'":
            q = not q
        if ch == ";" and not q:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    return [s for s in out if s]


def seed_if_empty():
    with engine.connect() as c:
        if c.execute(text("SELECT COUNT(*) FROM projects")).scalar() > 0:
            return
    if not SQL_FILE.exists():
        print("[TaskFlow] Task.sql not found - skipping seed")
        return
    inserts = [s for s in _statements(SQL_FILE.read_text(encoding="utf-8")) if s.upper().startswith("INSERT")]
    with engine.begin() as c:
        c.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        for t in TABLES:
            c.exec_driver_sql(f"DELETE FROM `{t}`")
            try:
                c.exec_driver_sql(f"ALTER TABLE `{t}` AUTO_INCREMENT = 1")
            except Exception:
                pass
        c.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")
        for s in inserts:
            c.exec_driver_sql(s)
    print(f"[TaskFlow] Loaded dataset from Task.sql ({len(inserts)} insert statements)")

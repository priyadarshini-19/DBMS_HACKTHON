from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import migrate
from routers import auth_routes, manager, employee, shared

@asynccontextmanager
async def lifespan(app):
    migrate.run()
    try:
        from database import SessionLocal, DATABASE_URL
        from models import User, Project, Task
        db = SessionLocal()
        print(f"[TaskFlow] DB: {DATABASE_URL.rsplit('@', 1)[-1]} -> users={db.query(User).count()} "
              f"projects={db.query(Project).count()} tasks={db.query(Task).count()}")
        db.close()
    except Exception as e:
        print("[TaskFlow] DB check failed:", e)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="TaskFlow - Employee Task Management API",
    version="2.0.0",
    description="Separate Manager and Employee APIs. Click 'Authorize' and log in with e.g. manager@demo.com / password123.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


app.include_router(auth_routes.router)
app.include_router(auth_routes.notif_router)
app.include_router(shared.router)
app.include_router(manager.router)
app.include_router(employee.router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "TaskFlow API is running. Docs at /docs"}


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok"}

# TaskFlow – Employee Task Management (React + FastAPI + MySQL)

First page = **Choose your portal** → Manager Portal or Employee Portal. Each role has its own login, sidebar, modules and API routes (`/api/manager/*`, `/api/employee/*`).

| Manager | Employee |
|---|---|
| Dashboard, Project Management, Task Management, Skill-Based Matching, Team Overview | Dashboard, My Tasks, Daily Planner, Bottleneck Detective, Skill Growth Tracker |

Both also get Notifications and Profile. Task status: Pending / In Progress / Completed. Priority: Low / Medium / High.

## Folder structure
```
Task-Management/
├── Task.sql                 # MySQL schema + demo data
├── backend/                 # FastAPI
│   ├── main.py  database.py  models.py  schemas.py  auth.py  common.py  migrate.py
│   ├── routers/ (auth_routes.py, manager.py, employee.py, shared.py)
│   ├── requirements.txt  .env.example  .env
└── src/  (React + Vite frontend: App.jsx, ManagerPortal.jsx, EmployeePortal.jsx, Shared.jsx, ui.jsx, api.js)
```

## 1. Database (MySQL) - automatic
Just make sure MySQL is running and `backend/.env` has your password. On first start the backend creates `task_mgmt`, the tables and loads the 50-record dataset from `backend/Task.sql` by itself (only when there are no projects). Manual import is optional.

### (optional) manual import
Open MySQL Workbench (or CLI) and run the whole file `Task.sql`:
```
mysql -u root -p < Task.sql
```
The backend automatically adds the extra column/table it needs on start-up (`tasks.estimated_hours`, `bottlenecks.task_id`, `task_history`) – no manual step.

## 2. Backend (VS Code Terminal 1)
```
cd backend
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # then put YOUR MySQL password in DB_PASSWORD (a .env is already included with password 7890)
uvicorn main:app --reload --port 8000
```
Swagger docs: http://localhost:8000/docs  (click **Authorize**, user = email).

## 3. Frontend (VS Code Terminal 2)
```
npm install
npm run dev
```
Open http://localhost:5173

## 
- Manager: `manager@demo.com`
- Employees: `arjun@demo.com`, `priya@demo.com`, `rahul@demo.com`
You can also register new accounts from each portal.

## How the key features work
- **Skill-based matching** score = 50% skill levels vs required skills + 20% experience (completed tasks using those skills) + 30% availability (open tasks/hours). Manager reviews and clicks *Confirm assignment*.
- **Bottleneck Detective**: employee reports a blocker (optionally with task + skill). Teammates in the same project with that skill (fallback: anyone with the skill / the project team) get a notification and see the chat; they reply, the reporter marks it Resolved.
- **Skill Growth**: completing a task raises levels of its required skills (logged in history); recommendations come from open tasks in your projects needing skills you're weak in.
- **Task history** (manager → Task Management → History) records creation, assignment and progress changes.

## Troubleshooting
- "Cannot reach the backend": start uvicorn on port 8000.
- MySQL access error: fix `DB_PASSWORD` in `backend/.env`.
- Different API URL: create `.env` in project root with `VITE_API_URL=http://localhost:8000/api`.

## Dataset & live updates
`Task.sql` now contains the full dataset (many managers, employees, projects, tasks…). Re-import it (it recreates `task_mgmt`). All managers share one workspace and see every project/task/employee. Every screen auto-refreshes every 5 seconds and refreshes immediately after you add/edit anything, so new records appear without reloading the page.

## If the app shows 0 projects / empty dashboard
The database is empty. Import `Task.sql` again (MySQL Workbench: File → Run SQL Script, or `mysql -u root -p < Task.sql`) and make sure it finishes without errors. On start the backend prints e.g. `[TaskFlow] DB: localhost:3306/task_mgmt -> users=51 projects=50 tasks=54`; if it shows 0, the import didn't work or `backend/.env` points to another database.

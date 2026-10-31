CREATE DATABASE IF NOT EXISTS task_mgmt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE task_mgmt;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  role ENUM('manager','employee') NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_users_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS skills (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS user_skills (
  user_id INT NOT NULL,
  skill_id INT NOT NULL,
  level INT NOT NULL DEFAULT 1,
  target INT NOT NULL DEFAULT 5,
  PRIMARY KEY (user_id, skill_id),
  CONSTRAINT fk_user_skills_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_skills_skill FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS skill_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  skill_id INT NOT NULL,
  level INT NOT NULL,
  logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_skill_logs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_skill_logs_skill FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS projects (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  description TEXT NULL,
  status ENUM('Planning','Active','Completed') NOT NULL DEFAULT 'Planning',
  deadline DATE NULL,
  manager_id INT NOT NULL,
  CONSTRAINT fk_projects_manager FOREIGN KEY (manager_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tasks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  project_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  description TEXT NULL,
  priority ENUM('Low','Medium','High') NOT NULL DEFAULT 'Medium',
  deadline DATE NULL,
  status ENUM('To Do','In Progress','Done') NOT NULL DEFAULT 'To Do',
  progress INT NOT NULL DEFAULT 0,
  assigned_to INT NULL,
  CONSTRAINT fk_tasks_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_tasks_assignee FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS task_skills (
  task_id INT NOT NULL,
  skill_id INT NOT NULL,
  PRIMARY KEY (task_id, skill_id),
  CONSTRAINT fk_task_skills_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
  CONSTRAINT fk_task_skills_skill FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS planner (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  priority ENUM('Low','Medium','High') NOT NULL DEFAULT 'Medium',
  plan_date DATE NOT NULL,
  done BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_planner_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bottlenecks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  description TEXT NULL,
  skill_id INT NULL,
  status ENUM('Open','In Progress','Resolved') NOT NULL DEFAULT 'Open',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_bottlenecks_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_bottlenecks_skill FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS replies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  bottleneck_id INT NOT NULL,
  user_id INT NOT NULL,
  message TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_replies_bottleneck FOREIGN KEY (bottleneck_id) REFERENCES bottlenecks(id) ON DELETE CASCADE,
  CONSTRAINT fk_replies_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  message TEXT NOT NULL,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

INSERT IGNORE INTO skills (name) VALUES
('Communication'), ('Python'), ('JavaScript'), ('React'), ('FastAPI'),
('SQL'), ('Project Planning'), ('Testing'), ('UI/UX Design'), ('Data Analysis');

-- Optional development accounts. Both use password: password123
-- Do not use these accounts or secrets in production.
INSERT IGNORE INTO users (id, name, email, password, role) VALUES
(1, 'Demo Manager', 'manager@example.com', SHA2('password123', 256), 'manager'),
(2, 'Demo Employee', 'employee@example.com', SHA2('password123', 256), 'employee');

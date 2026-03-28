-- ========================================================
-- SMARTCV AUTO - FULL DATABASE SCHEMA (16 TABLES TOTAL)
-- ========================================================

-- ============ 1. ENUM TYPES ============
CREATE TYPE gender_type AS ENUM ('male', 'female', 'other');
CREATE TYPE application_status AS ENUM (
    'mới', 'duyệt', 'từ chối', 'phỏng vấn', 'gửi offer', 'đã tuyển'
);
CREATE TYPE interview_status AS ENUM ('scheduled', 'completed', 'cancelled');
CREATE TYPE interview_type AS ENUM ('online', 'offline');
CREATE TYPE job_status AS ENUM ('open', 'closed', 'paused');
CREATE TYPE experience_level AS ENUM ('intern', 'fresher', 'junior', 'mid', 'senior', 'lead', 'manager');

-- ============ 2. RBAC & USERS ============

-- [1] roles
CREATE TABLE roles (
    name         VARCHAR(100) PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL,
    is_system    BOOLEAN      DEFAULT FALSE,
    created_at   TIMESTAMP    DEFAULT NOW()
);

-- [2] users
CREATE TABLE users (
    id            SERIAL       PRIMARY KEY,
    full_name     VARCHAR(255) NOT NULL,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(100) NOT NULL DEFAULT 'hr_staff' REFERENCES roles(name) ON UPDATE CASCADE,
    is_active     BOOLEAN      DEFAULT TRUE,
    avatar_url    VARCHAR(255),
    api_key       VARCHAR(255) UNIQUE,
    created_at    TIMESTAMP    DEFAULT NOW()
);

-- [3] role_permissions
CREATE TABLE role_permissions (
    role       VARCHAR(100) NOT NULL REFERENCES roles(name) ON DELETE CASCADE ON UPDATE CASCADE,
    resource   VARCHAR(100) NOT NULL,
    can_create BOOLEAN DEFAULT FALSE,
    can_read   BOOLEAN DEFAULT FALSE,
    can_update BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (role, resource)
);

-- ============ 3. CORE CATEGORIES ============

-- [4] departments
CREATE TABLE departments (
    id         SERIAL       PRIMARY KEY,
    name       VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP    DEFAULT NOW()
);

-- [5] skills
CREATE TABLE skills (
    id         SERIAL       PRIMARY KEY,
    name       VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP    DEFAULT NOW()
);

-- [6] branches
CREATE TABLE branches (
    id         SERIAL       PRIMARY KEY,
    name       VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP    DEFAULT NOW()
);

-- ============ 4. JOBS ============

-- [7] jobs
CREATE TABLE jobs (
    id               SERIAL           PRIMARY KEY,
    title            VARCHAR(255)     NOT NULL,
    department_id    INT              REFERENCES departments(id) ON DELETE SET NULL,
    branch_id        INT              REFERENCES branches(id)    ON DELETE SET NULL,
    experience_level experience_level,
    education_level  VARCHAR(100),
    quantity         INT DEFAULT 1,
    description      TEXT,
    requirements     TEXT,
    benefits         TEXT,
    salary_min       INT,
    salary_max       INT,
    salary_currency  VARCHAR(10)      DEFAULT 'VND',
    status           job_status       NOT NULL DEFAULT 'open',
    created_by       INT              REFERENCES users(id) ON DELETE SET NULL,
    created_at       TIMESTAMP        DEFAULT NOW()
);

-- [8] job_skills
CREATE TABLE job_skills (
    job_id   INT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id INT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, skill_id)
);

-- ============ 5. CANDIDATES ============

-- [9] candidates
CREATE TABLE candidates (
    id               SERIAL             PRIMARY KEY,
    full_name        VARCHAR(255)       NOT NULL,
    date_of_birth    DATE,
    gender           gender_type,
    phone            VARCHAR(20),
    email            VARCHAR(255),
    facebook         VARCHAR(255),
    specific_address VARCHAR(500),
    job_id           INT                REFERENCES jobs(id) ON DELETE SET NULL,
    cv_link          VARCHAR(500),
    portfolio_link   VARCHAR(500),
    ai_summary       TEXT,
    score            DECIMAL(4, 2),
    status           application_status NOT NULL DEFAULT 'mới',
    applied_date     DATE               DEFAULT CURRENT_DATE,
    assigned_to      INT                REFERENCES users(id) ON DELETE SET NULL,
    created_by       INT                REFERENCES users(id) ON DELETE SET NULL,
    created_at       TIMESTAMP          DEFAULT NOW()
);

-- [10] candidate_links
CREATE TABLE candidate_links (
    id           SERIAL       PRIMARY KEY,
    candidate_id INT          NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    label        VARCHAR(100) NOT NULL,
    url          VARCHAR(500) NOT NULL,
    created_at   TIMESTAMP    DEFAULT NOW()
);

-- [11] candidate_education
CREATE TABLE candidate_education (
    id           SERIAL       PRIMARY KEY,
    candidate_id INT          NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    degree       VARCHAR(100),
    institution  VARCHAR(255),
    major        VARCHAR(255),
    start_year   SMALLINT,
    end_year     SMALLINT,
    created_at   TIMESTAMP    DEFAULT NOW()
);

-- [12] candidate_experience
CREATE TABLE candidate_experience (
    id           SERIAL       PRIMARY KEY,
    candidate_id INT          NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    position     VARCHAR(255),
    start_date   DATE,
    end_date     DATE,
    description  TEXT,
    created_at   TIMESTAMP    DEFAULT NOW()
);

-- [13] candidate_skills
CREATE TABLE candidate_skills (
    candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    skill_id     INT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (candidate_id, skill_id)
);

-- [14] candidate_notes
CREATE TABLE candidate_notes (
    id           SERIAL    PRIMARY KEY,
    candidate_id INT       NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    created_by   INT       NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    content      TEXT      NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW()
);

-- ============ 6. INTERVIEWS ============

-- [15] interviews
CREATE TABLE interviews (
    id             SERIAL           PRIMARY KEY,
    candidate_id   INT              NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    scheduled_at   TIMESTAMP        NOT NULL,
    end_at         TIMESTAMP,
    interview_type interview_type   NOT NULL,
    location       VARCHAR(500),
    online_link    VARCHAR(1000),
    status         interview_status NOT NULL DEFAULT 'scheduled',
    created_by     INT              REFERENCES users(id) ON DELETE SET NULL,
    created_at     TIMESTAMP        DEFAULT NOW()
);

-- [16] interview_interviewers
CREATE TABLE interview_interviewers (
    interview_id INT NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    user_id      INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (interview_id, user_id)
);

-- ============ 7. SYSTEM SETTINGS ============

-- [17] system_settings
CREATE TABLE system_settings (
    key         VARCHAR(255) PRIMARY KEY,
    value       TEXT NOT NULL
);

-- ============ 8. INDEXES ============
CREATE INDEX idx_candidates_status    ON candidates(status);
CREATE INDEX idx_candidates_job_id    ON candidates(job_id);
CREATE INDEX idx_interviews_candidate ON interviews(candidate_id);
CREATE INDEX idx_interviews_status    ON interviews(status);

-- ============ 9. INITIAL DATA ============
INSERT INTO roles (name, display_name, is_system) VALUES
    ('admin',       'Quản trị viên',        TRUE),
    ('hr_staff',    'Chuyên viên Nhân sự',  TRUE),
    ('interviewer', 'Người phỏng vấn',    TRUE)
ON CONFLICT (name) DO NOTHING;

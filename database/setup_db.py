"""
Script setup DB đơn giản cho SmartCV Auto.
Drop tất cả → Tạo tables đúng thứ tự → Insert sample data → Tạo admin user.

Chạy (từ thư mục gốc): .\venv\Scripts\python database\setup_db.py

Login sau khi chạy:
    Email:    admin@smartcv.vn
    Password: admin123
"""
import asyncio
import asyncpg
import bcrypt
from datetime import date, datetime

def d(s): return date.fromisoformat(s) if s else None
def dt(s): return datetime.fromisoformat(s) if s else None

DB_URL = "postgresql://postgres:conmeonho2@localhost:5432/smartcv-auto"

# ── SQL TẠO BẢNG THEO ĐÚNG THỨ TỰ ────────────────────────────────────────
SETUP_SQL = """
-- ============ ENUM TYPES ============
CREATE TYPE gender_type AS ENUM ('male', 'female', 'other');
CREATE TYPE application_status AS ENUM (
    'mới', 'duyệt', 'từ chối', 'phỏng vấn', 'gửi offer', 'đã tuyển', 'bị từ chối'
);
CREATE TYPE interview_status AS ENUM ('scheduled', 'completed', 'cancelled');
CREATE TYPE interview_type AS ENUM ('online', 'offline');
CREATE TYPE job_status AS ENUM ('open', 'closed', 'paused');
CREATE TYPE experience_level AS ENUM ('intern', 'fresher', 'junior', 'mid', 'senior', 'lead', 'manager');

-- ============ BẢNG 1: roles ============
CREATE TABLE roles (
    name         VARCHAR(100) PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL,
    is_system    BOOLEAN      DEFAULT FALSE,
    created_at   TIMESTAMP    DEFAULT NOW()
);

-- ============ BẢNG 2: users ============
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

-- ============ BẢNG 3: role_permissions ============
CREATE TABLE role_permissions (
    role       VARCHAR(100) NOT NULL REFERENCES roles(name) ON DELETE CASCADE ON UPDATE CASCADE,
    resource   VARCHAR(100) NOT NULL,
    can_create BOOLEAN DEFAULT FALSE,
    can_read   BOOLEAN DEFAULT FALSE,
    can_update BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (role, resource)
);


-- ============ BẢNG 3: departments ============
CREATE TABLE departments (
    id         SERIAL       PRIMARY KEY,
    name       VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP    DEFAULT NOW()
);

-- ============ BẢNG 4: skills ============
CREATE TABLE skills (
    id         SERIAL       PRIMARY KEY,
    name       VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP    DEFAULT NOW()
);

-- ============ BẢNG 5: branches (chi nhánh công ty) ============
CREATE TABLE branches (
    id         SERIAL       PRIMARY KEY,
    name       VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP    DEFAULT NOW()
);

-- ============ BẢNG 6: jobs ============
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

-- ============ BẢNG 6: candidates ============
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

-- ============ BẢNG 7: candidate_links ============
CREATE TABLE candidate_links (
    id           SERIAL       PRIMARY KEY,
    candidate_id INT          NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    label        VARCHAR(100) NOT NULL,
    url          VARCHAR(500) NOT NULL,
    created_at   TIMESTAMP    DEFAULT NOW()
);

-- ============ BẢNG 8: candidate_education ============
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

-- ============ BẢNG 9: candidate_experience ============
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

-- ============ BẢNG 10: candidate_skills ============
CREATE TABLE candidate_skills (
    candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    skill_id     INT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (candidate_id, skill_id)
);

-- ============ BẢNG 11: candidate_notes ============
CREATE TABLE candidate_notes (
    id           SERIAL    PRIMARY KEY,
    candidate_id INT       NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    created_by   INT       NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    content      TEXT      NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW()
);

-- ============ BẢNG 12: job_skills ============
CREATE TABLE job_skills (
    job_id   INT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id INT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, skill_id)
);

-- ============ BẢNG 13: interviews ============
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

-- ============ BẢNG 15: system_settings ============
CREATE TABLE system_settings (
    key         VARCHAR(255) PRIMARY KEY,
    value       TEXT NOT NULL
);

-- ============ BẢNG 14: interview_interviewers ============
CREATE TABLE interview_interviewers (
    interview_id INT NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    user_id      INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (interview_id, user_id)
);

-- ============ INDEXES ============
CREATE INDEX idx_candidates_status    ON candidates(status);
CREATE INDEX idx_candidates_job_id    ON candidates(job_id);
CREATE INDEX idx_interviews_candidate ON interviews(candidate_id);
CREATE INDEX idx_interviews_status    ON interviews(status);

-- ============ DATA: departments ============
INSERT INTO departments (name) VALUES
    ('Engineering'), ('Design'), ('Marketing'), ('Sales'), ('HR & Admin');

-- ============ DATA: branches (chi nhánh công ty) ============
INSERT INTO branches (name) VALUES
    ('Hà Nội'), ('Hồ Chí Minh'), ('Đà Nẵng'), ('Cần Thơ');

-- ============ DATA: skills ============
INSERT INTO skills (name) VALUES
    ('Figma'), ('Adobe XD'), ('Photoshop'), ('Python'), ('JavaScript'),
    ('React'), ('Node.js'), ('SQL'), ('Excel'), ('Word'),
    ('Communication'), ('Leadership'), ('Project Management'), ('TypeScript'), ('Docker'),
    ('UI/UX Research');
"""




async def main():
    conn = await asyncpg.connect(DB_URL)
    try:
        # 1. Drop all
        print("1/4  Dropping existing tables...")
        await conn.execute("""
            DROP TABLE IF EXISTS
                system_settings,
                interview_interviewers, interviews,
                candidate_skills, candidate_notes, candidate_experience,
                candidate_education, candidate_links, candidates,
                job_skills, jobs, role_permissions, skills, branches, departments, users, roles
            CASCADE;
        """)
        for t in ["gender_type", "application_status",
                  "interview_status", "interview_type",
                  "job_status", "experience_level",
                  "user_role", "crud_resource"]:
            await conn.execute(f"DROP TYPE IF EXISTS {t} CASCADE;")
        print("     Done.")

        # 2. Create schema
        print("2/4  Creating tables...")
        await conn.execute(SETUP_SQL)
        print("     Done.")

        # 3. Seed roles hệ thống trước rồi mới tạo user
        print("3/4  Creating system roles & admin user...")
        await conn.execute("""
            INSERT INTO roles (name, display_name, is_system) VALUES
                ('admin',       'Quản trị viên',        TRUE),
                ('hr_staff',    'Chuyên viên Nhân sự',  TRUE),
                ('interviewer', 'Người phỏng vấn',    TRUE)
            ON CONFLICT (name) DO NOTHING;
        """)
        pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        await conn.execute("""
            INSERT INTO users (full_name, email, password_hash, role, is_active)
            VALUES ($1, $2, $3, 'admin', TRUE)
        """, "SmartCV Admin", "admin@smartcv.vn", pw_hash)
        print("     Done.")

        # 4. Sample data
        print("4/5  Inserting sample data...")
        H = "$2b$12$placeholder_do_not_use_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"  # placeholder pw

        # ── USERS (10 users tổng) ────────────────────────────────────────────
        users_raw = [
            ("Trần Thị Lan",      "lan.hr@acme.vn",       "hr_staff"),
            ("Nguyễn Minh Tuấn",  "tuan.hr@acme.vn",      "hr_staff"),
            ("Đỗ Thu Hà",         "ha.hr@acme.vn",         "hr_staff"),
            ("Phạm Thị Hoa",      "hoa.hr@acme.vn",       "hr_staff"),
            ("Lê Quốc Bảo",       "bao.dev@acme.vn",      "interviewer"),
            ("Vũ Thị Mai",        "mai.design@acme.vn",   "interviewer"),
            ("Trần Hùng Sơn",     "son.senior@acme.vn",   "interviewer"),
            ("Nguyễn Thị Linh",   "linh.ba@acme.vn",      "interviewer"),
            ("Hoàng Văn Khải",    "khai.tech@acme.vn",    "interviewer"),
        ]
        for full_name, email, role in users_raw:
            await conn.execute(
                "INSERT INTO users (full_name, email, password_hash, role) VALUES ($1,$2,$3,$4)",
                full_name, email, H, role)

        # ── ROLE PERMISSIONS ────────────────────────────────────────────────
        await conn.execute("""
            INSERT INTO role_permissions (role, resource, can_create, can_read, can_update, can_delete) VALUES
            ('admin',       'candidates',  TRUE,  TRUE,  TRUE,  TRUE),
            ('admin',       'jobs',        TRUE,  TRUE,  TRUE,  TRUE),
            ('admin',       'interviews',  TRUE,  TRUE,  TRUE,  TRUE),
            ('admin',       'users',       TRUE,  TRUE,  TRUE,  TRUE),
            ('admin',       'departments', TRUE,  TRUE,  TRUE,  TRUE),
            ('admin',       'skills',      TRUE,  TRUE,  TRUE,  TRUE),
            ('hr_staff',    'candidates',  TRUE,  TRUE,  TRUE,  TRUE),
            ('hr_staff',    'jobs',        TRUE,  TRUE,  TRUE,  FALSE),
            ('hr_staff',    'interviews',  TRUE,  TRUE,  TRUE,  FALSE),
            ('hr_staff',    'users',       FALSE, TRUE,  FALSE, FALSE),
            ('hr_staff',    'departments', FALSE, TRUE,  FALSE, FALSE),
            ('hr_staff',    'skills',      TRUE,  TRUE,  FALSE, FALSE),
            ('interviewer', 'candidates',  FALSE, TRUE,  FALSE, FALSE),
            ('interviewer', 'jobs',        FALSE, TRUE,  FALSE, FALSE),
            ('interviewer', 'interviews',  FALSE, TRUE,  TRUE,  FALSE),
            ('interviewer', 'users',       FALSE, FALSE, FALSE, FALSE),
            ('interviewer', 'departments', FALSE, FALSE, FALSE, FALSE),
            ('interviewer', 'skills',      FALSE, TRUE,  FALSE, FALSE)
            ON CONFLICT (role, resource) DO NOTHING;
        """)

        # ── LẤY IDs ─────────────────────────────────────────────────────────
        admin_id = await conn.fetchval("SELECT id FROM users WHERE email='admin@smartcv.vn'")

        dept_ids = {
            n: await conn.fetchval("SELECT id FROM departments WHERE name=$1", n)
            for n in ["Engineering", "Design", "Marketing", "Sales", "HR & Admin"]
        }
        branch_ids = {
            n: await conn.fetchval("SELECT id FROM branches WHERE name=$1", n)
            for n in ["Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Cần Thơ"]
        }

        # Insert thêm sample skills nếu chưa có đủ cho dữ liệu bên dưới
        extra_skills = ["FastAPI", "PostgreSQL", "Django", "Vue.js", "PHP", "Java", "Spring Boot",
                        "AWS", "Kubernetes", "Agile/Scrum", "Power BI", "SEO/SEM", "Google Ads",
                        "Negotiation", "Recruitment", "Canva"]
        for s in extra_skills:
            await conn.execute(
                "INSERT INTO skills (name) VALUES ($1) ON CONFLICT (name) DO NOTHING", s)

        skill_ids: dict = {
            n: await conn.fetchval("SELECT id FROM skills WHERE name=$1", n)
            for n in [
                "React", "TypeScript", "Vue.js", "JavaScript",
                "Python", "FastAPI", "Django", "PostgreSQL", "SQL",
                "Java", "Spring Boot", "PHP",
                "Figma", "Adobe XD", "Photoshop", "UI/UX Research", "Canva",
                "Docker", "AWS", "Kubernetes",
                "Agile/Scrum", "Power BI", "Project Management",
                "SEO/SEM", "Google Ads",
                "Communication", "Leadership", "Negotiation",
                "Recruitment", "Excel",
            ]
        }

        # ── JOBS (10 vị trí) ─────────────────────────────────────────────────
        # cột: title, dept, branch, exp, edu, qty, desc, req, benefits, status, min, max, skill_names
        jobs_data = [
            ("Frontend Developer (React)", "Engineering", "Hà Nội", "mid", "Đại học", 2,
             "Phát triển giao diện SaaS B2B phục vụ hàng chục nghìn người dùng.",
             "• Tối thiểu 2 năm React/TypeScript\n• Quen với REST API và GraphQL\n• Có kinh nghiệm tối ưu performance",
             "• Lương tháng 13\n• Bảo hiểm sức khỏe PVI\n• 15 ngày phép/năm",
             "open", 18_000_000, 28_000_000,
             ["React", "TypeScript", "JavaScript"]),

            ("Senior Backend Developer", "Engineering", "Hà Nội", "senior", "Đại học", 2,
             "Xây dựng và vận hành hệ thống microservices xử lý hàng triệu request/ngày.",
             "• 4+ năm Python (FastAPI/Django)\n• Thành thạo PostgreSQL, Redis\n• Kinh nghiệm Docker/Kubernetes",
             "• Lương thưởng cạnh tranh\n• Stock option\n• Flexible working hours",
             "open", 35_000_000, 55_000_000,
             ["Python", "FastAPI", "PostgreSQL", "Docker"]),

            ("UI/UX Designer", "Design", "Hồ Chí Minh", "junior", "Cao đẳng trở lên", 1,
             "Thiết kế trải nghiệm người dùng cho sản phẩm mobile & web B2B.",
             "• Thành thạo Figma, Prototyping\n• Portfolio ít nhất 3 dự án\n• Tư duy product-first",
             "• Môi trường sáng tạo\n• Ngân sách học công cụ\n• Team trẻ, năng động",
             "open", 12_000_000, 18_000_000,
             ["Figma", "Adobe XD", "UI/UX Research"]),

            ("Graphic Designer", "Design", "Đà Nẵng", "fresher", "Cao đẳng trở lên", 2,
             "Thiết kế ấn phẩm truyền thông, banner quảng cáo và nội dung mạng xã hội.",
             "• Thành thạo Photoshop, Illustrator, Canva\n• Có portfolio thiết kế\n• Sáng tạo, tỉ mỉ",
             "• Hỗ trợ ăn trưa\n• Cơ hội thăng tiến rõ ràng",
             "open", 8_000_000, 12_000_000,
             ["Photoshop", "Adobe XD", "Canva"]),

            ("Marketing Specialist", "Marketing", "Hồ Chí Minh", "mid", "Đại học", 2,
             "Lên kế hoạch và triển khai chiến lược marketing đa kênh cho sản phẩm SaaS.",
             "• 2+ năm digital marketing\n• Kinh nghiệm SEO, Google Ads, Facebook Ads\n• Biết phân tích số liệu (GA4, Power BI)",
             "• KPI thưởng theo hiệu quả\n• Ngân sách quảng cáo để tự thử nghiệm",
             "open", 15_000_000, 22_000_000,
             ["SEO/SEM", "Google Ads", "Power BI"]),

            ("Product Manager", "Engineering", "Hà Nội", "senior", "Đại học", 1,
             "Định hướng và dẫn dắt phát triển sản phẩm từ ý tưởng đến ra mắt thị trường.",
             "• 3+ năm PM tại công ty phần mềm\n• Sử dụng Jira/Confluence\n• Tư duy dữ liệu, thiên về kỹ thuật",
             "• Lương thương lượng\n• Quyền quyết định roadmap",
             "open", 40_000_000, 60_000_000,
             ["Agile/Scrum", "Project Management", "SQL"]),

            ("Sales Executive", "Sales", "Cần Thơ", "junior", "Cao đẳng trở lên", 3,
             "Tìm kiếm và phát triển khách hàng doanh nghiệp vừa và nhỏ tại khu vực miền Tây.",
             "• Kỹ năng thuyết trình, đàm phán tốt\n• Có mạng lưới B2B là lợi thế",
             "• Lương cứng + hoa hồng không giới hạn\n• Xe công ty",
             "open", 10_000_000, 15_000_000,
             ["Negotiation", "Communication"]),

            ("Java Developer", "Engineering", "Hồ Chí Minh", "mid", "Đại học", 2,
             "Phát triển tính năng mới cho hệ thống ERP phục vụ khối ngân hàng.",
             "• 2+ năm Java/Spring Boot\n• Kinh nghiệm Oracle/PostgreSQL\n• Hiểu biết về tích hợp API banking",
             "• Phụ cấp chứng chỉ kỹ thuật\n• Làm việc hybrid",
             "open", 22_000_000, 35_000_000,
             ["Java", "Spring Boot", "PostgreSQL", "SQL"]),

            ("HR Specialist (Tuyển dụng)", "HR & Admin", "Hà Nội", "mid", "Đại học", 1,
             "Phụ trách toàn bộ quy trình tuyển dụng từ đăng tin đến onboarding nhân viên.",
             "• 2+ năm tuyển dụng IT/Tech\n• Thành thạo các kênh tuyển dụng\n• Kỹ năng phỏng vấn hành vi",
             "• Môi trường chuyên nghiệp\n• Đào tạo bài bản",
             "open", 13_000_000, 18_000_000,
             ["Recruitment", "Communication", "Excel"]),

            ("DevOps Engineer", "Engineering", "Đà Nẵng", "senior", "Đại học", 1,
             "Xây dựng và vận hành CI/CD pipeline, hạ tầng đám mây cho toàn bộ sản phẩm.",
             "• 3+ năm DevOps/SRE\n• Thành thạo AWS/GCP, Kubernetes\n• Kinh nghiệm Terraform, Helm",
             "• Remote-first\n• Budget học tập $1000/năm",
             "closed", 30_000_000, 45_000_000,
             ["AWS", "Kubernetes", "Docker"]),
        ]

        job_ids: dict = {}
        for title, dept, branch, exp, edu, qty, desc, req, benefits, status, mn, mx, jskills in jobs_data:
            jid = await conn.fetchval(
                "INSERT INTO jobs (title, department_id, branch_id, experience_level, education_level, quantity, "
                "description, requirements, benefits, status, salary_min, salary_max, created_by) "
                "VALUES ($1,$2,$3,$4::experience_level,$5,$6,$7,$8,$9,$10::job_status,$11,$12,$13) RETURNING id",
                title, dept_ids[dept], branch_ids[branch], exp, edu, qty,
                desc, req, benefits, status, mn, mx, admin_id
            )
            job_ids[title] = jid
            for sn in jskills:
                sid = skill_ids.get(sn)
                if sid:
                    await conn.execute(
                        "INSERT INTO job_skills (job_id, skill_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                        jid, sid)

        # ── CANDIDATES (22 ứng viên tổng) ────────────────────────────────────
        # cột: full_name, dob, gender, phone, email, fb, zalo, province_code, district_code, ward_code,
        #      specific_address, job_title, cv_link, portfolio_link, ai_summary, score, status, applied_date
        candidates_raw = [
            ("Nguyễn Thành Long", d("1998-04-12"), "male", "0912345678", "long.dev@gmail.com",
             "fb.com/thanh.long", "0912345678", "79", "760", "26734",
             "45 Đinh Tiên Hoàng, Q.1, TP.HCM",
             "Frontend Developer (React)", "https://drive.google.com/cv_long", "https://github.com/nglong98",
             "Ứng viên có kỹ năng React tốt, tư duy logic mạnh, phù hợp với vị trí Frontend Mid-level.",
             7.5, "phỏng vấn", d("2026-01-15")),

            ("Phạm Ngọc Ánh", d("2000-08-25"), "female", "0971234567", "anh.designer@gmail.com",
             None, "0971234567", "48", "485", "19186",
             "12 Lê Duẩn, Q.Hải Châu, Đà Nẵng",
             "UI/UX Designer", "https://drive.google.com/cv_anh", "https://behance.net/ngocanhdesign",
             "Thiết kế sáng tạo, hiểu sâu về trải nghiệm người dùng, portfolio ấn tượng.",
             8.2, "duyệt", d("2026-01-20")),

            ("Lê Văn Dũng", d("1995-11-03"), "male", "0933456789", "dung.backend@gmail.com",
             "fb.com/dungle", "0933456789", "01", "001", "00001",
             "78 Trần Hưng Đạo, Hoàn Kiếm, Hà Nội",
             "Senior Backend Developer", "https://drive.google.com/cv_dung", "https://github.com/dunglt95",
             "Chuyên gia Backend với kinh nghiệm xử lý hệ thống tải cao, thành thạo Python và kiến trúc Microservices.",
             8.8, "phỏng vấn", d("2026-01-10")),

            ("Trần Thị Bích", d("1999-03-17"), "female", "0988765432", "bich.tran@gmail.com",
             None, "0988765432", "79", "765", "26995",
             "99 Nguyễn Hữu Thọ, Q.7, TP.HCM",
             "Marketing Specialist", "https://drive.google.com/cv_bich", None,
             "Kỹ năng Digital Marketing tốt, nắm bắt nhanh các xu hướng thị trường.",
             7.0, "mới", d("2026-02-01")),

            ("Hoàng Văn Tùng", d("1997-06-22"), "male", "0905123456", "tung.java@gmail.com",
             "fb.com/tung.hv", "0905123456", "79", "770", "27151",
             "23 Phạm Văn Đồng, Thủ Đức, TP.HCM",
             "Java Developer", "https://drive.google.com/cv_tung", "https://github.com/hoangtung97",
             "Lập trình viên Java chắc chắn, kinh nghiệm làm việc với các hệ thống tài chính/ngân hàng.",
             8.5, "duyệt", d("2026-01-28")),

            ("Vũ Thị Hương", d("2001-12-07"), "female", "0977654321", "huong.designer@gmail.com",
             None, "0977654321", "48", "490", "19261",
             "5 Hoàng Diệu, Q.Hải Châu, Đà Nẵng",
             "Graphic Designer", "https://drive.google.com/cv_huong", "https://behance.net/vuhuong",
             "Sáng tạo, sử dụng thành thạo bộ công cụ Adobe, thái độ chuyên nghiệp.",
             7.8, "mới", d("2026-02-10")),

            ("Ngô Trọng Nghĩa", d("1996-09-14"), "male", "0916789012", "nghia.devops@gmail.com",
             "fb.com/nghia.ngo", "0916789012", "01", "005", "00187",
             "34 Xuân Thủy, Cầu Giấy, Hà Nội",
             "DevOps Engineer", "https://drive.google.com/cv_nghia", "https://github.com/tnghia96",
             "Kinh nghiệm dày dặn về Cloud (AWS/Azure) và CI/CD, tự động hóa hạ tầng tốt.",
             9.0, "gửi offer", d("2025-12-20")),

            ("Bùi Phương Thảo", d("2000-05-30"), "female", "0962345678", "thao.bui@gmail.com",
             None, "0962345678", "92", "916", "31171",
             "8 Lý Thường Kiệt, Ninh Kiều, Cần Thơ",
             "Sales Executive", "https://drive.google.com/cv_thao", None,
             "Giao tiếp tốt, nhanh nhẹn, có tiềm năng phát triển trong mảng kinh doanh doanh nghiệp.",
             6.5, "mới", d("2026-02-05")),

            ("Đinh Quốc Huy", d("1994-02-19"), "male", "0945678901", "huy.pm@gmail.com",
             "fb.com/huydq94", "0945678901", "01", "001", "00031",
             "112 Nguyễn Chí Thanh, Đống Đa, Hà Nội",
             "Product Manager", "https://drive.google.com/cv_huy", "https://linkedin.com/in/dinhquochuy",
             "Mindset hướng sản phẩm rất tốt, khả năng quản lý dự án và dẫn dắt team hiệu quả.",
             9.2, "phỏng vấn", d("2026-01-05")),

            ("Lý Ngọc Phương", d("2002-10-11"), "female", "0935789012", "phuong.ly@gmail.com",
             None, "0935789012", "79", "760", "26728",
             "67 Đồng Khởi, Q.1, TP.HCM",
             "Marketing Specialist", "https://drive.google.com/cv_phuong", None,
             "Ứng viên trẻ, năng động, chưa có nhiều kinh nghiệm nhưng ham học hỏi.",
             7.3, "từ chối", d("2026-01-18")),

            ("Trần Đăng Khoa", d("1998-07-05"), "male", "0908234567", "khoa.react@gmail.com",
             "fb.com/khoa.td98", "0908234567", "01", "006", "00214",
             "55 Cầu Giấy, Cầu Giấy, Hà Nội",
             "Frontend Developer (React)", "https://drive.google.com/cv_khoa", "https://github.com/khoatd98",
             "Nắm vững React và hệ sinh thái liên quan, có kinh nghiệm thực chiến tốt.",
             8.0, "duyệt", d("2026-02-15")),

            ("Phan Minh Khải", d("1993-01-29"), "male", "0921456789", "khai.java@gmail.com",
             "fb.com/khaiphan93", "0921456789", "79", "774", "27370",
             "200 Điện Biên Phủ, Bình Thạnh, TP.HCM",
             "Java Developer", "https://drive.google.com/cv_khai", "https://linkedin.com/in/phanminhkhai",
             "Lập trình viên Java Senior với nền tảng kiến thức vững chắc và kinh nghiệm đào tạo fresher.",
             8.6, "đã tuyển", d("2025-11-30")),

            # ── 10 Ứng viên mới ──
            ("Đỗ Hùng Dũng", d("1995-01-01"), "male", "0900111222", "dung.do@gmail.com",
             "fb.com/dungdo", "0900111222", "01", "001", "00010",
             "Số 1 Kim Mã, Ba Đình, Hà Nội",
             "Senior Backend Developer", "https://drive.google.com/cv_dungdo", None,
             "Kỹ năng backend chuyên sâu, giải quyết vấn đề tốt.",
             8.9, "mới", d("2025-11-20")),

            ("Nguyễn Hoàng Đức", d("1998-02-02"), "male", "0900333444", "duc.nh@gmail.com",
             "fb.com/hoangduc", "0900333444", "48", "485", "19190",
             "23 Hùng Vương, Q.Hải Châu, Đà Nẵng",
             "Java Developer", "https://drive.google.com/cv_ducnh", "https://github.com/hoangduc98",
             "Làm việc có trách nhiệm, nắm bắt technology stack nhanh.",
             8.4, "duyệt", d("2025-12-05")),

            ("Quế Ngọc Hải", d("1993-03-03"), "male", "0900555666", "hai.qn@gmail.com",
             None, "0900555666", "79", "760", "26730",
             "102 Lê Lợi, Q.1, TP.HCM",
             "Product Manager", "https://drive.google.com/cv_haiqn", None,
             "Kinh nghiệm PM dày dặn, giao tiếp và quản trị đội ngũ xuất sắc.",
             9.1, "phỏng vấn", d("2025-12-15")),

            ("Đoàn Văn Hậu", d("1999-04-04"), "male", "0900777888", "hau.dv@gmail.com",
             "fb.com/vanhau", "0900777888", "01", "002", "00100",
             "50 Phố Huế, Hai Bà Trưng, Hà Nội",
             "DevOps Engineer", "https://drive.google.com/cv_vanhau", "https://github.com/vanhau99",
             "Yêu thích vọc vạch công nghệ mới, phù hợp môi trường startup.",
             7.9, "mới", d("2026-01-02")),

            ("Nguyễn Công Phượng", d("1995-05-05"), "male", "0900999000", "phuong.nc@gmail.com",
             "fb.com/congphuong", "0900999000", "79", "761", "26740",
             "75 Ba Tháng Hai, Q.10, TP.HCM",
             "Frontend Developer (React)", "https://drive.google.com/cv_phuongnc", None,
             "Có gu thẩm mỹ trong UI, kỹ năng React cứng.",
             8.3, "duyệt", d("2026-01-10")),

            ("Lương Xuân Trường", d("1995-06-06"), "male", "0901111222", "truong.lx@gmail.com",
             None, "0901111222", "92", "916", "31180",
             "15 Hòa Bình, Ninh Kiều, Cần Thơ",
             "Marketing Specialist", "https://drive.google.com/cv_truonglx", None,
             "Kỹ năng copy-writing và quản lý fanpage ổn.",
             7.2, "từ chối", d("2026-02-20")),

            ("Nguyễn Tuấn Anh", d("1995-07-07"), "male", "0901333444", "anh.nt@gmail.com",
             "fb.com/tuananh", "0901333444", "01", "005", "00190",
             "12 Phan Văn Trường, Cầu Giấy, Hà Nội",
             "Java Developer", "https://drive.google.com/cv_tuananh", "https://github.com/tuananh95",
             "Tính cách hòa đồng, kỹ năng giải thuật tốt.",
             8.1, "mới", d("2026-02-28")),

            ("Nguyễn Quang Hải", d("1997-08-08"), "male", "0901555666", "hai.nq@gmail.com",
             None, "0901555666", "01", "001", "00020",
             "Phố cổ Hà Nội",
             "UI/UX Designer", "https://drive.google.com/cv_quanghai", "https://behance.net/quanghai",
             "Tư duy thiết kế vượt trội, nhiều ý tưởng đột phá.",
             9.3, "gửi offer", d("2026-03-01")),

            ("Nguyễn Tiến Linh", d("1997-09-09"), "male", "0901777888", "linh.nt@gmail.com",
             "fb.com/tienlinh", "0901777888", "79", "765", "27000",
             "Phú Mỹ Hưng, Q.7, TP.HCM",
             "Sales Executive", "https://drive.google.com/cv_tienlinh", None,
             "Kỹ năng chốt đơn mạnh mẽ, cực kỳ xông xáo.",
             7.7, "duyệt", d("2026-03-05")),

            ("Phan Văn Đức", d("1996-10-10"), "male", "0901999000", "duc.pv@gmail.com",
             None, "0901999000", "48", "490", "19270",
             "Biển Mỹ Khê, Đà Nẵng",
             "Graphic Designer", "https://drive.google.com/cv_phanduc", "https://behance.net/phanduc",
             "Thiết kế trẻ trung, phù hợp với gen Z.",
             8.0, "mới", d("2026-03-08")),
        ]

        cand_ids: dict = {}
        hr_id = await conn.fetchval("SELECT id FROM users WHERE email='lan.hr@acme.vn'")

        for (full_name, dob, gender, phone, email, fb, zalo, prov, dist, ward,
             addr, job_title, cv_link, portfolio, ai_sum, score, status, applied_date) in candidates_raw:
            job_id = job_ids.get(job_title)
            cid = await conn.fetchval(
                "INSERT INTO candidates (full_name, date_of_birth, gender, phone, email, "
                "facebook, zalo, specific_address, "
                "job_id, cv_link, portfolio_link, ai_summary, score, status, applied_date, created_by) "
                "VALUES ($1,$2,$3::gender_type,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17::application_status,$18,$19) RETURNING id",
                full_name, dob, gender, phone, email, fb, zalo, prov, dist, ward, addr,
                job_id, cv_link, portfolio, ai_sum, score, status, applied_date, hr_id
            )
            cand_ids[full_name] = cid

        # ── CANDIDATE EDUCATION ───────────────────────────────────────────────
        edu_data = [
            ("Nguyễn Thành Long",  "Cử nhân", "Đại học Bách Khoa TP.HCM",   "Công nghệ thông tin", 2017, 2021),
            ("Lê Văn Dũng",        "Cử nhân", "Đại học KHTN Hà Nội",         "Khoa học máy tính",   2014, 2018),
            ("Hoàng Văn Tùng",     "Cử nhân", "Đại học Sài Gòn",              "Kỹ thuật phần mềm",  2016, 2020),
            ("Phạm Ngọc Ánh",      "Cao đẳng","Cao đẳng FPT Polytechnic",     "Thiết kế đồ họa",     2018, 2020),
            ("Vũ Thị Hương",       "Cao đẳng","Cao đẳng Nghề Đà Nẵng",        "Thiết kế mỹ thuật",  2019, 2022),
            ("Ngô Trọng Nghĩa",   "Cử nhân", "Đại học Công Nghệ - ĐHQG",    "Mạng máy tính",       2015, 2019),
            ("Đinh Quốc Huy",     "Thạc sĩ", "Đại học Kinh tế Quốc dân",    "Quản trị kinh doanh", 2013, 2017),
            ("Đinh Quốc Huy",     "Cử nhân", "Đại học Bách Khoa Hà Nội",    "Công nghệ thông tin", 2009, 2013),
            ("Trần Đăng Khoa",    "Cử nhân", "Đại học FPT",                  "Kỹ thuật phần mềm",  2017, 2021),
            ("Phan Minh Khải",    "Cử nhân", "Đại học Khoa học Tự nhiên",   "Hệ thống thông tin",  2012, 2016),
            ("Trần Thị Bích",     "Cử nhân", "Đại học Kinh tế TP.HCM",      "Marketing",           2017, 2021),
            ("Bùi Phương Thảo",   "Cao đẳng","Cao đẳng Cần Thơ",             "Kinh doanh",          2018, 2021),
            ("Đỗ Hùng Dũng",      "Cử nhân", "Đại học Bách Khoa Hà Nội",    "Công nghệ thông tin", 2013, 2017),
            ("Nguyễn Hoàng Đức",  "Cử nhân", "Đại học Sư phạm Kỹ thuật",     "Tự động hóa",        2016, 2020),
            ("Quế Ngọc Hải",      "Cử nhân", "Đại học Vinh",                  "Quản trị kinh doanh", 2011, 2015),
            ("Đoàn Văn Hậu",      "Cao đẳng","PVF Academy",                   "Thể thao chuyên nghiệp", 2015, 2017),
            ("Nguyễn Công Phượng", "Cử nhân", "Đại học HAGL JMG",              "Kỹ thuật bóng đá",    2010, 2014),
            ("Lương Xuân Trường", "Cử nhân", "Đại học Thể dục Thể thao",      "Quản lý thể thao",    2013, 2017),
            ("Nguyễn Tuấn Anh",   "Cử nhân", "Đại học HAGL JMG",              "Kỹ thuật phần mềm",   2013, 2017),
            ("Nguyễn Quang Hải",  "Cử nhân", "Đại học Mỹ thuật Công nghiệp", "Thiết kế đồ họa",      2015, 2019),
            ("Nguyễn Tiến Linh",  "Cử nhân", "Đại học Bình Dương",            "Quản trị kinh doanh", 2015, 2019),
            ("Phan Văn Đức",      "Cao đẳng","Cao đẳng Nghệ An",              "Mỹ thuật ứng dụng",   2014, 2017),
        ]
        for cname, degree, inst, major, sy, ey in edu_data:
            cid = cand_ids.get(cname)
            if cid:
                await conn.execute(
                    "INSERT INTO candidate_education (candidate_id, degree, institution, major, start_year, end_year) "
                    "VALUES ($1,$2,$3,$4,$5,$6)",
                    cid, degree, inst, major, sy, ey)

        # ── CANDIDATE EXPERIENCE ──────────────────────────────────────────────
        exp_data = [
            ("Nguyễn Thành Long", "MoMo",                 "Frontend Developer", d("2021-07-01"), d("2024-01-31"),
             "Phát triển mini-app tích hợp trong siêu ứng dụng MoMo. Stack: React, TypeScript, GraphQL."),
            ("Nguyễn Thành Long", "Startup GreenBiz",      "Intern Frontend",    d("2021-01-01"), d("2021-06-30"),
             "Làm giao diện landing page và dashboard quản lý bằng ReactJS."),
            ("Lê Văn Dũng",      "VNG Corporation",        "Backend Developer",  d("2018-09-01"), d("2024-06-30"),
             "Xây dựng service xử lý thanh toán, đạt 50,000 req/s. Stack: Python (FastAPI), Redis, Kafka."),
            ("Hoàng Văn Tùng",   "FPT Software",           "Java Developer",     d("2020-06-01"), d("2024-08-31"),
             "Phát triển module quản lý nhân sự và phiếu lương trên hệ thống ERP nội bộ."),
            ("Ngô Trọng Nghĩa",  "CMC Global",             "DevOps Engineer",    d("2019-01-01"), d("2024-12-31"),
             "Quản lý 200+ EC2 instances trên AWS, triển khai Kubernetes cluster phục vụ 30 microservices."),
            ("Đinh Quốc Huy",    "KMS Technology",         "Senior PM",          d("2018-03-01"), d("2024-11-30"),
             "Dẫn dắt team 15 người, ra mắt 3 sản phẩm B2B SaaS. Áp dụng OKR và Agile Scrum."),
            ("Đinh Quốc Huy",    "Logigear Vietnam",       "Junior PM",          d("2015-06-01"), d("2018-02-28"),
             "Hỗ trợ PM cấp cao trong việc thu thập yêu cầu và theo dõi sprint."),
            ("Trần Đăng Khoa",   "Tiki Corporation",       "Frontend Developer", d("2021-06-01"), d("2025-12-31"),
             "Xây dựng storefront cho Tiki Next dùng Next.js + TypeScript, tối ưu Core Web Vitals."),
            ("Phan Minh Khải",   "Techcombank",            "Java Developer",     d("2016-08-01"), d("2025-11-30"),
             "Phát triển module giao dịch chuyển khoản, tích hợp Napas và VN Pay. Spring Boot + Oracle."),
            ("Phạm Ngọc Ánh",   "Freelance",               "UI/UX Designer",     d("2021-01-01"), d("2024-09-30"),
             "Thiết kế UI cho 12 ứng dụng mobile và web. Dùng Figma, Principle để prototype."),
            ("Trần Thị Bích",   "Anymind Group",           "Marketing Exec",     d("2021-06-01"), d("2024-12-31"),
             "Quản lý ngân sách quảng cáo $20k/tháng trên Meta Ads và Google Ads."),
            ("Đỗ Hùng Dũng",    "Viettel Solutions",       "Senior Backend",     d("2017-09-01"), d("2025-11-15"),
             "Trưởng nhóm phát triển hệ thống lõi cho dự án Chính phủ số."),
            ("Nguyễn Hoàng Đức", "FPT Software",           "Java Developer",      d("2020-08-01"), d("2025-12-01"),
             "Phát triển microservices hỗ trợ cho các đối tác Nhật Bản bằng Java Spring Boot."),
            ("Quế Ngọc Hải",    "Viettel Post",            "Operations Manager", d("2015-10-01"), d("2025-12-10"),
             "Điều phối vận hành bưu chính toàn quốc, tối ưu hóa quy trình giao vận."),
            ("Đoàn Văn Hậu",    "Heerenveen (NL)",         "DevOps Engineer",    d("2019-09-01"), d("2020-08-31"),
             "Học hỏi và áp dụng quy trình CI/CD chuẩn Châu Âu tại CLB."),
            ("Nguyễn Công Phượng", "Sint-Truiden (BE)",     "Frontend Developer", d("2019-07-01"), d("2020-01-31"),
             "Thực tập và làm việc trong môi trường quốc tế về UI/UX Frontend."),
            ("Nguyễn Quang Hải",  "Pau FC (FR)",           "UI/UX Designer",     d("2022-07-01"), d("2023-06-30"),
             "Thiết kế lại trải nghiệm người dùng cho ứng dụng quản lý fan hâm mộ."),
            ("Nguyễn Tiến Linh",  "Bình Dương FC",         "Sales Executive",    d("2016-01-01"), d("2026-03-01"),
             "Phát triển thị trường đồ dùng thể thao tại khu vực phía Nam."),
        ]
        for cname, company, pos, sd, ed, desc in exp_data:
            cid = cand_ids.get(cname)
            if cid:
                await conn.execute(
                    "INSERT INTO candidate_experience (candidate_id, company_name, position, start_date, end_date, description) "
                    "VALUES ($1,$2,$3,$4,$5,$6)",
                    cid, company, pos, sd, ed, desc)

        # ── CANDIDATE SKILLS ─────────────────────────────────────────────────
        cand_skill_map = {
            "Nguyễn Thành Long": ["React", "TypeScript", "JavaScript"],
            "Lê Văn Dũng":       ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "Hoàng Văn Tùng":    ["Java", "Spring Boot", "PostgreSQL", "SQL"],
            "Phạm Ngọc Ánh":    ["Figma", "Adobe XD", "UI/UX Research"],
            "Vũ Thị Hương":     ["Photoshop", "Canva", "Adobe XD"],
            "Ngô Trọng Nghĩa":  ["AWS", "Kubernetes", "Docker"],
            "Đinh Quốc Huy":    ["Agile/Scrum", "Project Management", "SQL"],
            "Trần Thị Bích":    ["SEO/SEM", "Google Ads", "Excel"],
            "Bùi Phương Thảo":  ["Communication", "Negotiation"],
            "Trần Đăng Khoa":   ["React", "TypeScript", "JavaScript", "Vue.js"],
            "Phan Minh Khải":   ["Java", "Spring Boot", "SQL", "PostgreSQL"],
            "Lý Ngọc Phương":   ["Google Ads", "SEO/SEM", "Power BI"],
            "Đỗ Hùng Dũng":     ["Python", "FastAPI", "SQL", "Docker"],
            "Nguyễn Hoàng Đức": ["Java", "Spring Boot", "PostgreSQL"],
            "Quế Ngọc Hải":     ["Project Management", "Agile/Scrum", "Communication"],
            "Đoàn Văn Hậu":     ["AWS", "Kubernetes", "Docker", "Python"],
            "Nguyễn Công Phượng": ["React", "TypeScript", "JavaScript"],
            "Lương Xuân Trường": ["Google Ads", "SEO/SEM", "Project Management"],
            "Nguyễn Tuấn Anh":   ["Java", "SQL", "Spring Boot", "React"],
            "Nguyễn Quang Hải":  ["Figma", "Adobe XD", "UI/UX Research"],
            "Nguyễn Tiến Linh":  ["Negotiation", "Communication"],
            "Phan Văn Đức":      ["Photoshop", "Canva", "Adobe XD"],
        }
        for cname, skills_list in cand_skill_map.items():
            cid = cand_ids.get(cname)
            if cid:
                for sn in skills_list:
                    sid = skill_ids.get(sn)
                    if sid:
                        await conn.execute(
                            "INSERT INTO candidate_skills (candidate_id, skill_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                            cid, sid)

        # ── CANDIDATE LINKS ───────────────────────────────────────────────────
        link_data = [
            ("Nguyễn Thành Long",  "GitHub",   "https://github.com/nglong98"),
            ("Nguyễn Thành Long",  "LinkedIn", "https://linkedin.com/in/ngthanhlong"),
            ("Lê Văn Dũng",        "GitHub",   "https://github.com/dunglt95"),
            ("Lê Văn Dũng",        "LinkedIn", "https://linkedin.com/in/levandung95"),
            ("Hoàng Văn Tùng",     "GitHub",   "https://github.com/hoangtung97"),
            ("Phạm Ngọc Ánh",     "Behance",  "https://behance.net/ngocanhdesign"),
            ("Vũ Thị Hương",       "Behance",  "https://behance.net/vuhuong"),
            ("Ngô Trọng Nghĩa",   "GitHub",   "https://github.com/tnghia96"),
            ("Ngô Trọng Nghĩa",   "LinkedIn", "https://linkedin.com/in/ngotrongnghia"),
            ("Đinh Quốc Huy",     "LinkedIn", "https://linkedin.com/in/dinhquochuy"),
            ("Trần Đăng Khoa",    "GitHub",   "https://github.com/khoatd98"),
            ("Phan Minh Khải",    "LinkedIn", "https://linkedin.com/in/phanminhkhai"),
            ("Đỗ Hùng Dũng",      "LinkedIn", "https://linkedin.com/in/dohungdung"),
            ("Nguyễn Hoàng Đức",  "GitHub",   "https://github.com/ducnh98"),
            ("Đoàn Văn Hậu",      "GitHub",   "https://github.com/vanhau99"),
            ("Nguyễn Công Phượng","LinkedIn", "https://linkedin.com/in/congphuong"),
            ("Nguyễn Quang Hải",  "Behance",  "https://behance.net/quanghai19"),
            ("Nguyễn Tiến Linh",  "LinkedIn", "https://linkedin.com/in/tienlinh"),
        ]
        for cname, label, url in link_data:
            cid = cand_ids.get(cname)
            if cid:
                await conn.execute(
                    "INSERT INTO candidate_links (candidate_id, label, url) VALUES ($1,$2,$3)",
                    cid, label, url)

        # ── CANDIDATE NOTES ───────────────────────────────────────────────────
        note_data = [
            ("Nguyễn Thành Long",  "Ứng viên có code test tốt, logic rõ ràng. Cần kiểm tra thêm kỹ năng system design."),
            ("Lê Văn Dũng",        "Kiến thức backend rất chắc. Budget kỳ vọng 45–50tr. Đang trong giai đoạn offer."),
            ("Phạm Ngọc Ánh",     "Portfolio đẹp và đúng phong cách brand. Cần test thêm về user research."),
            ("Hoàng Văn Tùng",     "Có kinh nghiệm banking domain — phù hợp dự án Java ERP. Đặt lịch vòng 2."),
            ("Ngô Trọng Nghĩa",   "Rất xuất sắc, kinh nghiệm AWS/Kubernetes thực chiến. Đã gửi offer, chờ phản hồi."),
            ("Đinh Quốc Huy",     "PM lâu năm, mindset dữ liệu tốt. Phù hợp vị trí leadership level."),
            ("Đỗ Hùng Dũng",      "Ứng viên chuyên môn cực tốt, tinh thần kỷ luật cao."),
            ("Nguyễn Hoàng Đức",  "Kỹ năng Java rất sáng, tư duy nhanh nhạy."),
            ("Quế Ngọc Hải",      "Khả năng lãnh đạo và quản lý vận hành tốt."),
            ("Nguyễn Quang Hải",  "Sáng tạo đột phá, portfolio đẳng cấp."),
            ("Trần Đăng Khoa",    "React skills tốt, đã làm Next.js ở Tiki. Hẹn phỏng vấn vòng technical tuần sau."),
        ]
        for cname, content in note_data:
            cid = cand_ids.get(cname)
            if cid:
                await conn.execute(
                    "INSERT INTO candidate_notes (candidate_id, created_by, content) VALUES ($1,$2,$3)",
                    cid, hr_id, content)

        # ── INTERVIEWS (8 lịch phỏng vấn) ────────────────────────────────────
        int_user_ids = {
            "bao":   await conn.fetchval("SELECT id FROM users WHERE email='bao.dev@acme.vn'"),
            "mai":   await conn.fetchval("SELECT id FROM users WHERE email='mai.design@acme.vn'"),
            "son":   await conn.fetchval("SELECT id FROM users WHERE email='son.senior@acme.vn'"),
            "linh":  await conn.fetchval("SELECT id FROM users WHERE email='linh.ba@acme.vn'"),
            "khai":  await conn.fetchval("SELECT id FROM users WHERE email='khai.tech@acme.vn'"),
        }

        # cột: candidate, sched_at, end_at, type, loc/link, status, created_by, interviewers
        interviews_raw = [
            ("Nguyễn Thành Long", "2026-02-20 09:00", "2026-02-20 10:00",
             "online", None, "https://meet.google.com/abc-1234", "completed",
             admin_id, ["bao", "son"]),

            ("Nguyễn Thành Long", "2026-02-28 14:00", "2026-02-28 15:30",
             "offline", "Văn phòng Hà Nội - Tầng 7", None, "completed",
             hr_id, ["linh"]),

            ("Lê Văn Dũng", "2026-02-18 10:30", "2026-02-18 11:30",
             "online", None, "https://meet.google.com/def-5678", "completed",
             admin_id, ["son", "khai"]),

            ("Hoàng Văn Tùng", "2026-03-05 09:00", "2026-03-05 10:00",
             "online", None, "https://meet.google.com/ghi-9012", "completed",
             hr_id, ["khai"]),

            ("Phạm Ngọc Ánh", "2026-03-12 15:00", "2026-03-12 16:00",
             "offline", "Văn phòng HCM - Tầng 3", None, "scheduled",
             hr_id, ["mai"]),

            ("Đinh Quốc Huy", "2026-03-10 09:00", "2026-03-10 10:30",
             "online", None, "https://teams.microsoft.com/l/xyz", "completed",
             admin_id, ["linh", "bao"]),

            ("Trần Đăng Khoa", "2026-03-18 14:00", "2026-03-18 15:00",
             "online", None, "https://meet.google.com/jkl-3456", "scheduled",
             hr_id, ["bao", "son"]),

            ("Ngô Trọng Nghĩa", "2026-01-25 10:00", "2026-01-25 11:30",
             "offline", "Văn phòng HN - Tầng 7", None, "completed",
             admin_id, ["khai", "son"]),
        ]

        for (cname, sched, end_at, itype, loc, olink, istatus,
             created_by, inter_keys) in interviews_raw:
            cid = cand_ids.get(cname)
            if not cid:
                continue
            interview_id = await conn.fetchval(
                "INSERT INTO interviews (candidate_id, scheduled_at, end_at, interview_type, "
                "location, online_link, status, created_by) "
                "VALUES ($1,$2,$3,$4::interview_type,$5,$6,$7::interview_status,$8) RETURNING id",
                cid, dt(sched), dt(end_at), itype, loc, olink, istatus, created_by
            )
            for key in inter_keys:
                uid = int_user_ids.get(key)
                if uid:
                    await conn.execute(
                        "INSERT INTO interview_interviewers (interview_id, user_id) "
                        "VALUES ($1,$2) ON CONFLICT DO NOTHING",
                        interview_id, uid)

        print("     Done.")

        # Summary
        users_count      = await conn.fetchval("SELECT COUNT(*) FROM users")
        jobs_count       = await conn.fetchval("SELECT COUNT(*) FROM jobs")
        candidates_count = await conn.fetchval("SELECT COUNT(*) FROM candidates")
        interviews_count = await conn.fetchval("SELECT COUNT(*) FROM interviews")
        branches_count   = await conn.fetchval("SELECT COUNT(*) FROM branches")
        print(f"""
========================================
  Database setup COMPLETE!
========================================
  Users:       {users_count}
  Branches:    {branches_count}
  Jobs:        {jobs_count}
  Candidates:  {candidates_count}
  Interviews:  {interviews_count}

  Admin login:
    Email:    admin@smartcv.vn
    Password: admin123

  Run server:
    .\\venv\\Scripts\\uvicorn app.main:app --reload

  Swagger UI:
    http://localhost:8000/docs
========================================
""")
    except Exception as e:
        print(f"\nERROR: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())


# 🚀 SmartCV Auto

<div align="center">

![SmartCV Logo](https://img.shields.io/badge/SmartCV-Auto-FF6D5A?style=for-the-badge&logo=dependabot&logoColor=white)

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![HTMX](https://img.shields.io/badge/HTMX-336699?style=flat-square&logo=html5&logoColor=white)](https://htmx.org/)
[![n8n](https://img.shields.io/badge/n8n-FF6D5A?style=flat-square&logo=n8n&logoColor=white)](https://n8n.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)

**Hệ thống AI Automation hỗ trợ sàng lọc và xử lý hồ sơ ứng viên tự động dành cho phòng nhân sự.** \
_Giảm thời gian sàng lọc thủ công, nâng cao tính khách quan và tự động hóa toàn bộ quy trình tuyển dụng._

</div>

---

https://github.com/user-attachments/assets/178d08a6-ae6d-42b7-9225-4f9631d3f669

## ✨ Tính Năng Nổi Bật (Key Features)

| Tính Năng               | Mô Tả                                                                                                                |
| :---------------------- | :------------------------------------------------------------------------------------------------------------------- |
| **Đánh giá CV bằng AI** | Tự động trích xuất dữ liệu CV (PDF/Docx), tóm tắt năng lực và chấm điểm (Matching Score) mức độ phù hợp.             |
| **Tự Động Hóa (n8n)**   | Xây dựng các workflow tự động tiếp nhận CV từ Gmail/Form, đồng bộ hóa quá trình xử lý mà không cần thao tác tay.     |
| **Quản Lý Phỏng Vấn**   | Tự động tạo sự kiện trên Google Calendar, sinh link Google Meet và gửi email mời phỏng vấn tự động cho ứng viên.     |
| **Tự Động Gửi Offer**   | Tự động điền thông tin Offer Letter vào mẫu Google Docs, xuất file PDF và gửi email xác nhận mời nhận việc.          |
| **Giao diện Nội Bộ**    | Giao diện quản lý thân thiện (HTMX) kết hợp FastAPI siêu tốc, phân quyền chi tiết (RBAC) cho HR, Admin, Interviewer. |

> [!NOTE]
> **🤔 Hệ thống hoạt động như thế nào?**
> Thay vì HR phải đọc thủ công từng CV, **SmartCV Auto** sẽ tiếp nhận CV trực tiếp qua Email hoặc Form. Luồng tự động hóa bằng **n8n** sẽ gửi CV cho mô hình **AI (LLM)** để chấm điểm, tóm tắt và bóc tách thông tin. HR chỉ việc nhìn vào bảng điểm và duyệt, hệ thống sẽ tự động lên lịch, tạo link họp Meet và gửi thư mời (Offer) khi ứng viên đạt yêu cầu!

---

## 🚀 Hướng Dẫn Nhanh (Quick Start)

Làm theo các bước sau để thiết lập và chạy hệ thống trên môi trường local.

### 1. Yêu Cầu Hệ Thống (Prerequisites)

- [Python 3.9+](https://www.python.org/downloads/)
- [PostgreSQL](https://www.postgresql.org/download/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop) (để chạy n8n)
- Tài khoản Cloudflare (để sử dụng Cloudflare Tunnel)
- Cấu hình file chứng chỉ/credentials cho Google Workspace (Google Drive/Calendar API)

### 2. Cấu Hình Môi Trường

1. Clone dự án và truy cập thư mục gốc.
2. Tạo file `.env` dựa trên `.env.example` và điền thông tin cấu hình cần thiết:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/smartcv_db

# Security
SECRET_KEY="your_super_secret_jwt_key"
ALGORITHM="HS256"

# Cloudflare Tunnel
TUNNEL_TOKEN="eyJhIjoi..." # Từ Cloudflare Zero Trust để public Webhook của n8n và Backend
```

### 3. Vận Hành Hệ Thống

Hệ thống được chia làm hai phần chính: **Backend (FastAPI)** và **Workflow Engine (n8n)**.

#### Bước 3.1: Chạy Hệ Thống Backend (FastAPI)

Cài đặt các thư viện Python phụ thuộc và khởi chạy server Uvicorn:

```bash
# Cài đặt thư viện
pip install -r requirements.txt

# Khởi chạy server FastAPI (mặc định tại http://localhost:8000)
uvicorn main:app --reload
```

#### Bước 3.2: Chạy Hệ Thống Tự Động Hóa (n8n qua Docker)

Chạy dịch vụ n8n background cùng với Cloudflared để nhận webhook từ bên ngoài:

```bash
# Khởi chạy n8n và cloudflare tunnel thông qua Docker Compose
docker-compose up -d
```

> [!TIP]
> Lệnh này sẽ tự động chạy workflow engine và kết nối tới tunnel để nhận webhook CV hoặc Gmail.

#### Bước 3.3: Công Bố Backend Ra Internet (Thiết lập Cloudflare Tunnel)

Để n8n hoặc các dịch vụ ngoài có thể tương tác ngược lại Backend API, chạy Cloudflare Tunnel cho backend nội bộ (nếu chưa tích hợp vào Docker):

```bash
cloudflared tunnel run --token <TUNNEL_TOKEN>
```

### 4. Truy Cập Hệ Thống

Sau khi cài đặt xong, bạn có thể truy cập qua trình duyệt:

- 👉 **Giao diện Quản Lý HR (Frontend HTMX):** `http://localhost:8000`
- 👉 **Giao diện Workflow (n8n Editor):** `http://localhost:5678`

---

## 📂 Kiến Trúc Dự Án (Project Structure)

```text
SmartCV_Auto/
├── 📄 main.py              # Entry point của ứng dụng FastAPI
├── 📄 .env                 # Chứa các biến môi trường cấu hình
├── 🐳 docker-compose.yml   # Chạy n8n automation engine
├── 📂 app/                 # Thư mục chính của Backend & Frontend xử lý
│   ├── 📂 api/             # Các Endpoints API (RESTful)
│   ├── 📂 core/            # Configs, Security, Database settings
│   ├── 📂 models/          # Khai báo models Database (SQLAlchemy)
│   ├── 📂 schemas/         # Xác thực dữ liệu vào/ra (Pydantic)
│   ├── 📂 services/        # Logic nghiệp vụ xử lý hệ thống
│   ├── 📂 templates/       # Giao diện HTML Render (Jinja2 + HTMX)
│   └── 📂 static/          # Tài nguyên frontend (CSS, JS)
├── 📂 database/            # Scripts quản lý và khởi tạo database
├── 📂 n8n/                 # Dữ liệu tài liệu của hệ thống tự động hóa n8n
└── 📂 docs/                # Các tài liệu phân tích, biểu đồ và thiết kế hệ thống
```

## ⚠️ Lưu Ý Quan Trọng (Important Notes)

> [!IMPORTANT]
> **Đảm bảo đồng bộ Webhook giữa Backend và n8n!**
>
> - Luồng gửi CV từ giao diện HR, luồng gửi Offer và đặt lịch phỏng vấn đều sử dụng Webhook để "bắn" thông tin sang n8n.
> - Cần import các cấu hình workflow (file .json) vào giao diện n8n của bạn và thay đổi URL webhook cho phù hợp trước khi đưa vào vận hành thực tế.
> - Cấu hình đầy đủ Credentials cho mô hình AI LLM trong node của n8n để hệ thống có thể chấm điểm hồ sơ trơn tru.

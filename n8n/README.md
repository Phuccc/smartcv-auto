# 🚀 Self-Hosted n8n (Queue Mode)

<div align="center">

![n8n Logo](https://raw.githubusercontent.com/n8n-io/n8n/master/assets/n8n-logo.png)

[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Windows](https://img.shields.io/badge/Windows-0078D6?style=flat-square&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat-square&logo=linux&logoColor=black)](https://kernel.org/)
[![n8n](https://img.shields.io/badge/n8n-FF6D5A?style=flat-square&logo=n8n&logoColor=white)](https://n8n.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)
[![Qdrant](https://img.shields.io/badge/Qdrant-D51D5A?style=flat-square&logo=qdrant&logoColor=white)](https://qdrant.tech/)

**Ultimate self-hosted n8n toolkit tailored for high performance using Queue Mode, built-in Vector Database for AI Agents, and secure Cloudflare Tunnel access.**

</div>

---

## ✨ Key Features

| Feature              | Description                                                                    |
| :------------------- | :----------------------------------------------------------------------------- |
| **⚡ Queue Mode**    | Decouples the Editor from Workers to prevent freezes under heavy load.         |
| **🧠 AI-Ready**      | Integrated **Qdrant** Vector Store, ready for advanced AI Agent workflows.     |
| **🔒 Secure Access** | Expose your instance securely via **Cloudflare Tunnel** without opening ports. |
| **🔄 Scalable**      | Easily scale Worker replicas to handle concurrent job execution.               |

> [!NOTE]
> **🤔 What are n8n Workers?**
> Think of **n8n Editor** as the "Manager" who designs the plans, and **Workers** as the "Staff" who actually do the heavy lifting.
> By adding more Workers and limiting their resources, you ensure that one heavy job doesn't crash the whole system.

---

## 🚀 Quick Start

Get your system up and running in minutes with our automated scripts.

### 1. Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed.
- A domain name (for Cloudflare Tunnel).

### 2. Configure Environment

1.  Open `.env` file.
2.  Fill in the required fields. Here is a quick reference:

```bash
# Resources
WORKER_COUNT=4            # Number of simultaneous workers
WORKER_CPU_LIMIT=0.5      # CPU limit per worker (0.5 = 50% core)
WORKER_RAM_LIMIT=1024M    # RAM limit per worker

# Security
N8N_ENCRYPTION_KEY="your_super_secret_random_string"

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=mysecretpassword
POSTGRES_DB=n8n

# Connectivity
WEBHOOK_URL="https://n8n.yourdomain.com"
TUNNEL_TOKEN="eyJhIjoi..." # From Cloudflare Zero Trust
```

> [!TIP]
> **Don't know how to get the `TUNNEL_TOKEN`?**
> 👉 **[Read our Step-by-Step Cloudflare Guide](./CLOUDFLARE_GUIDE.md)**

### 3. Launch System

Run the following command depending on your OS:

**Windows (PowerShell):**

```powershell
.\scripts\update_n8n.ps1
```

**Linux / MacOS (Terminal):**

```bash
pwsh ./scripts/update_n8n.ps1
```

> [!TIP]
> This script automatically keeps your environment clean by updating images, removing old containers, and restarting services.

### 4. Verify

Open your browser and navigate to:
👉 **[https://n8n.yourdomain.com](https://n8n.yourdomain.com)**

Or access locally via `http://localhost:5678`

### 5. Import Workflows & Credentials

If you have existing data, you can import it without restarting:

1.  Place `.json` workflow files in `n8n_storage/workflow`.
2.  Place credentials files in `n8n_storage/certificate`.
3.  Run the import script:

```powershell
.\scripts\import_data.ps1
```

---

## 📂 Project Structure

```text
self-hosted_n8n/
├── 📄 .env                 # Environment variables
├── 🐳 docker-compose.yml   # Docker services definition
├── 📂 scripts/             # Management scripts (update, import)
│   ├── 📜 update_n8n.ps1
│   └── 📜 import_data.ps1
├── 📂 docker_data/         # Redis persistence
├── 📂 n8n_storage/         # n8n data (workflows, credentials)
└── 📂 qdrant_data/         # Vector embeddings (AI memory)
```

## ⚠️ Important Notes

> [!IMPORTANT]
> **Backup `n8n_storage` and `.env` regularly!**
>
> - `n8n_storage`: Contains your workflows, credentials, and binary data.
> - `.env`: Contains your secrets and configuration.
> - Database data is stored in Docker volumes (`db_data`), which should also be backed up for production use.

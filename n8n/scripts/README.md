# Helper Scripts

This directory contains PowerShell scripts to help manage the n8n instance. These scripts are cross-platform and can be run on both Windows (natively) and Ubuntu/Linux (via PowerShell).

## 🐧 Running on Ubuntu / Linux

First, install PowerShell:

```bash
sudo snap install powershell --classic
```

Then run the scripts using `pwsh`:

```bash
pwsh ./scripts/update_n8n.ps1
```

## 🛠️ Scripts

### `update_n8n.ps1`

One-click update script to pull the latest images, clean up old containers, and restart the system.

### `import_data.ps1`

Manually imports workflows and credentials from `n8n_storage/` into the running n8n instance.

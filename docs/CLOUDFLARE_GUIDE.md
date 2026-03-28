# ☁️ How to Get Your Cloudflare Tunnel Token

This guide will show you exactly how to generate the `TUNNEL_TOKEN` required for your `.env` file.

## Prerequisites
1.  A **Cloudflare Account**.
2.  A **Domain Name** added to your Cloudflare account.
3.  **Zero Trust** setup (it's free). If you haven't enabled it, go to the Cloudflare Dashboard and click "Zero Trust" on the sidebar to enable it.

---

## Step-by-Step Guide

### 1. Open Zero Trust Dashboard
*   Go to [one.dash.cloudflare.com](https://one.dash.cloudflare.com/).
*   Navigate to **Networks** -> **Tunnels**.

### 2. Create a New Tunnel
*   Click the **Create a tunnel** button.
*   Select **Cloudflared** as the connector type.
*   Click **Next**.

### 3. Name Your Tunnel
*   Enter a name for your tunnel (e.g., `n8n-server`).
*   Click **Save tunnel**.

### 4. Get the Token
You will see a screen titled "Install and run a connector".
*   Look for the box confirming your OS (it defaults to Windows/Mac/Linux).
*   Look at the command block below "Run the following command".
*   You will see a long string of characters after `--token`.

**That long string is your `TUNNEL_TOKEN`.**

> Example Command:
> `cloudflared.exe service install eyJhIjoiM...`
>
> You only need the part starting with `eyJh...`

### 5. Configure Public Hostname (Important!)
*   Click **Next**.
*   In the **Public Hostnames** tab, click **Add a public hostname**.
*   **Subdomain**: Enter `n8n` (or whatever you like).
*   **Domain**: Select your domain from the dropdown.
*   **Service**:
    *   **Type**: `HTTP`
    *   **URL**: `n8n:5678` (Note: Use the container name `n8n`, not `localhost`)
*   Click **Save hostname**.

---

## ✅ You're Done!
Copy the token you found in **Step 4** and paste it into your `.env` file:

```bash
TUNNEL_TOKEN="eyJhIjoiM..."
```

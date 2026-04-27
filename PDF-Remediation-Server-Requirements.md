# PDF Accessibility Remediation Tool
## Server Setup Requirements
### Brooklyn College — IT Systems
### Prepared by: Mariya Gluzman
### Date: April 17, 2026

---

## What We Are Building and Why

Brooklyn College faculty are facing back-to-back accessibility compliance deadlines —
Title II of the ADA in April 2026 and New York State accessibility requirements in
January 2027. For many courses, PDF documents make up the majority of course materials that must be
remediated, and they are among the hardest file types to fix — typically requiring
technical knowledge, multiple specialized tools (some of them paid), and significant
time across dozens of files per course.

The College does not have the staff or resources to support faculty through this
process at any meaningful scale. CUNY-wide tools such as Brightspace Ally help,
but leave PDFs largely unaddressed. This application attempts to fill that gap at least partially — giving
Brooklyn College a way to support its faculty through a free, accessible,
browser-based tool that requires no technical expertise and no additional software.

Faculty access it through a web link. All processing happens on the server.
No user accounts. No data storage. When a session ends, everything is gone.

---

## The Application

The tool is built in **Python** using **Streamlit**, a free open-source web
framework. It is already written and working. We are not changing the code —
we just need a server to run it on.

The application:
- Accepts a PDF upload from a faculty member
- Analyzes it for accessibility issues
- Runs OCR on scanned documents (image-based PDFs)
- Guides the faculty member through fixing each issue
- Delivers a remediated file for download
- Wipes all data from the session when the user is done

---

## Server Specifications

| Component | Minimum | Optimal |
|-----------|---------|---------|
| CPU | 8-core x86-64 | 16-core x86-64 (Intel Xeon or AMD EPYC) |
| RAM | 16 GB | 32 GB |
| Storage | 256 GB SSD | 512 GB NVMe SSD |
| Network | 1 Gbps, public-facing with a Brooklyn College hostname and SSL certificate | Same |
| Operating System | **Ubuntu Server 24.04 LTS (64-bit)** | Same |

The minimum configuration supports 2–3 concurrent users. RAM is the most
critical factor — the document analysis engine (Docling) loads approximately
4 GB of AI models into memory at startup regardless of how many users are
active. The optimal configuration supports 6–8 concurrent users comfortably,
with headroom for peak periods at the start of a semester.

---

## Software to Install

### 1. Python 3.12
The programming language the application is written in.
```
apt install python3.12 python3.12-venv python3.12-dev
```

### 2. Tesseract OCR 5.x
Reads text from scanned PDF pages (PDFs that are images rather than real text).
```
apt install tesseract-ocr tesseract-ocr-eng
```

### 3. Poppler
Converts PDF pages into images so OCR can process them.
```
apt install poppler-utils
```

### 4. Supporting system libraries
Required by the image processing components of the application.
```
apt install libmagic1 libgl1-mesa-glx libglib2.0-0
```

### 5. Nginx
Sits in front of the application and handles the public URL and SSL certificate.
```
apt install nginx
```

### 6. Certbot
Manages the SSL certificate so the site runs on HTTPS.
```
apt install certbot python3-certbot-nginx
```

### 7. Docling (IBM)
An AI-powered document structure analysis engine developed by IBM, released as
free open-source software. Docling examines each PDF to identify headings, reading
order, tables, figures, and lists — the foundation for the tool's accessibility
analysis. It runs entirely on the server using locally stored model files.
Installed via pip (see item 9 below). On first run, Docling downloads its model
files (~1 GB) from the internet. This happens once only. After that it runs
entirely on-device with no outbound connections.

### 8. EasyOCR
A neural-network-based OCR engine used as a fallback when Tesseract cannot
accurately read a scanned page. Like Docling, it runs entirely on the server
and downloads its model files once on first use. Installed via pip (see item 9).

### 9. Streamlit — Front End (included, no custom development required)
Streamlit is the free open-source framework that serves the browser interface
faculty see when they use the tool. It generates the entire front end automatically
from our Python code. No separate front end needs to be built, designed, or
maintained by IT.

### 10. Remaining Python application packages
All other dependencies — PDF processing libraries, image processing, language
detection, and output generation — install in one command from the requirements
file we provide, alongside Streamlit, Docling, and EasyOCR.
```
pip install -r requirements.txt
```

---

## Configuration

### Streamlit config file
Place the following at `.streamlit/config.toml` in the application directory:

```toml
[server]
port = 8501
address = "127.0.0.1"
maxUploadSize = 300
headless = true

[browser]
gatherUsageStats = false

[runner]
fastReruns = true
```

`gatherUsageStats = false` ensures Streamlit does not phone home to its own servers.
`address = "127.0.0.1"` means Streamlit only listens internally — all public traffic
goes through Nginx.

### Nginx config
Nginx proxies public HTTPS traffic to Streamlit on port 8501 and handles the
SSL certificate. A standard Streamlit reverse-proxy config is well-documented
and straightforward to apply.

### Systemd service
The application should run as a systemd service so it starts automatically on
boot and restarts automatically if it crashes. We will provide the service file.

---

## Session Data Policy

The application holds uploaded PDFs and all working data in memory only, for
the duration of the session. When the session ends:

- All uploaded files are gone
- All processing results are gone
- Nothing is written to a database
- The only disk writes are small temporary files created during document analysis,
  which are deleted immediately after use by the application itself

Add the following cron job as a belt-and-suspenders cleanup of the system
temp directory:

```
0 3 * * * find /tmp -type f -mmin +120 -delete
```

This deletes any file in `/tmp` older than 2 hours, running nightly at 3 AM.

---

## Firewall Rules

Only two inbound ports need to be open to the public internet:

| Port | Protocol | Purpose |
|------|----------|---------|
| 80 | HTTP | Redirects to HTTPS automatically |
| 443 | HTTPS | All faculty traffic |

Streamlit runs internally on port 8501 and must **not** be exposed publicly.
All other ports should remain closed.

---

## Monitoring

No additional monitoring infrastructure is required. The application runs as a
systemd service, which automatically restarts it if it crashes. To check whether
the application is running at any time:

```
systemctl status pdf-assistant
```

---

## Backup

No backup is required. The application stores nothing — no database, no user
files, no session data. The only items on disk are the application code and the
Docling model files, both of which can be fully restored by redeploying the code
and running the application once to re-download the models.

---

## SSL Certificate Renewal

Certbot renews the SSL certificate automatically. No manual renewal or calendar
reminders are needed. To confirm auto-renewal is working:

```
certbot renew --dry-run
```

---

## What We Will Provide

- The complete application code
- `requirements.txt` listing all Python packages
- The Streamlit config file
- The systemd service file
- Instructions for the one-time Docling model download

---

## Summary Checklist

- [ ] Provision server per specifications above
- [ ] Install Ubuntu Server 24.04 LTS
- [ ] Assign a Brooklyn College hostname and point DNS
- [ ] Open inbound ports 80 and 443; confirm port 8501 is not publicly accessible
- [ ] `apt install` all system packages listed above
- [ ] Create a Python virtual environment and run `pip install -r requirements.txt`
- [ ] Deploy application code to server
- [ ] Run the application once to trigger Docling model download
- [ ] Configure Nginx as reverse proxy
- [ ] Run Certbot to issue SSL certificate and confirm auto-renewal with `certbot renew --dry-run`
- [ ] Create systemd service for automatic startup and restart
- [ ] Add cron job for temp file cleanup
- [ ] Confirm the public URL loads in a browser

---

*Contact: Mariya Gluzman — mgluzman@brooklyn.cuny.edu*

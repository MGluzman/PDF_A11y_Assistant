# PDF Accessibility Remediation Tool
## Plain-Language Server Setup Overview
### Brooklyn College — For IT Administration
### Prepared by: Mariya Gluzman
### Date: April 17, 2026

---

## What This Tool Is and Why We Built It

Brooklyn College faculty are facing back-to-back accessibility compliance deadlines —
Title II of the ADA in April 2026 and New York State accessibility requirements in
January 2027. PDF documents make up the majority of course materials that must be
remediated, and they are among the hardest file types to fix. Doing it properly
typically requires knowledge of technical standards, access to multiple specialized
tools (many of them paid), and significant time — multiplied across dozens of files
per course.

CUNY offers some remediation resources, such as Brightspace Ally, but coverage is
incomplete and PDFs remain a persistent gap. Brooklyn College faculty are being asked
to meet these requirements largely on their own.

This tool addresses that gap directly. It is a simple web application — accessible
via a browser link, no installation required — that guides faculty through the
remediation process step by step, without requiring technical expertise or access
to paid software. Faculty upload a PDF, work through the issues the tool identifies,
download the corrected file, and the tool wipes all data from the session when they
are done.

The tool is already built and working. We are simply asking for a server to run it on.

---

## Why It Needs to Live on a Brooklyn College Server

- **Cost.** Commercial hosting services charge based on traffic volume. As faculty
  adoption grows, costs would become unsustainable. A Brooklyn College server
  eliminates ongoing hosting fees entirely.

- **Data privacy.** CUNY policy requires that faculty documents not be processed
  on systems outside the CUNY ecosystem. A Brooklyn College server keeps everything
  in-house. No faculty files ever leave the campus infrastructure.

- **No vendor dependency.** The application runs on standard free open-source
  software. We are not locked into any platform or subscription.

---

## What the Server Will Run

The application is written in **Python**, one of the most widely used programming
languages in the world. It uses a free open-source web framework called
**Streamlit** that serves the browser interface. All the heavy lifting —
reading PDFs, running document analysis, processing scanned pages — happens on
the server, not on the faculty member's computer.

Below is a plain-language description of each software component and why it is needed.

---

## Software Components

### Python 3.12
The programming language the entire application is written in. Free and
universally supported on Linux. Your systems team will be familiar with it.

### Streamlit
The framework that turns our Python code into a working website. Free and
open-source. This is what faculty see when they open the tool in their browser.
There is no licensing cost.

### Tesseract OCR
A free open-source program that reads text from scanned documents —
PDFs that were physically photocopied and saved as images rather than as
real text. Without this, the tool cannot process scanned course packets,
which are extremely common in faculty course materials.
Tesseract was originally developed by HP and is now maintained by Google.

### Docling (IBM)
An AI-powered document analysis engine developed by IBM and released as free
open-source software. It examines the structure of a PDF — identifying headings,
reading order, tables, figures, and lists — so the tool can assess and fix
accessibility issues accurately. It runs entirely on the server using pre-downloaded
models. It does not call any external service or API. No data leaves the server.

### Nginx
A widely used free web server that sits between the public internet and the
application. It handles the secure HTTPS connection (the padlock in the browser)
and routes faculty traffic to the application. Your team will almost certainly
have experience with Nginx.

### Ubuntu Server 24.04 LTS
The Linux operating system we are requesting for the server. LTS stands for
Long-Term Support, meaning it receives security updates from Canonical through 2029.
It is the most common server operating system for Python-based applications and
is free to run.

---

## Server Hardware Needed

| What | Why |
|------|-----|
| 16-core processor | Document analysis (Docling) is computationally intensive, especially for large PDFs. More cores means faculty are not waiting on each other. |
| 32 GB of RAM | Docling loads AI models into memory (~4 GB). Each active faculty session needs additional memory. 32 GB supports roughly 6–8 simultaneous users comfortably. |
| 512 GB SSD | Fast storage for the operating system, application, and AI model files. |
| Public hostname + SSL certificate | Faculty need a stable Brooklyn College URL (e.g., `pdftool.brooklyn.cuny.edu`) and a valid HTTPS certificate so the browser shows a secure connection. |

---

## Data Privacy and Retention

This is designed to be a zero-retention service.

- Faculty files are held in the server's memory only, for the duration of their session
- Nothing is written to a database
- Nothing is stored after the session ends
- A scheduled cleanup task runs nightly to remove any temporary files older than two hours
- There are no user accounts and no login — the tool is open to anyone with the URL

This design was intentional. It minimizes privacy risk and eliminates the need
for a data retention policy.

---

## What We Will Hand Off to Your Team

When we are ready to deploy, your team will receive:

- The complete application code
- A list of all software packages to install (one command installs everything)
- A configuration file for the application
- A service file so the application starts automatically and restarts if it crashes
- Step-by-step setup instructions written for your technical staff

Your team's work is essentially: provision the server, run the install commands
we provide, configure Nginx, and point DNS to the new hostname. Estimated setup
time for an experienced Linux administrator is **half a day**.

---

## Setup Checklist (High Level)

- [ ] Provision a server meeting the hardware specifications above
- [ ] Install Ubuntu Server 24.04 LTS
- [ ] Assign a Brooklyn College hostname and SSL certificate
- [ ] Install required software packages (detailed list provided separately)
- [ ] Deploy the application code
- [ ] Configure Nginx and enable HTTPS
- [ ] Set the application to start automatically on boot
- [ ] Schedule the nightly temp file cleanup
- [ ] Confirm the public URL is reachable in a browser

---

*Questions: Mariya Gluzman — mgluzman@brooklyn.cuny.edu*

*Full technical specifications are in the companion document:*
*`PDF-Remediation-Server-Requirements.md`*

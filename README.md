# FreightRead 🚛
### Bill of Lading Processor — Built on the Affinda Intelligent Document Processing API

FreightRead extracts structured data from trucking documents instantly. Upload any bill of lading as a PDF or image and get back 16 fields — shipper, consignee, carrier, cargo, weight, and more — in seconds. No templates, no manual entry.

Built as a demonstration of the [Affinda](https://affinda.com) document AI platform, specialised for the trucking industry.

---

## What it looks like

Upload a bill of lading → AI extracts all fields → results appear in a clean dashboard:

| Section | Fields extracted |
|---|---|
| Document details | BOL number, date, SID number, Pro number |
| Shipper & consignee | Shipper, origin, consignee, destination |
| Carrier details | Carrier name, trailer number, seal number |
| Shipment details | Gross weight, quantity |
| Description of goods | Each cargo line item separately |
| Terms & instructions | Freight terms, special instructions |

---

## Prerequisites

Before you start, make sure you have these installed:

- **Python 3.8 or higher** — download from [python.org](https://python.org/downloads)
  - During install on Windows, tick **"Add Python to PATH"**
- **pip** — comes with Python automatically
- **Git** — download from [git-scm.com](https://git-scm.com/download/win) (Windows)

Check you have them by running:
```bash
python --version
pip --version
git --version
```

---

## Step 1 — Get your Affinda credentials

You need two things from Affinda: an API key and a Workspace ID.

### 1a. Create a free Affinda account

Go to [affinda.com](https://affinda.com) and sign up. The free trial gives you full API access — no credit card required.

### 1b. Get your API key

1. Log in to [app.affinda.com](https://app.affinda.com)
2. Click **Settings** in the left sidebar
3. Click **API Keys**
4. Click **Create API Key**
5. Copy the key — it starts with `aff_`

### 1c. Set up your workspace and get the Workspace ID

1. In the Affinda dashboard, click **Workspaces** in the left sidebar
2. Click an existing workspace or create a new one
3. Inside the workspace, click **Document Types** → create a new one called `Bill of Lading`
4. In the "Describe what fields to extract" box, paste this:

```
Extract the following fields from this trucking Bill of Lading:
- billOfLadingNumber: the BOL reference number
- date: the document date
- sidNumber: the SID number
- proNumber: the Pro number
- shipper: the company sending the shipment (Ship From name and address)
- origin: the Ship From address
- consignee: the company receiving the shipment (Ship To name and address)
- destination: the Ship To address
- carrier: the trucking company name
- trailerNumber: the trailer number
- sealNumber: the seal number
- grossWeight: the total weight
- quantity: the total number of packages
- descriptionOfGoods: the cargo description (repeating field)
- freightTerms: payment terms such as Prepaid or Collect
- specialInstructions: any special handling notes
```

5. Upload a sample bill of lading PDF to train the model, then click **Save**

---

## Step 2 — Download the project

### Option A — Clone from GitHub
```bash
git clone https://github.com/Fakrul-chowdhury/freightread.git
cd freightread
```

### Option B — Download as ZIP
Click the green **Code** button on this page → **Download ZIP** → unzip the folder.

---

## Step 3 — Navigate to the project folder

Open a terminal (Command Prompt on Windows) inside the project folder.

**On Windows — quickest way:**
1. Open the project folder in File Explorer
2. Click the address bar at the top
3. Type `cmd` and press Enter

You should see the folder path in your terminal, e.g.:
```
C:\Users\yourname\Downloads\freightread>
```

---

## Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs Flask, Requests, and Werkzeug. Takes about 30 seconds.

---

## Step 5 — Set your API credentials

You must set these before running the app. They are read as environment variables so your keys are never stored in the code.

**Windows (Command Prompt):**
```bash
set AFFINDA_API_KEY=aff_your_key_here
set AFFINDA_WORKSPACE_ID=your_workspace_id_here
```

**Mac / Linux:**
```bash
export AFFINDA_API_KEY=aff_your_key_here
export AFFINDA_WORKSPACE_ID=your_workspace_id_here
```

> ⚠️ These only last for the current terminal session. If you close the terminal and reopen it, you need to set them again before running the app.

**To verify they are set correctly (Windows):**
```bash
echo %AFFINDA_API_KEY%
echo %AFFINDA_WORKSPACE_ID%
```
Both should print the actual values, not blank lines.

---

## Step 6 — Run the app

```bash
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

---

## Step 7 — Use the app

1. Open your browser and go to **http://localhost:5000**
2. Drag and drop a bill of lading PDF onto the upload zone, or click to browse
3. Wait 10–30 seconds while Affinda's AI reads the document
4. All extracted fields appear in the results dashboard
5. Click **Copy JSON** to copy the structured data to your clipboard
6. Click **Process another** to upload a new document

---

## Project structure

```
freightread/
├── app.py                  # Flask backend + Affinda API integration
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── static/
│   └── uploads/            # Temporary file storage (auto-created, auto-cleared)
└── templates/
    └── index.html          # Frontend UI (drag-and-drop, results dashboard)
```

---

## How it works

```
User uploads PDF
      ↓
Flask receives file → saves temporarily to static/uploads/
      ↓
app.py POSTs file to Affinda API (/v3/documents)
      ↓
Affinda returns a document ID
      ↓
app.py polls GET /v3/documents/{id} every 2 seconds
      ↓
Affinda AI extracts all 16 fields (OCR + LLM + RAG)
      ↓
app.py maps field names to our trucking data structure
      ↓
Flask returns JSON to the frontend
      ↓
index.html renders results in the dashboard
      ↓
Temp file is deleted
```

---

## Troubleshooting

**"Not found" error or all fields show as empty**
- Your Workspace ID is wrong. Check the URL in your Affinda dashboard while inside your workspace.
- Your API key may have expired. Go to Affinda → Settings → API Keys and generate a new one.

**"No such file or directory: requirements.txt"**
- You are not inside the project folder. Run `cd freightread` (or wherever you unzipped the folder) before installing.

**Fields show as "Not found" after processing**
- Your Affinda workspace document type may not be configured. Follow Step 1c above to set up the Bill of Lading model with the correct field names.
- Use the debug endpoint to see exactly what Affinda is returning (see below).

**App works but credentials reset after closing terminal**
- Environment variables are session-only on Windows. Set them again each time you open a new terminal, or add them to your system environment variables permanently via Control Panel → System → Advanced → Environment Variables.

---

## Debug endpoint

If fields are not extracting correctly, use the debug endpoint to see the raw Affinda response:

```bash
curl -X POST http://localhost:5000/debug -F "file=@your_document.pdf"
```

This returns all the field names and values exactly as Affinda returns them, so you can verify the field name mapping in `app.py`.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3 / Flask |
| Document AI | [Affinda API v3](https://docs.affinda.com) |
| Frontend | Vanilla HTML, CSS, JavaScript |
| File handling | Werkzeug |

---

## Extending this project

Ideas to take it further:
- **Export to CSV** — add a download button that exports extracted fields to a spreadsheet
- **History log** — store past extractions in a SQLite database
- **Email upload** — Affinda supports document upload via email natively
- **Webhook support** — replace polling with Affinda webhooks for instant results
- **Multi-document batch** — process an entire folder of BOLs at once
- **Customer-specific models** — fine-tune the Affinda workspace for a specific carrier's document format

---

*Built for the Affinda Winter Internship 2026 application.*  
*Demonstrates specialisation of the Affinda platform for the trucking industry.*

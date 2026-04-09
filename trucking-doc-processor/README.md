# FreightRead — Trucking Document Processor
### Built on the Affinda Intelligent Document Processing API

A web app that extracts structured data from bills of lading, delivery dockets, and freight orders using AI.

---

## Setup (5 minutes)

### 1. Get your Affinda credentials

1. Sign up at [affinda.com](https://affinda.com) — free trial, no credit card
2. Go to **Settings → API Keys** and create a key
3. Create a new **Workspace** called "Trucking"
4. Copy the Workspace ID from **Workspace → Workflow → Integrations**

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set environment variables

**Mac/Linux:**
```bash
export AFFINDA_API_KEY="aff_your_key_here"
export AFFINDA_WORKSPACE_ID="your_workspace_id_here"
```

**Windows:**
```bash
set AFFINDA_API_KEY=aff_your_key_here
set AFFINDA_WORKSPACE_ID=your_workspace_id_here
```

### 4. Run the app

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000)

---

## What it extracts

| Field | Description |
|---|---|
| Shipper | Consignor / sender name |
| Consignee | Receiver name |
| Carrier | Transport company |
| Origin | Port of loading / pickup |
| Destination | Port of discharge / delivery |
| BOL Number | Bill of lading reference |
| Date | Document / shipment date |
| Cargo | Description of goods |
| Weight | Gross weight |
| Quantity | Number of packages / units |
| Vessel / Vehicle | Ship or truck identifier |
| Freight Terms | Payment terms |

---

## How it works

1. User uploads a PDF, image, or DOCX of a trucking document
2. The file is sent to the **Affinda API** (`POST /v3/documents`)
3. Affinda's AI agents (OCR + LLM + RAG) extract all fields
4. The app maps Affinda's response to structured trucking fields
5. Results are displayed in a clean dashboard with a JSON export

---

## Project structure

```
trucking-doc-processor/
├── app.py              # Flask backend + Affinda API integration
├── requirements.txt    # Python dependencies
├── README.md
└── templates/
    └── index.html      # Frontend UI
```

---

## Extending this

Some ideas to take it further for the Affinda internship:
- Add a database to store historical extractions (SQLite)
- Export results as CSV for spreadsheet import
- Add email upload support (Affinda supports this natively)
- Build a webhook endpoint to receive async results
- Specialise the workspace for a specific customer's document format

---

## Tech stack

- **Backend**: Python / Flask
- **Document AI**: [Affinda API](https://docs.affinda.com)
- **Frontend**: Vanilla HTML/CSS/JS

---

*Built as a demo project for the Affinda Winter Internship 2026 application.*

import os
import time
import requests
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB file size limit
app.config['UPLOAD_FOLDER'] = 'static/uploads'

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx'}

# Loaded from environment variables — never hardcode API keys in source code
AFFINDA_API_KEY = os.environ.get('AFFINDA_API_KEY', 'YOUR_API_KEY_HERE')
AFFINDA_WORKSPACE_ID = os.environ.get('AFFINDA_WORKSPACE_ID', 'YOUR_WORKSPACE_ID_HERE')
AFFINDA_BASE_URL = 'https://api.affinda.com/v3'


def allowed_file(filename):
    # Only accept document and image formats — reject executables, scripts, etc.
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_to_affinda(file_path, filename):
    """
    Uploads a document to the Affinda API and polls until extraction is complete.
    Affinda processes documents asynchronously — we upload, get a document ID,
    then poll every 2 seconds until extracted data appears in the response.
    """
    headers = {
        'Authorization': f'Bearer {AFFINDA_API_KEY}',
        'Accept': 'application/json',
    }

    # POST the file to Affinda — workspace ID tells Affinda which document
    # type model to use (our Bill of Lading model with 16 configured fields)
    with open(file_path, 'rb') as f:
        files = {'file': (filename, f, 'application/octet-stream')}
        data = {'workspace': AFFINDA_WORKSPACE_ID}
        response = requests.post(
            f'{AFFINDA_BASE_URL}/documents',
            headers=headers,
            files=files,
            data=data,
            timeout=60
        )

    if response.status_code not in (200, 201):
        raise Exception(f'Affinda API error {response.status_code}: {response.text}')

    doc = response.json()
    if doc.get('type') == 'client_error':
        raise Exception(f'Affinda error: {doc}')

    # Affinda returns the document identifier inside the 'meta' object
    doc_id = (doc.get('meta') or {}).get('identifier') or doc.get('identifier') or doc.get('id')
    if not doc_id:
        raise Exception(f'No document ID in response: {doc}')

    # Poll until Affinda's AI has finished extracting fields.
    # We don't wait for human review — we read extracted data immediately.
    # Max wait: 30 attempts x 2 seconds = 60 seconds.
    for attempt in range(30):
        time.sleep(2)
        poll = requests.get(
            f'{AFFINDA_BASE_URL}/documents/{doc_id}',
            headers=headers,
            timeout=30
        )
        result = poll.json()

        if result.get('type') == 'client_error':
            raise Exception(f'Affinda poll error: {result}')

        data = result.get('data')
        # As soon as 'data' is non-empty, extraction is done
        if isinstance(data, dict) and len(data) > 0:
            return result
        if isinstance(data, list) and len(data) > 0:
            return result

    return result  # Return whatever we have after timeout


def extract_value(field):
    """
    Affinda returns each field as a dict containing metadata (position on page,
    confidence score, etc.) alongside the actual value. This function pulls out
    just the human-readable value we care about.
    """
    if field is None:
        return None
    if isinstance(field, str):
        return field.strip() or None
    if isinstance(field, (int, float)):
        return str(field)
    if isinstance(field, list):
        # Some fields (e.g. cargo descriptions) return multiple values as a list
        parts = [extract_value(item) for item in field]
        parts = [p for p in parts if p]
        return parts if parts else None  # Return as list so frontend can render each item
    if isinstance(field, dict):
        # Prefer 'raw' (original text) over 'parsed' (normalised by Affinda)
        for key in ('raw', 'parsed', 'value', 'formatted'):
            v = field.get(key)
            if v is not None and str(v).strip():
                return str(v).strip()
        # Fallback: grab the first non-empty string value in the dict
        for v in field.values():
            if v and isinstance(v, str) and v.strip():
                return v.strip()
    return None


def camel_to_label(name):
    """
    Converts camelCase field names from Affinda into readable labels.
    e.g. 'billOfLadingNumber' -> 'Bill Of Lading Number'
         'grossWeight'        -> 'Gross Weight'
         'sidNumber'          -> 'Sid Number'
    """
    import re
    # Insert a space before each uppercase letter, then title case the result
    spaced = re.sub(r'([A-Z])', r' \1', name).strip()
    return spaced.title()


def parse_trucking_data(affinda_result):
    """
    Dynamically extracts ALL fields Affinda returns — no hardcoded field list.
    This means the app automatically displays any new fields added to the
    Affinda workspace without needing code changes.
    """
    raw = affinda_result.get('data') or {}

    # Skip these internal/non-display fields
    skip_fields = {'rawText', 'pageIndex', 'rectangle', 'rectangles', 'document',
                   'confidence', 'isVerified', 'field', 'contentType', 'parent'}

    fields = []
    for key, value in raw.items():
        if key in skip_fields:
            continue

        extracted = extract_value(value)
        if not extracted:
            continue

        fields.append({
            'key':   key,
            'label': camel_to_label(key),
            'value': extracted,  # Either a string or a list (for repeating fields)
            'is_list': isinstance(extracted, list),
        })

    return {
        'fields':   fields,
        'raw':      raw,
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    """Receives a file from the frontend, sends it to Affinda, returns extracted fields as JSON."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not supported. Use PDF, PNG, JPG, or DOCX.'}), 400

    filename = secure_filename(file.filename)  # Sanitise filename to prevent path traversal
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)

    try:
        affinda_result = upload_to_affinda(save_path, filename)
        parsed = parse_trucking_data(affinda_result)
        parsed['filename'] = filename
        return jsonify({'success': True, 'data': parsed})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Always clean up the temp file, even if extraction fails
        if os.path.exists(save_path):
            os.remove(save_path)


@app.route('/debug', methods=['POST'])
def debug():
    """
    Debug endpoint — returns the raw Affinda response including all field names
    and values. Useful for checking what the API returns when adding new fields.
    Hit with: curl -X POST http://localhost:5000/debug -F "file=@document.pdf"
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)
    try:
        result = upload_to_affinda(save_path, filename)
        data = result.get('data', {})
        return jsonify({
            'data_keys': list(data.keys()) if isinstance(data, dict) else str(type(data)),
            'data': data,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(save_path):
            os.remove(save_path)


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5000)

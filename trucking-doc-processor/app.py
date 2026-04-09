import os
import time
import requests
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'static/uploads'

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx'}

AFFINDA_API_KEY = os.environ.get('AFFINDA_API_KEY', 'YOUR_API_KEY_HERE')
AFFINDA_WORKSPACE_ID = os.environ.get('AFFINDA_WORKSPACE_ID', 'YOUR_WORKSPACE_ID_HERE')
AFFINDA_BASE_URL = 'https://api.affinda.com/v3'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_to_affinda(file_path, filename):
    headers = {
        'Authorization': f'Bearer {AFFINDA_API_KEY}',
        'Accept': 'application/json',
    }
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

    # ID is inside meta
    doc_id = (doc.get('meta') or {}).get('identifier') or doc.get('identifier') or doc.get('id')
    if not doc_id:
        raise Exception(f'No document ID in response: {doc}')

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
        if isinstance(data, dict) and len(data) > 0:
            return result
        if isinstance(data, list) and len(data) > 0:
            return result

    return result


def extract_value(field):
    if field is None:
        return None
    if isinstance(field, str):
        return field.strip() or None
    if isinstance(field, (int, float)):
        return str(field)
    if isinstance(field, list):
        parts = [extract_value(item) for item in field]
        parts = [p for p in parts if p]
        return ', '.join(parts) if parts else None
    if isinstance(field, dict):
        for key in ('raw', 'parsed', 'value', 'formatted'):
            v = field.get(key)
            if v is not None and str(v).strip():
                return str(v).strip()
        for v in field.values():
            if v and isinstance(v, str) and v.strip():
                return v.strip()
    return None


def parse_trucking_data(affinda_result):
    raw = affinda_result.get('data') or {}

    def get(*keys):
        for key in keys:
            val = extract_value(raw.get(key))
            if val:
                return val
        return None

    # descriptionOfGoods is a list of items — keep them separate for display
    cargo_raw = raw.get('descriptionOfGoods', [])
    if isinstance(cargo_raw, list):
        cargo_list = [extract_value(item) for item in cargo_raw]
        cargo_list = [c for c in cargo_list if c]
    elif cargo_raw:
        cargo_list = [extract_value(cargo_raw)]
    else:
        cargo_list = []

    return {
        'bol_number':           get('billOfLadingNumber', 'bill_of_lading_number'),
        'date':                 get('date'),
        'sid_number':           get('sidNumber', 'sid_number'),
        'pro_number':           get('proNumber', 'pro_number'),
        'shipper':              get('shipper'),
        'origin':               get('origin'),
        'consignee':            get('consignee'),
        'destination':          get('destination'),
        'carrier':              get('carrier'),
        'trailer_number':       get('trailerNumber', 'trailer_number'),
        'seal_number':          get('sealNumber', 'seal_number'),
        'gross_weight':         get('grossWeight', 'gross_weight'),
        'quantity':             get('quantity'),
        'cargo_list':           cargo_list,
        'freight_terms':        get('freightTerms', 'freight_terms'),
        'special_instructions': get('specialInstructions', 'special_instructions'),
        'raw':                  raw,
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not supported. Use PDF, PNG, JPG, or DOCX.'}), 400

    filename = secure_filename(file.filename)
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
        if os.path.exists(save_path):
            os.remove(save_path)


@app.route('/debug', methods=['POST'])
def debug():
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

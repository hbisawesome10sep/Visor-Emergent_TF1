"""
Statement Upload — Endpoints for uploading Groww/Zerodha XLSX statements.
"""
import uuid
import logging
import jwt as pyjwt
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from database import db
from auth import get_current_user
from config import JWT_SECRET
from services.statement_parser import parse_holdings_xlsx

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ─────────────────────────────────────────────────────────────────────────────
#  WEB UPLOAD PAGE  (Safari-based — bypasses iOS native picker completely)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/upload-page", response_class=HTMLResponse)
async def upload_page(token: str, type: str = "auto"):
    """Serve a mobile-optimised HTML upload page for iOS/Android."""
    type_labels = {
        "stock_statement": "Stock Holdings (Zerodha / Groww XLSX)",
        "mf_statement": "Mutual Fund Holdings (Groww MF XLSX)",
        "ecas": "eCAS Statement (CAMS / KFintech PDF)",
        "auto": "Any Holdings Statement",
    }
    label = type_labels.get(type, "Holdings Statement")
    accept_attr = "application/pdf,.pdf" if type == "ecas" else ".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>Visor — Upload Statement</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, 'DM Sans', sans-serif;
      background: #0A0A0B; color: #F9FAFB;
      min-height: 100vh; display: flex; flex-direction: column;
      align-items: center; justify-content: flex-start;
      padding: 32px 20px 48px;
    }}
    .logo {{ font-size: 22px; font-weight: 800; color: #10B981; margin-bottom: 8px; letter-spacing: -0.5px; }}
    .subtitle {{ font-size: 13px; color: rgba(255,255,255,0.45); margin-bottom: 32px; }}
    .card {{
      background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09);
      border-radius: 20px; padding: 28px 24px; width: 100%; max-width: 420px;
    }}
    .card-title {{ font-size: 17px; font-weight: 700; margin-bottom: 4px; }}
    .card-sub {{ font-size: 13px; color: rgba(255,255,255,0.5); margin-bottom: 24px; line-height: 1.4; }}
    .drop-zone {{
      border: 2px dashed rgba(16,185,129,0.4); border-radius: 14px;
      padding: 28px 20px; text-align: center; cursor: pointer;
      transition: border-color 0.2s, background 0.2s;
      background: rgba(16,185,129,0.04);
      position: relative;
    }}
    .drop-zone.has-file {{ border-color: #10B981; background: rgba(16,185,129,0.08); }}
    .drop-zone input[type=file] {{
      position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
    }}
    .drop-icon {{ font-size: 36px; margin-bottom: 8px; }}
    .drop-text {{ font-size: 14px; font-weight: 600; color: #10B981; }}
    .drop-hint {{ font-size: 12px; color: rgba(255,255,255,0.4); margin-top: 4px; }}
    .file-name {{
      font-size: 13px; color: #10B981; font-weight: 600; margin-top: 8px;
      word-break: break-all; display: none;
    }}
    .upload-btn {{
      width: 100%; margin-top: 20px; padding: 15px;
      background: #10B981; border: none; border-radius: 14px;
      color: #fff; font-size: 15px; font-weight: 700;
      cursor: pointer; transition: opacity 0.2s;
    }}
    .upload-btn:disabled {{ opacity: 0.4; cursor: not-allowed; }}
    .upload-btn:active {{ opacity: 0.8; }}
    .progress {{ display: none; margin-top: 16px; }}
    .progress-bar-wrap {{
      background: rgba(255,255,255,0.08); border-radius: 8px; height: 6px; overflow: hidden;
    }}
    .progress-bar {{ height: 100%; background: #10B981; border-radius: 8px; width: 0%; transition: width 0.3s; }}
    .progress-text {{ font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 8px; text-align: center; }}
    .result {{ display: none; margin-top: 24px; border-radius: 14px; padding: 20px; text-align: center; }}
    .result.success {{ background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3); }}
    .result.error {{ background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.3); }}
    .result-icon {{ font-size: 36px; margin-bottom: 10px; }}
    .result-title {{ font-size: 17px; font-weight: 700; margin-bottom: 6px; }}
    .result-msg {{ font-size: 13px; color: rgba(255,255,255,0.6); line-height: 1.5; }}
    .back-btn {{
      width: 100%; margin-top: 16px; padding: 14px;
      background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.1);
      border-radius: 14px; color: #fff; font-size: 14px; font-weight: 600;
      cursor: pointer; display: none;
    }}
    .tips {{ margin-top: 20px; font-size: 12px; color: rgba(255,255,255,0.35); line-height: 1.6; }}
    .tips b {{ color: rgba(255,255,255,0.6); }}
  </style>
</head>
<body>
  <div class="logo">Visor Finance</div>
  <div class="subtitle">Secure statement upload</div>

  <div class="card">
    <div class="card-title">Upload {label}</div>
    <div class="card-sub">Select your file from Files / iCloud Drive. Your data is encrypted and stays private.</div>

    <div class="drop-zone" id="dropZone">
      <input type="file" id="fileInput" accept="{accept_attr}" />
      <div class="drop-icon">📂</div>
      <div class="drop-text">Tap to choose file</div>
      <div class="drop-hint">Supported: {'PDF' if type == 'ecas' else 'XLSX / XLS'}</div>
      <div class="file-name" id="fileName"></div>
    </div>

    <button class="upload-btn" id="uploadBtn" disabled onclick="doUpload()">Upload Statement</button>

    <div class="progress" id="progress">
      <div class="progress-bar-wrap"><div class="progress-bar" id="progressBar"></div></div>
      <div class="progress-text" id="progressText">Uploading...</div>
    </div>

    <div class="result" id="result">
      <div class="result-icon" id="resultIcon"></div>
      <div class="result-title" id="resultTitle"></div>
      <div class="result-msg" id="resultMsg"></div>
    </div>

    <button class="back-btn" id="backBtn" onclick="goBack()">← Return to Visor App</button>

    <div class="tips">
      <b>How to find your statement:</b><br/>
      Groww: Profile → Statements → Download XLSX<br/>
      Zerodha: Console → Portfolio → Holdings → Download
    </div>
  </div>

  <script>
    const TOKEN = '{token}';
    const TYPE = '{type}';
    const BACKEND = '{{}}'.replace('{{}}', window.location.origin);

    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const fileName = document.getElementById('fileName');
    const uploadBtn = document.getElementById('uploadBtn');

    fileInput.addEventListener('change', () => {{
      if (fileInput.files.length) {{
        const f = fileInput.files[0];
        fileName.textContent = f.name;
        fileName.style.display = 'block';
        dropZone.classList.add('has-file');
        uploadBtn.disabled = false;
      }}
    }});

    async function doUpload() {{
      const file = fileInput.files[0];
      if (!file) return;

      uploadBtn.disabled = true;
      document.getElementById('progress').style.display = 'block';
      document.getElementById('progressBar').style.width = '30%';
      document.getElementById('progressText').textContent = 'Uploading...';

      const formData = new FormData();
      formData.append('file', file);
      formData.append('statement_type', TYPE);

      try {{
        document.getElementById('progressBar').style.width = '60%';
        const res = await fetch(window.location.origin + '/api/upload-statement', {{
          method: 'POST',
          headers: {{ 'Authorization': 'Bearer ' + TOKEN }},
          body: formData,
        }});
        document.getElementById('progressBar').style.width = '100%';
        const data = await res.json();

        document.getElementById('progress').style.display = 'none';
        const resultEl = document.getElementById('result');
        resultEl.style.display = 'block';

        if (res.ok && (data.status === 'success' || data.saved >= 0)) {{
          resultEl.className = 'result success';
          document.getElementById('resultIcon').textContent = '✅';
          document.getElementById('resultTitle').textContent = 'Upload Successful!';
          const sip = data.sip_suggestions_created > 0 ? ` ${{data.sip_suggestions_created}} SIP suggestions added.` : '';
          document.getElementById('resultMsg').textContent =
            `${{data.saved}} holdings imported, ${{data.duplicates}} updated.${{sip}} Return to Visor to see your portfolio.`;
        }} else {{
          resultEl.className = 'result error';
          document.getElementById('resultIcon').textContent = '❌';
          document.getElementById('resultTitle').textContent = 'Upload Failed';
          document.getElementById('resultMsg').textContent = data.detail || data.message || 'Please check the file format and try again.';
          uploadBtn.disabled = false;
        }}
        document.getElementById('backBtn').style.display = 'block';
      }} catch (e) {{
        document.getElementById('progress').style.display = 'none';
        const resultEl = document.getElementById('result');
        resultEl.style.display = 'block';
        resultEl.className = 'result error';
        document.getElementById('resultIcon').textContent = '❌';
        document.getElementById('resultTitle').textContent = 'Network Error';
        document.getElementById('resultMsg').textContent = 'Could not connect. Please check your internet and try again.';
        document.getElementById('backBtn').style.display = 'block';
        uploadBtn.disabled = false;
      }}
    }}

    function goBack() {{
      // Try to close the tab / go back in Safari
      window.close();
      setTimeout(() => history.back(), 300);
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.post("/upload-statement")
async def upload_statement(
    file: UploadFile = File(...),
    statement_type: str = Form("auto"),
    user=Depends(get_current_user),
):
    """
    Upload a Groww/Zerodha XLSX statement.
    statement_type: 'stock_statement', 'mf_statement', 'ecas', or 'auto'
    """
    user_id = user["id"]

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only XLSX/XLS files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 10MB)")

    try:
        result = parse_holdings_xlsx(content, statement_type, file.filename)
    except Exception as e:
        logger.error(f"Parse error for {file.filename}: {e}")
        raise HTTPException(400, f"Failed to parse file: {str(e)}")

    holdings = result["holdings"]
    metadata = result["metadata"]

    if not holdings:
        return {
            "status": "no_holdings",
            "message": "No holdings found in the uploaded file. Please check the file format.",
            "metadata": metadata,
        }

    saved = 0
    duplicates = 0
    errors = 0
    saved_holdings = []

    for h in holdings:
        # Check for duplicate (same user + ISIN or same name+category)
        dup_filter = {"user_id": user_id}
        if h["isin"]:
            dup_filter["isin"] = h["isin"]
        else:
            dup_filter["name"] = h["name"]
            dup_filter["category"] = h["category"]

        existing = await db.holdings.find_one(dup_filter)

        if existing:
            # Update existing holding instead of creating duplicate
            update_fields = {}
            if h["quantity"] > 0:
                update_fields["quantity"] = h["quantity"]
            if h["buy_price"] > 0:
                update_fields["buy_price"] = h["buy_price"]
            if h["invested_value"] > 0:
                update_fields["invested_value"] = h["invested_value"]
            if h.get("current_price") and h["current_price"] > 0:
                update_fields["current_price"] = h["current_price"]
                update_fields["current_value"] = h["current_price"] * h["quantity"]
            if h.get("current_value") and h["current_value"] > 0:
                update_fields["current_value"] = h["current_value"]
            update_fields["source"] = f"{metadata['source']}_statement"
            update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

            await db.holdings.update_one(
                {"_id": existing["_id"]},
                {"$set": update_fields},
            )
            duplicates += 1
            continue

        holding_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": h["name"],
            "ticker": h["ticker"],
            "isin": h["isin"],
            "category": h["category"],
            "sub_category": h.get("sub_category", ""),
            "sector": h.get("sector", ""),
            "amc": h.get("amc", ""),
            "folio": h.get("folio", ""),
            "quantity": h["quantity"],
            "buy_price": h["buy_price"],
            "buy_date": h["buy_date"] or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "invested_value": h["invested_value"],
            "current_price": h.get("current_price") or h["buy_price"],
            "current_value": h.get("current_value") or h["invested_value"],
            "gain_loss": h.get("gain_loss", 0),
            "gain_loss_pct": h.get("gain_loss_pct", 0),
            "xirr": h.get("xirr"),
            "source": f"{metadata['source']}_statement",
            "source_platform": h.get("source_platform", metadata["source"]),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await db.holdings.insert_one(holding_doc)
            saved += 1
            saved_holdings.append({
                "name": h["name"],
                "category": h["category"],
                "quantity": h["quantity"],
                "invested_value": h["invested_value"],
            })
        except Exception as e:
            logger.error(f"Insert error for {h['name']}: {e}")
            errors += 1

    # Log import history
    await db.import_history.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "statement_upload",
        "source": metadata["source"],
        "statement_type": statement_type,
        "filename": file.filename,
        "saved": saved,
        "duplicates": duplicates,
        "errors": errors,
        "total_parsed": len(holdings),
        "imported_at": datetime.now(timezone.utc).isoformat(),
    })

    # Auto-create SIP suggestions for Mutual Fund holdings
    sip_suggestions_created = 0
    mf_holdings = [h for h in holdings if h["category"] == "Mutual Fund"]
    for mf in mf_holdings:
        existing_sug = await db.sip_suggestions.find_one({
            "user_id": user_id,
            "fund_name": mf["name"],
            "status": {"$in": ["pending", "approved"]},
        })
        if not existing_sug:
            await db.sip_suggestions.insert_one({
                "user_id": user_id,
                "fund_name": mf["name"],
                "isin": mf.get("isin", ""),
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            sip_suggestions_created += 1

    return {
        "status": "success",
        "message": f"Imported {saved} holdings ({duplicates} updated, {errors} errors)",
        "saved": saved,
        "duplicates": duplicates,
        "errors": errors,
        "total_parsed": len(holdings),
        "holdings": saved_holdings,
        "metadata": metadata,
        "sip_suggestions_created": sip_suggestions_created,
    }


@router.post("/parse-statement-preview")
async def parse_statement_preview(
    file: UploadFile = File(...),
    statement_type: str = Form("auto"),
    user=Depends(get_current_user),
):
    """Preview parsed holdings before importing."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only XLSX/XLS files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 10MB)")

    try:
        result = parse_holdings_xlsx(content, statement_type, file.filename)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse file: {str(e)}")

    return {
        "holdings": result["holdings"],
        "metadata": result["metadata"],
    }

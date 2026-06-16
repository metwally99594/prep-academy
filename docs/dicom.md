# DICOM Readiness Notes

The DICOM feature is still a gated advanced feature and must not be treated as production-ready until the checks below are complete.

## Current Intended Stack

- Parsing: `pydicom`
- Image processing: `numpy` plus `opencv-python-headless`
- Optional series metadata: `SimpleITK`
- Retrieval: unified RAG via `services.retrieval_orchestrator`
- LLM: OpenRouter-backed report generation
- Export: `fpdf2` PDF and optional DICOM SR

## Production Gate

The backend only attempts to include the DICOM router when:

```env
ENABLE_ADVANCED_FEATURES=true
```

Keep DICOM behind the advanced-feature gate until a staging smoke test has passed with anonymized sample files.

## Blocking Items Before Shipping

- Required runtime dependencies are included in `backend/requirements.txt`:
  - `numpy`
  - `pydicom`
  - `opencv-python-headless`
  - optional: `SimpleITK` remains intentionally excluded unless tested.
- Verify Render memory and cold-start impact after installing image-processing packages.
- Raw DICOM storage is disabled by default. It requires both `DICOM_ENCRYPTION_KEY` and `DICOM_STORE_RAW_ENCRYPTED=true`.
- Avoid storing large raw DICOM payloads in MongoDB; use external object storage or GridFS before enabling raw-byte storage.
- Verify PHI stripping and audit logging with real anonymized sample files.
- Static one-segment routes such as `/api/dicom/review` and `/api/dicom/kb-info` have route-smoke coverage against the UUID analysis route.
- Run DICOM upload/analyze/list/report smoke tests against a staging backend before production exposure.

## API Surface Under Review

- `POST /api/dicom/upload`
- `POST /api/dicom/analyze/{analysis_id}`
- `GET /api/dicom/{analysis_id}`
- `GET /api/dicom/list/mine`
- `POST /api/dicom/compare/{id1}/{id2}`
- `GET /api/dicom/report-pdf/{analysis_id}`
- `GET /api/dicom/timeline/{patient_label}`
- `POST /api/dicom/review/{analysis_id}`
- `GET /api/dicom/review`
- `GET /api/dicom/feedback/{analysis_id}`
- `POST /api/dicom/feedback/{analysis_id}`
- `GET /api/dicom/export-sr/{analysis_id}`
- `GET /api/dicom/kb-info`

## Verification Commands

```powershell
python -m py_compile backend\routes\dicom.py backend\services\email_service.py
cd frontend
npm run build
```

For route-level verification, use a Python environment that includes `pydicom`, `numpy`, `opencv-python-headless`, and `fastapi`.

## Release Rule

Ship DICOM as its own reviewed change set. Do not mix it with RAG, auth, deployment, or unrelated cleanup changes.

# Production Smoke Checks

Use this script after every Render/Vercel deployment to verify the public
production surface without requiring admin credentials.

```powershell
$env:EXPECTED_BACKEND_COMMIT="3b0f80d9551a"
.\backend\venv\Scripts\python.exe backend\evaluation\production_smoke.py
```

Optional environment variables:

```env
BACKEND_URL=https://prep-academy.onrender.com
FRONTEND_URL=https://prepacademy-med.com
EXPECTED_BACKEND_COMMIT=
SMOKE_TIMEOUT_SECONDS=30
```

The smoke report checks:

- backend health is healthy
- deployed commit matches the expected prefix when provided
- RAG is ready on Qdrant
- legacy Chroma is not active
- frontend domain returns HTTP 200
- DICOM and Obsidian admin/protected endpoints reject anonymous access

The script exits with status code `0` only when all checks pass.

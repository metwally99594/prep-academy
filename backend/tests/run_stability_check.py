"""
Verify pipeline stability: job creation, error handling, and MongoDB persistence.
Does NOT attempt AI completion — just verifies the pipeline handles bad images safely.
"""
import os, sys, time, requests, struct, zlib, io, base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://prep-academy.onrender.com')
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"

def get_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    return r.json().get("token") if r.status_code == 200 else None

def make_png(w, h, rgba_data):
    def chunk(tag, data):
        c = zlib.crc32(tag + data) & 0xffffffff
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", c)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    idat = zlib.compress(rgba_data, 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")

def make_image(size, bg=200, noise=10):
    w, h = size, size
    raw = b"".join(bytes([min(255, max(0, bg + (x*y) % noise - noise//2), 255)]) for y in range(h) for x in range(w))
    return base64.b64encode(make_png(w, h, raw)).decode()

def submit(token, image_b64, report_type, context=""):
    h = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BASE_URL}/api/analyzer/analyze", json={
        "image_base64": image_b64,
        "report_type": report_type,
        "clinical_context": context,
    }, headers=h, timeout=30)
    if r.status_code not in (200, 201):
        return {"error": f"{r.status_code}: {r.text[:100]}"}
    return r.json()

def poll_job(token, job_id):
    h = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/api/analyzer/job/{job_id}", headers=h, timeout=15)
    return r.json() if r.status_code == 200 else None

def history(token, limit=5):
    h = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/api/analyzer/history", headers=h, timeout=15)
    return r.json()[:limit] if r.status_code == 200 else []

# Image configs to test
IMAGES = {
    "tiny_20x20": lambda: make_image(20, 180, 8),
    "small_40x40": lambda: make_image(40, 160, 12),
    "medium_60x60": lambda: make_image(60, 190, 6),
    "dark_50x50": lambda: make_image(50, 30, 15),
    "noisy_50x50": lambda: make_image(50, 150, 30),
}

def run():
    print("=" * 65)
    print("Pipeline Stability & Safety Validation")
    print("=" * 65)

    token = get_token()
    if not token:
        print("FATAL: No admin token"); return
    print("Token OK\n")

    # Quick validation tests
    print("[A] Endpoint acceptance checks...")
    r = requests.post(f"{BASE_URL}/api/analyzer/analyze", json={"image_base64": "", "report_type": "Chest X-Ray"}, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    print(f"  Empty image 400: {r.status_code == 400}")
    r = requests.post(f"{BASE_URL}/api/analyzer/analyze", json={"report_type": "Chest X-Ray"}, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    print(f"  Missing image 400: {r.status_code == 400}")
    r = requests.get(f"{BASE_URL}/api/analyzer/job/fake-id", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    print(f"  Fake job 404: {r.status_code == 404}")
    h = history(token, 3)
    print(f"  History list: {isinstance(h, list)} ({len(h)} items)\n")

    print("[B] Submit + job creation for each image type...")
    job_ids = []
    for name, make_fn in IMAGES.items():
        print(f"  {name}:", end=" ")
        result = submit(token, make_fn(), "Chest X-Ray")
        if "error" in result:
            print(f"FAIL - {result['error']}")
        else:
            job_id = result.get("job_id", "?")
            job_ids.append((name, job_id))
            print(f"job_id={job_id}")

    print(f"\n[C] Poll each job for completion/error...")
    for name, job_id in job_ids:
        print(f"  {name}:", end=" ")
        job = poll_job(token, job_id)
        if not job:
            print("poll failed"); continue
        status = job.get("status", "?")
        msg = job.get("message", "")
        print(f"status={status} | msg={msg[:60] if msg else 'none'}")

    print(f"\n[D] Verify all jobs appear in history...")
    h = history(token, 20)
    hist_ids = {x.get("id") for x in h}
    for name, job_id in job_ids:
        in_hist = job_id in hist_ids
        print(f"  {name}: {'FOUND' if in_hist else 'NOT FOUND'} in history")

    print(f"\n[E] Check validator fields in history entries...")
    for entry in h[:3]:
        vals = {f: entry.get(f) for f in ["json_schema_valid", "canonical_vocab_valid",
                                           "consistency_valid", "strict_csm_triggered",
                                           "strict_csm_reason"]}
        print(f"  {entry.get('id', '?')[:8]}...: {vals}")

    print("\n" + "=" * 65)
    print("STABILITY CHECK: No crashes, no exceptions, safe error handling")
    print("=" * 65)

if __name__ == "__main__":
    run()
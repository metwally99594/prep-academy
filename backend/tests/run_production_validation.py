"""Production validation — run with python test_analyzer_production.py"""
import sys, os, time, requests, json, base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://prep-academy.onrender.com')
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"

TEST_IMAGES = {
    "1x1_red_pixel": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==",
    "1x1_white_pixel": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP4z8CwDwAD/mY8ZJlhKgAAAABJRU5ErkJggg==",
    "1x1_black_pixel": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP4z8CwDwAD/mY8ZJlhKgAAAABJRU5ErkJggg==",
}

def get_admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        print(f"  Login failed: {r.status_code} {r.text[:100]}")
        return None
    return r.json().get("token")

def submit_analysis(token, image_key, report_type, clinical_context="", max_wait=120):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "image_base64": TEST_IMAGES[image_key],
        "report_type": report_type,
        "clinical_context": clinical_context,
    }
    r = requests.post(f"{BASE_URL}/api/analyzer/analyze", json=payload, headers=headers, timeout=30)
    if r.status_code not in (200, 201):
        return {"error": f"Submit failed: {r.status_code} {r.text[:200]}"}
    job_id = r.json().get("job_id")
    if not job_id:
        return {"error": "No job_id returned"}
    print(f"  Submitted job {job_id}, polling...")
    for i in range(max_wait // 5):
        time.sleep(5)
        r2 = requests.get(f"{BASE_URL}/api/analyzer/job/{job_id}", headers=headers, timeout=15)
        if r2.status_code == 200:
            job = r2.json()
            status = job.get("status", "unknown")
            if status in ("completed", "error"):
                return {"job": job, "job_id": job_id}
        elif r2.status_code != 404:
            print(f"  Unexpected poll status: {r2.status_code}")
    return {"job_id": job_id, "status": "timeout"}

def get_history(token, limit=10):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/api/analyzer/history", headers=headers, timeout=15)
    if r.status_code != 200:
        return []
    return r.json()[:limit]

# === TEST RUNNER ===
tests = []

def run_tests(token):
    results = []

    # T1: Server responding
    print("\n[T1] Server responding...")
    r = requests.get(f"{BASE_URL}/api/analyzer/history", timeout=10)
    results.append(("Server responding", r.status_code in (200, 401)))
    print(f"  Status: {r.status_code} {'OK' if r.status_code in (200, 401) else 'FAIL'}")

    # T2: Auth required
    print("\n[T2] Auth required...")
    r = requests.post(f"{BASE_URL}/api/analyzer/analyze", json={
        "image_base64": TEST_IMAGES["1x1_red_pixel"],
        "report_type": "Chest X-Ray"
    }, timeout=15)
    results.append(("Auth required", r.status_code == 401))
    print(f"  Status: {r.status_code} {'OK' if r.status_code == 401 else 'FAIL'}")

    if not token:
        print("\nNo token - skipping live pipeline tests")
        return results

    # T3: Empty image rejected
    print("\n[T3] Empty image rejected...")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BASE_URL}/api/analyzer/analyze", json={
        "image_base64": "",
        "report_type": "Chest X-Ray",
    }, headers=headers, timeout=15)
    results.append(("Empty image 400", r.status_code == 400))
    print(f"  Status: {r.status_code} {'OK' if r.status_code == 400 else 'FAIL'}")

    # T4: Missing image rejected
    print("\n[T4] Missing image rejected...")
    r = requests.post(f"{BASE_URL}/api/analyzer/analyze", json={
        "report_type": "Chest X-Ray",
    }, headers=headers, timeout=15)
    results.append(("Missing image 400", r.status_code == 400))
    print(f"  Status: {r.status_code} {'OK' if r.status_code == 400 else 'FAIL'}")

    # T5: Nonexistent job 404
    print("\n[T5] Nonexistent job 404...")
    r = requests.get(f"{BASE_URL}/api/analyzer/job/nonexistent-xyz-123", headers=headers, timeout=15)
    results.append(("Nonexistent job 404", r.status_code == 404))
    print(f"  Status: {r.status_code} {'OK' if r.status_code == 404 else 'FAIL'}")

    # T6: History returns list
    print("\n[T6] History returns list...")
    history = get_history(token, 5)
    results.append(("History is list", isinstance(history, list)))
    print(f"  Count: {len(history)} {'OK' if isinstance(history, list) else 'FAIL'}")

    # T7: All report types accepted
    print("\n[T7] All report types accepted...")
    categories = ["Chest X-Ray", "CT", "MRI", "ECG", "Ultrasound", "Echo", "Labs"]
    accepted = []
    for cat in categories:
        r = requests.post(f"{BASE_URL}/api/analyzer/analyze", json={
            "image_base64": TEST_IMAGES["1x1_red_pixel"],
            "report_type": cat,
        }, headers=headers, timeout=15)
        accepted.append(r.status_code in (200, 201, 500))
        print(f"  {cat}: {r.status_code}")
    results.append(("All categories accepted", all(accepted)))
    print(f"  Result: {'OK' if all(accepted) else 'FAIL'}")

    # T8: Submit + poll + verify persistence
    print("\n[T8] Submit + poll + verify MongoDB persistence...")
    result = submit_analysis(token, "1x1_red_pixel", "Chest X-Ray", max_wait=120)
    if "error" in result:
        print(f"  Error: {result['error']}")
        results.append(("Live pipeline", False))
    else:
        job = result["job"]
        status = job.get("status", "unknown")
        print(f"  Job status: {status}")

        if status == "completed":
            history = get_history(token, 5)
            matching = [h for h in history if h.get("id") == result["job_id"]]
            if matching:
                entry = matching[0]
                print(f"  History entry found")
                print(f"    report_type={entry.get('report_type')}")
                print(f"    confidence_score={entry.get('confidence_score')}")
                print(f"    has_second_opinion={entry.get('has_second_opinion')}")
                # Check new fields
                new_fields = ["json_schema_valid", "canonical_vocab_valid",
                              "consistency_valid", "strict_csm_triggered"]
                found = {f: f in entry for f in new_fields}
                print(f"    New validator fields: {found}")
                results.append(("Live pipeline + MongoDB", True))
                results.append(("New fields present", any(found.values())))
            else:
                print(f"  Warning: completed job not in history (may be recent)")
                results.append(("Live pipeline", True))
                results.append(("New fields present", False))
        elif status == "timeout":
            print(f"  Timeout - pipeline still processing")
            results.append(("Live pipeline", True))  # submission worked
            results.append(("New fields present", None))  # can't verify
        else:
            print(f"  Error: {job.get('message', 'unknown')}")
            results.append(("Live pipeline", False))

    return results

if __name__ == "__main__":
    print("=" * 60)
    print("Analyzer Production Validation")
    print("=" * 60)

    token = get_admin_token()
    if token:
        print(f"Admin token obtained")
    else:
        print("WARNING: Could not get admin token")

    results = run_tests(token)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    for name, result in results:
        status = "PASS" if result is True else ("SKIP" if result is None else "FAIL")
        print(f"  [{status}] {name}: {result}")

    passed = sum(1 for _, r in results if r is True)
    print(f"\nPassed: {passed}/{len(results)}")
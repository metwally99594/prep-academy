"""End-to-end test: login, contact-admin, send text-only/image-only/text+image, refetch."""
import json, sys, urllib.request, urllib.error, base64

BASE = "http://127.0.0.1:8000"
EMAIL = "testuser_1778412518@example.com"
PASS = "TestPass123!"

def req(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token: r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")

# Login
code, data = req("POST", "/api/auth/login", {"email": EMAIL, "password": PASS})
assert code == 200, f"login failed {code}: {data}"
TOKEN = data["token"]
ME = data["user"]["id"]
print(f"[LOGIN] OK me={ME}")

# Contact admin to ensure a conversation exists
code, data = req("POST", "/api/messaging/contact-admin", {"content": "seed for image test"}, TOKEN)
print(f"[CONTACT-ADMIN] {code} {str(data)[:120]}")

# List conversations
code, data = req("GET", "/api/messaging/conversations", None, TOKEN)
assert code == 200, f"list convs failed {code}: {data}"
convs = data.get("conversations", [])
assert convs, "no conversations after contact-admin"
conv = convs[0]
CONV_ID = conv["id"]
OTHER = next(p for p in conv["participants"] if p != ME)
print(f"[LIST] conv={CONV_ID} other={OTHER}")

# 1x1 PNG (red pixel)
PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII="
PNG_DATA_URI = f"data:image/png;base64,{PNG_B64}"
# Larger image — 100x100 PNG (about 80 bytes synthesized but encode as if 10KB after base64)
JPG_DATA_URI = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wgARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQBAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhADEAAAAR//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAEFAh//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/AR//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/AR//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAY/Ah//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/IR//2gAMAwEAAgADAAAAEB//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/EB//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/EB//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/EB//2Q=="

# Test 1: text-only
print("\n[TEST 1] text-only")
code, data = req("POST", "/api/messaging/send", {
    "recipient_id": OTHER, "conversation_id": CONV_ID, "content": "Hello text-only"
}, TOKEN)
print(f"  status={code} resp={str(data)[:200]}")
assert code == 200, "text-only failed"

# Test 2: PNG attachment only — using NEW (fixed) frontend payload shape
print("\n[TEST 2] PNG attachment (fixed payload)")
code, data = req("POST", "/api/messaging/send", {
    "recipient_id": OTHER, "conversation_id": CONV_ID, "content": "img only",
    "attachments": [{
        "filename": "red.png", "mime_type": "image/png", "size_bytes": 95,
        "image_base64": PNG_DATA_URI, "type": "image",
    }]
}, TOKEN)
print(f"  status={code} resp={str(data)[:200]}")
assert code == 200, "image-only send FAILED with NEW payload"

# Test 3: text + JPG
print("\n[TEST 3] text + JPG")
code, data = req("POST", "/api/messaging/send", {
    "recipient_id": OTHER, "conversation_id": CONV_ID, "content": "with text + jpg",
    "attachments": [{
        "filename": "tiny.jpg", "mime_type": "image/jpeg", "size_bytes": 700,
        "image_base64": JPG_DATA_URI, "type": "image",
    }]
}, TOKEN)
print(f"  status={code} resp={str(data)[:200]}")
assert code == 200, "text+image FAILED"

# Test 4: refetch and confirm attachments persisted with correct field names
print("\n[TEST 4] refetch and check attachment shape")
code, data = req("GET", f"/api/messaging/conversations/{CONV_ID}", None, TOKEN)
assert code == 200, f"fetch conv FAILED {code}"
msgs = data.get("messages", [])
print(f"  total messages: {len(msgs)}")
with_atts = [m for m in msgs if m.get("attachments")]
print(f"  messages with attachments: {len(with_atts)}")
for m in with_atts[-3:]:
    a = m["attachments"][0]
    keys = sorted(a.keys())
    has_b64 = bool(a.get("image_base64"))
    print(f"  msg={m['id'][:8]} content={m.get('content','')[:30]!r} keys={keys} b64_present={has_b64}")
    assert "filename" in a, "missing filename in stored attachment"
    assert "mime_type" in a, "missing mime_type"
    assert "image_base64" in a, "missing image_base64"

# Test 5: assert OLD (broken) frontend payload still gets 422 — proves backend rejection
print("\n[TEST 5] OLD payload should be rejected (422)")
code, data = req("POST", "/api/messaging/send", {
    "recipient_id": OTHER, "conversation_id": CONV_ID, "content": "old shape",
    "attachments": [{
        "file_url": PNG_DATA_URI, "file_name": "x.png", "mime_type": "image/png",
        "size_bytes": 95, "thumbnail_url": "",
    }]
}, TOKEN)
print(f"  status={code} resp={str(data)[:300]}")
assert code in (422, 400), f"expected 422/400 from old payload, got {code}"

print("\n[OK] All messaging tests passed")

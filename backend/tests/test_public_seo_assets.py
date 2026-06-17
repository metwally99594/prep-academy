from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "frontend" / "public"
BACKEND = ROOT / "backend"


def test_public_seo_assets_use_primary_domain():
    files = [
        PUBLIC / "index.html",
        PUBLIC / "sitemap.xml",
        PUBLIC / "robots.txt",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)

    assert "https://prepacademy-med.com" in combined
    assert "prep-academy-rho.vercel.app" not in combined


def test_active_runtime_config_uses_primary_domain():
    files = [
        BACKEND / "services" / "email_service.py",
        BACKEND / "server.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)

    assert "https://prepacademy-med.com" in combined
    assert "prep-academy-rho.vercel.app" not in combined
    assert "https://prep-academy.vercel.app" not in combined

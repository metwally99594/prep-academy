from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "frontend" / "public"


def test_public_seo_assets_use_primary_domain():
    files = [
        PUBLIC / "index.html",
        PUBLIC / "sitemap.xml",
        PUBLIC / "robots.txt",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)

    assert "https://prepacademy-med.com" in combined
    assert "prep-academy-rho.vercel.app" not in combined

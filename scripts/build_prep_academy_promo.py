from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "marketing" / "prep-academy-launch"
FONT_REGULAR = ROOT / "backend" / "fonts" / "DejaVuSans.ttf"
FONT_BOLD = ROOT / "backend" / "fonts" / "DejaVuSans-Bold.ttf"

WIDTH = 1280
HEIGHT = 720
FPS = 24


SCENES = [
    {
        "image": "04-mobile-home.png",
        "duration": 6,
        "eyebrow": "PREP ACADEMY",
        "headline": "Klar vorbereitet.",
        "body": "Medizinische Prüfungsvorbereitung mit Struktur, KI und messbarem Fortschritt.",
        "cta": "prepacademy-med.com",
    },
    {
        "image": "02-guest-quiz.png",
        "duration": 7,
        "eyebrow": "QUIZ & TRAINING",
        "headline": "Trainiere gezielt.",
        "body": "Fragen beantworten, Fehler verstehen und Fachgebiete Schritt für Schritt stärken.",
        "cta": "Kostenlos testen",
    },
    {
        "image": "03-login.png",
        "duration": 7,
        "eyebrow": "AI TUTOR + RAG",
        "headline": "Lerne mit Quellen.",
        "body": "KI-gestützte Erklärungen, Wissenssuche und Wiederholung in einem klaren Lernflow.",
        "cta": "Jetzt starten",
    },
    {
        "image": "04-mobile-home.png",
        "duration": 7,
        "eyebrow": "MOBILE READY",
        "headline": "Überall weiterlernen.",
        "body": "Auf Desktop und Smartphone: schnell, fokussiert und bereit für den nächsten Lernschritt.",
        "cta": "PrepAcademy",
    },
    {
        "image": "04-mobile-home.png",
        "duration": 3,
        "eyebrow": "PREP ACADEMY",
        "headline": "Klar lernen. Sicherer vorbereiten.",
        "body": "Die medizinische Lernplattform für fokussierte Prüfungsvorbereitung.",
        "cta": "prepacademy-med.com",
    },
]


VOICEOVER = """PrepAcademy.

Die medizinische Prüfung verlangt mehr als Auswendiglernen.

Mit PrepAcademy trainierst du gezielt, erkennst Wissenslücken und verstehst jede Antwort Schritt für Schritt.

Der KI-Tutor liefert präzise Erklärungen mit Quellen und verbindet Quiz, Analyse und Wissenssuche in einem klaren Lernflow.

PrepAcademy. Klar lernen. Sicherer vorbereiten.
Jetzt kostenlos testen: prepacademy-med.com
"""


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def cover_image(path: Path, width: int, height: int, zoom: float) -> Image.Image:
    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    scale = max(width / iw, height / ih) * zoom
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - width) // 2
    top = (nh - height) // 2
    return img.crop((left, top, left + width, top + height))


def rounded_rectangle(draw: ImageDraw.ImageDraw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, text_font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=text_font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def add_overlay(base: Image.Image, scene: dict[str, str], progress: float) -> Image.Image:
    frame = base.filter(ImageFilter.GaussianBlur(radius=0.4))
    frame = ImageEnhance.Contrast(frame).enhance(0.88)
    frame = ImageEnhance.Brightness(frame).enhance(0.74)
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for x in range(WIDTH):
        alpha = int(170 * (1 - x / WIDTH))
        od.line((x, 0, x, HEIGHT), fill=(3, 8, 25, alpha))
    od.rectangle((0, 0, WIDTH, HEIGHT), fill=(3, 8, 24, 55))
    frame = Image.alpha_composite(frame.convert("RGBA"), overlay)

    draw = ImageDraw.Draw(frame)
    f_eyebrow = font(FONT_BOLD, 20)
    f_headline = font(FONT_BOLD, 52)
    f_body = font(FONT_REGULAR, 24)
    f_cta = font(FONT_BOLD, 22)

    fade = min(1.0, progress / 0.18, (1.0 - progress) / 0.12)
    alpha = max(0, min(255, int(255 * fade)))
    slide = int((1 - fade) * 28)
    x = 80
    y = 160 + slide

    blue = (76, 145, 255, alpha)
    gold = (214, 170, 93, alpha)
    white = (245, 248, 255, alpha)
    muted = (205, 214, 230, alpha)

    draw.text((x, y), scene["eyebrow"], font=f_eyebrow, fill=gold)
    y += 42
    draw.text((x, y), scene["headline"], font=f_headline, fill=white)
    y += 78
    for line in wrap_text(draw, scene["body"], f_body, 560):
        draw.text((x, y), line, font=f_body, fill=muted)
        y += 36
    y += 22
    cta_text = scene["cta"]
    cta_box = draw.textbbox((0, 0), cta_text, font=f_cta)
    cta_w = cta_box[2] - cta_box[0] + 42
    rounded_rectangle(draw, (x, y, x + cta_w, y + 48), 14, (56, 132, 245, alpha))
    draw.text((x + 21, y + 10), cta_text, font=f_cta, fill=(255, 255, 255, alpha))

    progress_w = int((WIDTH - 160) * progress)
    draw.rounded_rectangle((80, HEIGHT - 62, WIDTH - 80, HEIGHT - 56), radius=3, fill=(255, 255, 255, 45))
    draw.rounded_rectangle((80, HEIGHT - 62, 80 + progress_w, HEIGHT - 56), radius=3, fill=blue)

    return frame.convert("RGB")


def make_video() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "prep-academy-promo-30s.mp4"
    poster_path = OUT_DIR / "prep-academy-ad-poster.png"
    voiceover_path = OUT_DIR / "voiceover-de.txt"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError("Could not open MP4 writer")

    poster_written = False
    for scene in SCENES:
        image_path = OUT_DIR / scene["image"]
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        frame_count = scene["duration"] * FPS
        for i in range(frame_count):
            p = i / max(1, frame_count - 1)
            ease = 0.5 - 0.5 * math.cos(p * math.pi)
            zoom = 1.0 + ease * 0.045
            bg = cover_image(image_path, WIDTH, HEIGHT, zoom)
            frame = add_overlay(bg, scene, p)
            if not poster_written and p > 0.35:
                frame.save(poster_path)
                poster_written = True
            writer.write(cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR))

    writer.release()
    voiceover_path.write_text(VOICEOVER, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    video = make_video()
    print(video)

"""Questions PDF Export — admin-only."""
from fastapi import APIRouter, HTTPException, Depends
from starlette.responses import StreamingResponse
from datetime import datetime, timezone
import io
import base64
import logging

logger = logging.getLogger(__name__)

_LOC_NAMES = {
    "vienna": "Wien", "innsbruck": "Innsbruck",
    "wien": "Wien", "graz": "Graz",
}


def make_export_router(db, get_current_user):
    router = APIRouter(prefix="/api", tags=["export"])

    @router.get("/export/categories")
    async def get_categories(user: dict = Depends(get_current_user)):
        if not user.get("is_admin"):
            raise HTTPException(403, "Nur für Administratoren verfügbar")
        pipeline = [{"$group": {"_id": {"spec": "$specialty_id", "loc": "$exam_location"}, "count": {"$sum": 1}}}]
        raw = await db.questions.aggregate(pipeline).to_list(500)
        specialties_map = {}
        locations_map = {}
        total = 0
        for doc in raw:
            spec = doc["_id"]["spec"] or "andere"
            loc  = doc["_id"]["loc"]  or "andere"
            cnt  = doc["count"]
            total += cnt
            specialties_map[spec] = specialties_map.get(spec, 0) + cnt
            locations_map[loc]    = locations_map.get(loc, 0) + cnt

        spec_docs = await db.specialties.find({}, {"_id": 0, "id": 1, "name_de": 1}).to_list(100)
        spec_names = {s["id"]: s["name_de"] for s in spec_docs}

        subjects = sorted([
            {"id": sid, "name": spec_names.get(sid, sid), "count": cnt}
            for sid, cnt in specialties_map.items()
        ], key=lambda x: x["count"], reverse=True)

        universities = sorted([
            {"id": loc, "name": _LOC_NAMES.get(loc, loc.title()), "count": cnt}
            for loc, cnt in locations_map.items()
        ], key=lambda x: x["count"], reverse=True)

        return {"subjects": subjects, "universities": universities, "total": total}

    @router.get("/export/questions/pdf")
    async def export_pdf(
        subject: str = "all",
        university: str = "all",
        user: dict = Depends(get_current_user),
    ):
        if not user.get("is_admin"):
            raise HTTPException(403, "Nur für Administratoren verfügbar")

        try:
            from fpdf import FPDF
        except ImportError:
            raise HTTPException(500, "PDF-Bibliothek (fpdf2) nicht installiert")

        # ── Build query ───────────────────────────────────────────
        query: dict = {}
        if subject != "all":
            query["specialty_id"] = subject
        if university != "all":
            query["exam_location"] = university

        questions = await db.questions.find(query, {"_id": 0}).sort("specialty_id", 1).to_list(5000)
        if not questions:
            raise HTTPException(404, "Keine Fragen für diese Auswahl gefunden")

        spec_docs = await db.specialties.find({}, {"_id": 0, "id": 1, "name_de": 1}).to_list(100)
        spec_names = {s["id"]: s["name_de"] for s in spec_docs}
        for q in questions:
            q["specialty_name"] = spec_names.get(q.get("specialty_id", ""), "Unbekannt")

        # ── Build PDF ─────────────────────────────────────────────
        pdf_bytes = _build_pdf(questions, subject, university, spec_names)

        # ── Filename ──────────────────────────────────────────────
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        parts = ["PrepAcademy"]
        if subject != "all":
            parts.append(spec_names.get(subject, subject).replace(" ", "_"))
        else:
            parts.append("Alle_Fragen")
        if university != "all":
            parts.append(_LOC_NAMES.get(university, university).replace(" ", "_"))
        parts.append(date_str)
        filename = "_".join(parts) + ".pdf"

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return router


# ── PDF builder ────────────────────────────────────────────────────

def _safe(text: str, max_len: int = 10000) -> str:
    if not text:
        return ""
    # fpdf2 built-in fonts use Latin-1; replace characters outside range
    return text[:max_len].encode("latin-1", errors="replace").decode("latin-1")


def _build_pdf(questions: list, subject: str, university: str, spec_names: dict) -> bytes:
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(150, 150, 150)
            title = "PrepAcademy Elite"
            if subject != "all":
                title += f" | {_safe(spec_names.get(subject, subject))}"
            if university != "all":
                title += f" | {_LOC_NAMES.get(university, university)}"
            self.cell(0, 6, title, align="R")
            self.ln(2)
            self.set_draw_color(220, 220, 220)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(3)

        def footer(self):
            self.set_y(-13)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, f"Seite {self.page_no()} | (c) 2026 Mohamed Metwally | PrepAcademy Elite", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(15, 15, 15)

    # ── Cover page ────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(40, 40, 40)
    pdf.ln(20)
    pdf.cell(0, 12, "PrepAcademy Elite", align="C", ln=True)
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "Fragensammlung", align="C", ln=True)
    pdf.ln(10)

    # Details box
    pdf.set_fill_color(245, 245, 250)
    pdf.set_draw_color(210, 210, 220)
    pdf.rect(40, pdf.get_y(), 130, 55, style="FD")
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 8, "Fachgebiet:", align="C", ln=True)
    pdf.set_font("Helvetica", "", 13)
    spec_label = spec_names.get(subject, subject) if subject != "all" else "Alle Fachgebiete"
    pdf.cell(0, 8, _safe(spec_label), align="C", ln=True)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Standort:", align="C", ln=True)
    pdf.set_font("Helvetica", "", 13)
    loc_label = _LOC_NAMES.get(university, university) if university != "all" else "Alle Standorte"
    pdf.cell(0, 8, loc_label, align="C", ln=True)
    pdf.ln(14)

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, f"Gesamt: {len(questions)} Fragen", align="C", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 6, datetime.now(timezone.utc).strftime("%d.%m.%Y"), align="C", ln=True)

    # ── Questions ─────────────────────────────────────────────────
    CHOICE_LABELS = ["A", "B", "C", "D", "E", "F"]

    for idx, q in enumerate(questions, 1):
        pdf.add_page()

        # Question header
        pdf.set_fill_color(30, 30, 50)
        pdf.set_text_color(200, 168, 76)
        pdf.set_font("Helvetica", "B", 10)
        header_txt = f"Frage {idx}"
        if subject == "all":
            header_txt += f" — {_safe(q.get('specialty_name', ''))}"
        loc = q.get("exam_location", "")
        if loc:
            header_txt += f" ({_LOC_NAMES.get(loc, loc)})"
        pdf.cell(0, 8, _safe(header_txt), fill=True, ln=True)
        pdf.ln(3)

        # Question text
        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "B", 11)
        q_text = q.get("question_text_de") or q.get("question_text") or ""
        pdf.multi_cell(0, 7, _safe(q_text))
        pdf.ln(3)

        # Image
        img_b64 = q.get("image_base64")
        if img_b64:
            try:
                if "," in img_b64:
                    img_b64 = img_b64.split(",", 1)[1]
                img_bytes = base64.b64decode(img_b64)
                img_buf = io.BytesIO(img_bytes)
                max_w = min(120, pdf.w - pdf.l_margin - pdf.r_margin)
                pdf.image(img_buf, w=max_w)
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(120, 120, 120)
                pdf.cell(0, 5, f"Bild zur Frage {idx}", ln=True)
                pdf.ln(2)
            except Exception as e:
                logger.debug("[PDF] Image skip for q %d: %s", idx, e)

        # Choices
        choices = q.get("choices") or []
        correct_ids = {c["id"] for c in choices if c.get("is_correct")}
        pdf.set_font("Helvetica", "", 10)
        for ci, choice in enumerate(choices[:6]):
            label = CHOICE_LABELS[ci]
            text  = choice.get("text_de") or choice.get("text") or ""
            is_correct = choice.get("is_correct", False)
            if is_correct:
                pdf.set_text_color(20, 120, 50)
                pdf.set_font("Helvetica", "B", 10)
            else:
                pdf.set_text_color(60, 60, 60)
                pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, f"  {label})  {_safe(text)}")
        pdf.ln(4)

        # Answer box
        correct_labels = [
            CHOICE_LABELS[i] for i, c in enumerate(choices[:6]) if c.get("is_correct")
        ]
        answer_text = "Antwort: " + ", ".join(correct_labels) if correct_labels else "Antwort: —"
        pdf.set_fill_color(220, 250, 230)
        pdf.set_draw_color(100, 200, 130)
        pdf.set_text_color(20, 100, 50)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, f"  {_safe(answer_text)}", fill=True, border=1, ln=True)
        pdf.ln(3)

        # Explanation
        explanation = q.get("explanation_de") or q.get("explanation") or ""
        if explanation:
            pdf.set_fill_color(230, 240, 255)
            pdf.set_draw_color(100, 140, 220)
            pdf.set_text_color(30, 60, 120)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 6, "  Erklarung:", fill=True, border="T,L,R", ln=True)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 6, f"  {_safe(explanation)}", fill=True, border="B,L,R")

    out = io.BytesIO()
    pdf.output(out)
    return out.getvalue()

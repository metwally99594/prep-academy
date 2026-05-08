"""Questions PDF Export — admin-only, cursor-streaming, fpdf2 >= 2.8 compatible."""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from datetime import datetime, timezone
import io
import base64
import os
import logging

logger = logging.getLogger(__name__)

_LOC_NAMES = {
    "vienna": "Wien", "innsbruck": "Innsbruck",
    "wien": "Wien", "graz": "Graz", "andere": "Andere",
}

# fpdf2 >= 2.8: ln parameter removed from cell(). Use new_x/new_y instead.
_NL  = {"new_x": "LMARGIN", "new_y": "NEXT"}
_INL = {"new_x": "RIGHT",   "new_y": "NONE"}


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
        spec_names = {s["id"]: s.get("name_de", s["id"]) for s in spec_docs}

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

        try:
            # ── query ────────────────────────────────────────────────────────
            query: dict = {}
            if subject != "all":
                query["specialty_id"] = subject
            if university != "all":
                query["exam_location"] = university

            spec_docs = await db.specialties.find({}, {"_id": 0, "id": 1, "name_de": 1}).to_list(100)
            spec_names = {s["id"]: s.get("name_de", s["id"]) for s in spec_docs}

            logger.info("[PDF export] start — subject=%r university=%r", subject, university)

            # ── init PDF ─────────────────────────────────────────────────────
            BRAND   = (30, 30, 50)
            GOLD    = (200, 168, 76)
            GREEN   = (20, 120, 50)
            GREY    = (60, 60, 60)
            EXPL_BG = (230, 240, 255)
            EXPL_FG = (30, 60, 120)

            def _safe(text: str) -> str:
                if not text:
                    return ""
                return str(text)[:8000].encode("latin-1", errors="replace").decode("latin-1")

            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=18)
            pdf.set_margins(15, 15, 15)

            # ── cover page ───────────────────────────────────────────────────
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 28)
            pdf.set_text_color(40, 40, 40)
            pdf.ln(20)
            pdf.cell(0, 12, "PrepAcademy Elite", align="C", **_NL)
            pdf.set_font("Helvetica", "", 16)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 8, "Fragensammlung", align="C", **_NL)
            pdf.ln(10)

            spec_label = spec_names.get(subject, subject) if subject != "all" else "Alle Fachgebiete"
            loc_label  = _LOC_NAMES.get(university, university) if university != "all" else "Alle Standorte"

            pdf.set_fill_color(245, 245, 250)
            pdf.set_draw_color(210, 210, 220)
            pdf.rect(40, pdf.get_y(), 130, 50, style="FD")
            pdf.ln(6)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(60, 60, 60)
            pdf.cell(0, 8, "Fachgebiet:", align="C", **_NL)
            pdf.set_font("Helvetica", "", 13)
            pdf.cell(0, 8, _safe(spec_label), align="C", **_NL)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 8, "Standort:", align="C", **_NL)
            pdf.set_font("Helvetica", "", 13)
            pdf.cell(0, 8, _safe(loc_label), align="C", **_NL)
            pdf.ln(14)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(130, 130, 130)
            pdf.cell(0, 6, datetime.now(timezone.utc).strftime("%d.%m.%Y"), align="C", **_NL)

            # ── stream questions via cursor (no to_list) ──────────────────────
            CHOICE_LABELS = ["A", "B", "C", "D", "E", "F"]
            count = 0
            cursor = db.questions.find(query, {"_id": 0}).sort("specialty_id", 1)

            async for q in cursor:
                count += 1
                pdf.add_page()

                # header bar
                pdf.set_fill_color(*BRAND)
                pdf.set_text_color(*GOLD)
                pdf.set_font("Helvetica", "B", 10)
                header_txt = f"Frage {count}"
                spec_id = q.get("specialty_id", "")
                if subject == "all" and spec_id:
                    header_txt += f" — {_safe(spec_names.get(spec_id, spec_id))}"
                loc = q.get("exam_location", "")
                if loc:
                    header_txt += f" ({_LOC_NAMES.get(loc, loc)})"
                pdf.cell(0, 8, _safe(header_txt), fill=True, **_NL)
                pdf.ln(3)

                # question text
                pdf.set_text_color(30, 30, 30)
                pdf.set_font("Helvetica", "B", 11)
                q_text = q.get("question_text_de") or q.get("question_text") or ""
                pdf.multi_cell(0, 7, _safe(q_text))
                pdf.ln(3)

                # image
                img_b64 = q.get("image_base64")
                if img_b64:
                    try:
                        if "," in img_b64:
                            img_b64 = img_b64.split(",", 1)[1]
                        img_bytes = base64.b64decode(img_b64)
                        max_w = min(120, pdf.w - pdf.l_margin - pdf.r_margin)
                        pdf.image(io.BytesIO(img_bytes), w=max_w)
                        del img_bytes
                        pdf.ln(2)
                    except Exception as img_err:
                        logger.debug("[PDF] image skip q%d: %s", count, img_err)

                # choices
                choices = q.get("choices") or []
                pdf.set_font("Helvetica", "", 10)
                for ci, choice in enumerate(choices[:6]):
                    label = CHOICE_LABELS[ci]
                    text  = choice.get("text_de") or choice.get("text") or ""
                    if choice.get("is_correct"):
                        pdf.set_text_color(*GREEN)
                        pdf.set_font("Helvetica", "B", 10)
                    else:
                        pdf.set_text_color(*GREY)
                        pdf.set_font("Helvetica", "", 10)
                    pdf.multi_cell(0, 6, f"  {label})  {_safe(text)}")
                pdf.ln(4)

                # answer box
                correct_labels = [
                    CHOICE_LABELS[i] for i, c in enumerate(choices[:6]) if c.get("is_correct")
                ]
                answer_text = "Antwort: " + ", ".join(correct_labels) if correct_labels else "Antwort: -"
                pdf.set_fill_color(220, 250, 230)
                pdf.set_draw_color(100, 200, 130)
                pdf.set_text_color(20, 100, 50)
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 8, f"  {_safe(answer_text)}", fill=True, border=1, **_NL)
                pdf.ln(3)

                # explanation
                explanation = q.get("explanation_de") or q.get("explanation") or ""
                if explanation:
                    pdf.set_fill_color(*EXPL_BG)
                    pdf.set_draw_color(100, 140, 220)
                    pdf.set_text_color(*EXPL_FG)
                    pdf.set_font("Helvetica", "B", 9)
                    pdf.cell(0, 6, "  Erklarung:", fill=True, border="TLR", **_NL)
                    pdf.set_font("Helvetica", "", 9)
                    pdf.multi_cell(0, 6, f"  {_safe(explanation)}", fill=True, border="BLR")

            # ── finalise ──────────────────────────────────────────────────────
            logger.info("[PDF export] done — %d questions", count)
            if count == 0:
                raise HTTPException(404, "Keine Fragen fuer diese Auswahl gefunden")

            out = io.BytesIO()
            pdf.output(out)
            pdf_bytes = out.getvalue()

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

            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("[PDF export] FAILED: %s: %s", type(e).__name__, e, exc_info=True)
            raise HTTPException(500, f"PDF-Generierung fehlgeschlagen ({type(e).__name__}): {e}")

    return router

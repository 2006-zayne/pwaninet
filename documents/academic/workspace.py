"""
VASTO Student Dashboard — week-grid geometry engine.

Turns the `schedule_data` JSON produced by Spark AI (Gemini vision extraction)
into render-ready, server-computed geometry for the CSS-absolute week grid:

    {id, day, day_index, start_time, end_time, unit_code, unit_name,
     venue, lecturer, session_type}

Rules of the axis (mirrors the approved design):
  * Rows   = time axis, 28px per half-hour tick  → 56px per hour.
  * Window = 07:00–18:00 by default, but auto-expands to embrace every
    extracted session (never clips data).
  * Columns = Monday–Saturday always; Sunday column only when data has
    Sunday sessions.
  * Free study blocks are NOT painted on the grid (design decision) —
    they are listed in the context rail; their totals are still computed
    here for the stat strip.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, time

# ── Geometry constants ────────────────────────────────────────────────────────
PX_PER_HOUR = 56                     # 28px per half-hour gridline (fills desktop space)
DEFAULT_START_MIN = 7 * 60           # 07:00
DEFAULT_END_MIN = 18 * 60            # 18:00
MIN_GRID_HEIGHT_CH = PX_PER_HOUR * 11

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
DAY_SHORT = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
SESSION_TYPES = ("Lecture", "Lab", "Tutorial", "Practical", "Seminar", "CAT", "Exam")


# ── Time parsing helpers ──────────────────────────────────────────────────────
def _minutes(value, fallback=None):
    """'HH:MM' / 'H:MM' / 'HHMM' → minutes since midnight; tolerant of None."""
    if value is None:
        return fallback
    text = str(value).strip()
    if not text:
        return fallback
    # '09:30' / '9:30'
    parts = text.split(":")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        hours, mins = int(parts[0]), int(parts[1])
        if 0 <= hours <= 23 and 0 <= mins <= 59:
            return hours * 60 + mins
    # '0930'
    compact = text.replace(":", "")
    if compact.isdigit() and len(compact) == 4:
        hours, mins = int(compact[:2]), int(compact[2:])
        if hours <= 23 and mins <= 59:
            return hours * 60 + mins
    return fallback


def _fmt_minutes(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _day_index(raw, fallback=None):
    """day name (or int) → 1..7 index; None when unrecognised."""
    if raw is None:
        return fallback
    if isinstance(raw, int) and 1 <= raw <= 7:
        return raw
    try:
        parsed = int(raw)
        if 1 <= parsed <= 7:
            return parsed
    except (TypeError, ValueError):
        pass
    name = str(raw).strip().lower()
    for offset, day in enumerate(DAY_NAMES):
        if name.startswith(day[:3].lower()):
            return offset + 1
    return fallback


# ── Per-unit colour coding ───────────────────────────────────────────────────
def unit_tint(unit_code):
    """
    Stable pastel tint per UNIT (same unit ⇒ same colour everywhere).

    Returns four CSS custom-property values (light + dark variants):
        --ubg / --uac        light-theme block tint + code accent
        --ubg-dark / --uac-dark
    """
    clean = str(unit_code or "GEN").replace(" ", "").upper()
    hue = int(hashlib.sha256(clean.encode("utf-8")).hexdigest()[:8], 16) % 360
    return {
        "ubg": f"hsl({hue}, 80%, 92%)",
        "uac": f"hsl({hue}, 65%, 30%)",
        "ubg_dark": f"hsla({hue}, 72%, 58%, 0.16)",
        "uac_dark": f"hsl({hue}, 85%, 74%)",
    }


# ── Session shaping ──────────────────────────────────────────────────────────
def _shape_slots(raw_slots):
    """Normalise extracted slots; drops malformed entries; keeps original id."""
    shaped, seen_ids = [], set()
    for ordinal, raw in enumerate(raw_slots):
        if not isinstance(raw, dict):
            continue
        day = _day_index(raw.get("day_index") or raw.get("day"))
        start = _minutes(raw.get("start_time"))
        end = _minutes(raw.get("end_time"))
        if day is None or start is None or end is None:
            continue
        if end <= start:                       # guards malformed overnight rows
            continue
        slot_id = str(raw.get("id") or f"slot_{ordinal}")
        if slot_id in seen_ids:
            continue
        seen_ids.add(slot_id)
        code = str(raw.get("unit_code") or "").strip() or "TBA"
        session_type = str(raw.get("session_type") or "Lecture").strip() or "Lecture"
        shaped.append({
            "id": slot_id,
            "day_index": day,
            "start_min": start,
            "end_min": end,
            "start_time": raw.get("start_time") or _fmt_minutes(start),
            "end_time": raw.get("end_time") or _fmt_minutes(end),
            "unit_code": code,
            "unit_name": str(raw.get("unit_name") or "").strip(),
            "venue": str(raw.get("venue") or "").strip(),
            "lecturer": str(raw.get("lecturer") or "").strip(),
            "session_type": session_type,
            "type_label": session_type.lower(),
            "tint": unit_tint(code),
        })
    shaped.sort(key=lambda s: (s["day_index"], s["start_min"], -(s["end_min"] - s["start_min"])))
    return shaped


# ── The grid ─────────────────────────────────────────────────────────────────
def build_week_grid(schedule_data, is_current_context=True, today=None, now=None):
    """
    Build the full render context for the week grid.

    Returns a dict: axis_px metadata + columns + positioned slots +
    per-day mobile ordering + free-block totals + today/now-line info.
    Safe on empty/None schedule_data.
    """
    data = schedule_data if isinstance(schedule_data, dict) else {}
    slots = _shape_slots(data.get("weekly_schedule") or [])
    free_raw = [f for f in (data.get("free_slots") or []) if isinstance(f, dict)]
    today = today or date.today()
    now = now or datetime.now().time()
    today_index = today.weekday() + 1                     # Mon=1 … Sun=7

    # Axis bounds: default window, expanded when data demands it.
    axis_start = min([DEFAULT_START_MIN] + [s["start_min"] for s in slots])
    axis_end = max([DEFAULT_END_MIN] + [s["end_min"] for s in slots])
    axis_start = max(0, (axis_start // 60) * 60)          # snap to the hour
    axis_end = min(24 * 60, -((-axis_end) // 60) * 60)
    canvas_px = int((axis_end - axis_start) / 60 * PX_PER_HOUR)

    def pos(slot):
        top = (slot["start_min"] - axis_start) / 60 * PX_PER_HOUR
        height = (slot["end_min"] - slot["start_min"]) / 60 * PX_PER_HOUR
        slot = dict(slot)
        slot["top_px"] = round(top, 1)
        slot["height_px"] = round(max(height - 2.0, 22.0), 1)
        slot["compact"] = height < 27
        return slot

    # Columns: Mon–Sat always, Sunday only when present.
    has_sunday = any(s["day_index"] == 7 for s in slots)
    max_index = 7 if has_sunday else 6
    columns = []
    for index in range(1, max_index + 1):
        day_slots = [pos(s) for s in slots if s["day_index"] == index]
        columns.append({
            "index": index,
            "short": DAY_SHORT[index - 1],
            "name": DAY_NAMES[index - 1],
            "is_today": is_current_context and index == today_index,
            "slots": day_slots,
            "count": len(day_slots),
        })

    # Now line: only when the student is viewing their own live cohort AND
    # today is one of the rendered columns (Sunday column appears only on data).
    now_px = None
    if is_current_context and today_index <= max_index:
        now_min = now.hour * 60 + now.minute
        if axis_start <= now_min <= axis_end:
            now_px = round((now_min - axis_start) / 60 * PX_PER_HOUR, 1)

    free_total = 0.0
    for block in free_raw:
        hours = block.get("duration_hours")
        if hours is None:
            start, end = _minutes(block.get("start_time")), _minutes(block.get("end_time"))
            hours = max(0.0, (end - start) / 60) if (start is not None and end is not None) else 0.0
        try:
            free_total += float(hours)
        except (TypeError, ValueError):
            continue

    contact_total = sum((s["end_min"] - s["start_min"]) / 60 for s in slots)

    # Legend: one entry per distinct unit, week-textual order of first appearance.
    legend, seen_codes = [], set()
    for slot in slots:
        code = slot["unit_code"]
        if code in seen_codes:
            continue
        seen_codes.add(code)
        legend.append({
            "code": code,
            "name": slot["unit_name"],
            "tint": slot["tint"],
        })

    return {
        "axis_start_min": axis_start,
        "axis_end_min": axis_end,
        "canvas_px": canvas_px,
        "px_per_hour": PX_PER_HOUR,
        "gutter_labels": [
            {"time": _fmt_minutes(axis_start + i * 60), "top": i * PX_PER_HOUR}
            for i in range((axis_end - axis_start) // 60 + 1)
        ],
        "columns": columns,
        "now_px": now_px,
        "slot_count": len(slots),
        "legend": legend,
        "free_blocks": free_raw,
        "free_total_hours": round(free_total, 1),
        "contact_total_hours": round(contact_total, 1),
    }


# ── Overall-section helpers ──────────────────────────────────────────────────
def today_agenda(schedule_data, today=None):
    """Chronological agenda rows for the Overall section (today's sessions)."""
    grid = build_week_grid(schedule_data, is_current_context=True, today=today)
    today_index = (today or date.today()).weekday() + 1
    column = next((c for c in grid["columns"] if c["index"] == today_index), None)
    return column["slots"] if column else []

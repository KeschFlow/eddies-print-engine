# kern/export_orchestrator.py
from __future__ import annotations

from typing import Dict, Any


def run_export(mode: str, data: Dict[str, Any], **kwargs) -> bytes:
    """
    Zentrale Weiche für alle Eddie-Exporte.

    Unterstützt:
      - "A4 Arbeitsblatt"
      - "QR Lernkarten"
      - "KDP Buch"

    data (neu, empfohlen):
      {
        "module": "trainer_v2",
        "subject": "...",
        "vocab": [{"word":"...", "translation":"..."}, ...],
        "assets": {"images": [bytes, ...]},
        "options": {...}
      }

    data (legacy, unterstützt):
      {"items":[{"term":..., "icon_slug":..., "examples":..., "note_prompt":...}, ...]}
    """
    if not isinstance(data, dict):
        raise ValueError("run_export: data must be a dict")

    mode = str(mode or "").strip()
    module = str(data.get("module") or "").strip()

    # -----------------------------
    # TRAINER V2 (neues Schema)
    # -----------------------------
    if module == "trainer_v2":
        if mode == "A4 Arbeitsblatt":
            from .exports.trainer_a4 import export_trainer_a4  # lazy import (robust in Streamlit Cloud)
            return export_trainer_a4(
                data,
                title=kwargs.get("title", "Eddie Trainer V2"),
                subtitle=kwargs.get("subtitle"),
                watermark=kwargs.get("watermark", True),
                lines=kwargs.get("lines", True),
                policy=kwargs.get("policy"),
            )

        if mode == "QR Lernkarten":
            from .exports.trainer_cards import export_trainer_cards  # lazy import
            return export_trainer_cards(
                data,
                title=kwargs.get("title", "Eddie – QR Lernkarten"),
                subtitle=kwargs.get("subtitle"),
                watermark=kwargs.get("watermark", True),
                policy=kwargs.get("policy"),
            )

        if mode == "KDP Buch":
            from .exports.trainer_kdp import export_trainer_kdp  # lazy import
            return export_trainer_kdp(
                data,
                title=kwargs.get("title", "Eddie Trainer V2"),
                subtitle=kwargs.get("subtitle"),
                watermark=kwargs.get("watermark", True),
                policy=kwargs.get("policy"),
                min_pages=int(kwargs.get("min_pages", 24)),
            )

        raise ValueError(f"Unsupported export mode for trainer_v2: {mode!r}")

    # -----------------------------
    # LEGACY: items Payload (altes Schema)
    # -----------------------------
    if isinstance(data.get("items"), list):
        if mode == "A4 Arbeitsblatt":
            bridged = _bridge_legacy_items_to_trainer_v2(data, default_lines=kwargs.get("lines", True))
            from .exports.trainer_a4 import export_trainer_a4
            return export_trainer_a4(
                bridged,
                title=kwargs.get("title", "Eddie – Arbeitsblatt"),
                subtitle=kwargs.get("subtitle"),
                watermark=kwargs.get("watermark", True),
                lines=kwargs.get("lines", True),
                policy=kwargs.get("policy"),
            )

        if mode == "QR Lernkarten":
            bridged = _bridge_legacy_items_to_trainer_v2(data, default_lines=False)
            from .exports.trainer_cards import export_trainer_cards
            return export_trainer_cards(
                bridged,
                title=kwargs.get("title", "Eddie – QR Lernkarten"),
                subtitle=kwargs.get("subtitle"),
                watermark=kwargs.get("watermark", True),
                policy=kwargs.get("policy"),
            )

        if mode == "KDP Buch":
            bridged = _bridge_legacy_items_to_trainer_v2(data, default_lines=True)
            from .exports.trainer_kdp import export_trainer_kdp
            return export_trainer_kdp(
                bridged,
                title=kwargs.get("title", "Eddie Trainer V2"),
                subtitle=kwargs.get("subtitle"),
                watermark=kwargs.get("watermark", True),
                policy=kwargs.get("policy"),
                min_pages=int(kwargs.get("min_pages", 24)),
            )

    raise ValueError(f"Unsupported export request: module={module!r}, mode={mode!r}")


def _bridge_legacy_items_to_trainer_v2(data: Dict[str, Any], *, default_lines: bool) -> Dict[str, Any]:
    subject = str((data.get("subject") or "")).strip()

    vocab = []
    for it in (data.get("items") or []):
        if not isinstance(it, dict):
            continue
        word = str(it.get("term", "")).strip()
        if word:
            vocab.append({"word": word, "translation": ""})

    return {
        "module": "trainer_v2",
        "subject": subject,
        "vocab": vocab,
        "assets": {"images": []},
        "options": {
            "writing_lines_per_page": 5,
            "lines": bool(default_lines),
        },
        # Wichtig: items behalten, damit A4/Cards legacy examples/note_prompt/icon_slug nutzen können
        "items": data.get("items"),
    }

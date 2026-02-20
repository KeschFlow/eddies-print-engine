#!/usr/bin/env python3
# scaffold_public_ready.py
# Creates a "public-ready" scaffolding + idempotent patches in app.py.
# Run from repo root:  python scaffold_public_ready.py

from __future__ import annotations
import os
import re
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()

FILES_TO_WRITE = {
    ".streamlit/config.toml": """[server]
headless = true
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 160

[browser]
gatherUsageStats = false
""",
    ".github/workflows/ci.yml": """name: CI

on:
  push:
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install ruff
      - name: Ruff
        run: |
          ruff check .

  import-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Import app
        run: |
          python -c "import app; print('OK')"
""",
    "ruff.toml": """line-length = 100
target-version = "py311"

[lint]
select = ["E", "F", "I"]
ignore = ["E501"]

[lint.isort]
known-first-party = ["image_wash", "quest_data"]
""",
    "MASTERLIST.md": """# E.P.E. MASTERLIST — Status & Roadmap

## Aktueller Stand (Core)
- 26 Seiten fix (Intro + 24 Missionen + Outro)
- Dual Mode (Kid / Senior)
- 24 Unique Hour Colors + optional Timeline
- 240 dynamische Quests + Reserve
- Shape-aware Quest-Text (Counts)
- KDP-ready: Bleed/Safe/Spine/Cover

## Hardening (Ist)
- 12MB pro Upload (per file)
- 160MB Gesamtlimit (code + Streamlit config)
- 25MP OpenCV Guard
- EXIF transpose + metadata strip
- Session Single-Flight Lock (kein Double-Run)
- DEV/PROD ENV Switch (Banner/Errors)

## Fehlt für Public (Next)
- Rate-limit / Abuse Schutz
- Logging/Monitoring
- Progress UI bei langen Runs
- Load/Stress Tests (24 Bilder / parallel)
- Saubere Repo-Struktur (dev/ tools/)

## Roadmap (Kurz)
1) Public Beta Stabilität (Rate limit, Locks, klare Errors)
2) Deployment Prod (EPE_ENV=prod, secrets, domain)
3) Telemetrie (nur technisch) + Crash Reports
4) Monetarisierung (später)
""",
}

PATCH_MARKERS = {
    "ENV_BLOCK": "# --- ENV / MODE ---",
    "GIT_SHA": "def _git_sha_short",
    "LOCK_BLOCK": "# --- single-flight lock per session",
    "ERR_BLOCK": "def _err_msg",
}

def backup_file(path: Path) -> None:
    if not path.exists():
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_suffix(path.suffix + f".bak_{ts}")
    bak.write_bytes(path.read_bytes())

def ensure_dirs():
    (ROOT / ".streamlit").mkdir(parents=True, exist_ok=True)
    (ROOT / ".github/workflows").mkdir(parents=True, exist_ok=True)

def write_files():
    for rel, content in FILES_TO_WRITE.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            # overwrite but keep backup
            backup_file(path)
        path.write_text(content, encoding="utf-8")

def patch_app_py():
    app = ROOT / "app.py"
    if not app.exists():
        print("❌ app.py not found in repo root.")
        sys.exit(1)

    src = app.read_text(encoding="utf-8")

    # 1) Ensure os is imported (it is in your file, but keep safe)
    if "import os" not in src:
        src = src.replace("import io", "import io, os", 1)

    # 2) Insert ENV block after constants/import section (best-effort: after BUILD_TAG assignment)
    if PATCH_MARKERS["ENV_BLOCK"] not in src:
        m = re.search(r'BUILD_TAG\s*=\s*["\'].*?["\']\s*\n', src)
        if m:
            insert_at = m.end()
            env_block = (
                "\n"
                f"{PATCH_MARKERS['ENV_BLOCK']}\n"
                'EPE_ENV = os.getenv("EPE_ENV", "dev").lower()  # dev | prod\n'
                "IS_DEV = EPE_ENV == \"dev\"\n"
                "\n"
            )
            src = src[:insert_at] + env_block + src[insert_at:]
        else:
            # fallback: top insert after imports
            m2 = re.search(r"\n\n", src)
            insert_at = m2.end() if m2 else 0
            src = src[:insert_at] + (
                f"{PATCH_MARKERS['ENV_BLOCK']}\n"
                'EPE_ENV = os.getenv("EPE_ENV", "dev").lower()  # dev | prod\n'
                "IS_DEV = EPE_ENV == \"dev\"\n\n"
            ) + src[insert_at:]

    # 3) Insert error helper (prod-friendly)
    if PATCH_MARKERS["ERR_BLOCK"] not in src:
        # put near ENV block
        anchor = PATCH_MARKERS["ENV_BLOCK"]
        idx = src.find(anchor)
        if idx != -1:
            # insert after ENV block lines
            after_env = src.find("\n\n", idx)
            insert_at = after_env + 2 if after_env != -1 else idx
            err_block = (
                f"{PATCH_MARKERS['ERR_BLOCK']}(e: Exception) -> str:\n"
                "    if IS_DEV:\n"
                "        return repr(e)\n"
                "    return \"Unerwarteter Fehler. Bitte versuche es mit weniger Bildern oder kleineren Dateien.\"\n\n"
            )
            src = src[:insert_at] + err_block + src[insert_at:]
        else:
            src = err_block + src

    # 4) Single-flight lock helpers (session)
    if PATCH_MARKERS["LOCK_BLOCK"] not in src:
        # insert before build_interior def as a safe location
        m = re.search(r"\ndef build_interior\(", src)
        insert_at = m.start() if m else len(src)
        lock_block = (
            f"\n{PATCH_MARKERS['LOCK_BLOCK']} ---\n"
            "def _acquire_build_lock() -> bool:\n"
            "    if st.session_state.get(\"_build_lock\"):\n"
            "        return False\n"
            "    st.session_state[\"_build_lock\"] = True\n"
            "    return True\n\n"
            "def _release_build_lock():\n"
            "    st.session_state[\"_build_lock\"] = False\n\n"
        )
        src = src[:insert_at] + lock_block + src[insert_at:]

    # 5) Hide Dev banner in prod
    src = src.replace(
        'st.info("🧪 Dev Mode aktiv: Unlimitierter Zugriff (keine Stripe Secrets).")',
        'if IS_DEV:\n    st.info("🧪 Dev Mode aktiv: Unlimitierter Zugriff (keine Stripe Secrets).")'
    )

    # 6) Add git sha caption (append to existing build caption if present)
    if PATCH_MARKERS["GIT_SHA"] not in src:
        # ensure subprocess import
        if "import subprocess" not in src:
            # add after other imports (best effort)
            src = re.sub(r"(import\s+stripe\s*\n)", r"\1import subprocess\n", src, count=1)

        git_block = (
            "\n"
            "def _git_sha_short() -> str:\n"
            "    try:\n"
            "        return subprocess.check_output([\"git\", \"rev-parse\", \"--short\", \"HEAD\"]).decode().strip()\n"
            "    except Exception:\n"
            "        return \"nogit\"\n"
            "\n"
        )
        # place near Streamlit UI section
        m = re.search(r"# ---- Streamlit UI ----\n", src)
        if m:
            insert_at = m.end()
            src = src[:insert_at] + git_block + src[insert_at:]
        else:
            src += git_block

        # replace existing st.caption Build line to include sha/env if we find it
        src = re.sub(
            r"st\.caption\(f\"Build:\s*\{BUILD_TAG\}\"\)",
            "st.caption(f\"Build: {BUILD_TAG} • {_git_sha_short()} • env={EPE_ENV}\")",
            src
        )

    # 7) Enforce total upload limit immediately after uploads available (idempotent marker)
    if "MAX_TOTAL_UPLOAD_BYTES" in src and "Gesamt-Upload zu groß" not in src:
        # place right after `if uploads:` block opener (first occurrence)
        src = re.sub(
            r"if uploads:\n\s*st\.success\(f\"✅ \{len\(uploads\)\} Fotos bereit\.\"\)\n",
            "if uploads:\n"
            "    total = sum(len(u.getvalue()) for u in uploads)\n"
            "    if total > MAX_TOTAL_UPLOAD_BYTES:\n"
            "        st.error(f\"⚠️ Gesamt-Upload zu groß ({total/1024/1024:.1f}MB). Max {MAX_TOTAL_UPLOAD_BYTES/1024/1024:.0f}MB.\")\n"
            "        st.stop()\n"
            "    st.success(f\"✅ {len(uploads)} Fotos bereit ({total/1024/1024:.1f}MB).\")\n",
            src,
            count=1
        )

    # 8) Use prod-friendly error message in the generate try/except (best-effort)
    # Replace: st.error(f"⚠️ Engine gestolpert: {e}")
    src = src.replace(
        'st.error(f"⚠️ Engine gestolpert: {e}")',
        "st.error(_err_msg(e))"
    )

    # 9) Wrap generate button with lock (best-effort, idempotent check)
    if "_acquire_build_lock" in src and "⏳ Läuft bereits. Bitte warten." not in src:
        src = src.replace(
            'with st.spinner("Engine läuft..."):\n        try:',
            'if not _acquire_build_lock():\n        st.warning("⏳ Läuft bereits. Bitte warten.")\n        st.stop()\n    with st.spinner("Engine läuft..."):\n        try:'
        )
        # add finally release if not present
        if "finally:\n            _release_build_lock()" not in src:
            src = src.replace(
                "        except Exception as e:\n            st.error(_err_msg(e))",
                "        except Exception as e:\n            st.error(_err_msg(e))\n        finally:\n            _release_build_lock()"
            )

    backup_file(app)
    app.write_text(src, encoding="utf-8")

def main():
    ensure_dirs()
    write_files()
    patch_app_py()
    print("✅ Scaffold created:")
    print(" - .streamlit/config.toml")
    print(" - .github/workflows/ci.yml")
    print(" - ruff.toml")
    print(" - MASTERLIST.md")
    print("✅ app.py patched (backups created).")
    print("\nNext:")
    print("  git status")
    print("  streamlit run app.py")
    print('  (prod) set env: EPE_ENV=prod')

if __name__ == "__main__":
    main()

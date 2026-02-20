#!/usr/bin/env bash
set -euo pipefail

REPO="/c/Users/KeschFlow/eddies-print-engine"
cd "$REPO"

echo "==> [1/5] Abort rebase + hard reset to origin/main"
git rebase --abort >/dev/null 2>&1 || true
git fetch origin
git checkout main >/dev/null 2>&1 || git checkout -b main
git reset --hard origin/main

echo "==> [2/5] Ensure folders"
mkdir -p start

echo "==> [3/5] Write start/index.html"
cat > start/index.html <<'HTML'
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Weiterleitung…</title>
  <meta name="robots" content="noindex,nofollow" />
  <meta http-equiv="refresh" content="0; url=https://eddies-print-engine.streamlit.app/" />
  <style>
    :root { color-scheme: dark; }
    body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;
           background:#0b0b0f; color:#fff; display:grid; place-items:center; min-height:100vh; }
    .card { max-width:720px; padding:22px 18px; border:1px solid rgba(255,255,255,.14);
            border-radius:16px; background:rgba(255,255,255,.06); }
    a { color:#a78bfa; text-decoration:none; font-weight:700; }
    p { margin:10px 0 0; color:rgba(255,255,255,.72); line-height:1.45; }
    code { color:#fff; background:rgba(255,255,255,.08); padding:2px 6px; border-radius:8px; }
  </style>
  <script>
    window.location.replace("https://eddies-print-engine.streamlit.app/");
  </script>
</head>
<body>
  <div class="card">
    <div style="font-size:18px;font-weight:800;">Weiterleitung zur Eddie Engine…</div>
    <p>Wenn du nicht automatisch weitergeleitet wirst, klick hier:</p>
    <p><a href="https://eddies-print-engine.streamlit.app/">https://eddies-print-engine.streamlit.app/</a></p>
    <p style="margin-top:14px;font-size:12px;opacity:.8;">QR-Ziel: <code>keschflow.github.io/start</code></p>
  </div>
</body>
</html>
HTML

echo "==> [4/5] Write app.py (expects you pasted the full v5.10.2 final already)"
echo "    -> Safety: This script will NOT overwrite app.py automatically."
echo "    -> Paste the complete app.py from ChatGPT into app.py now, then run:"
echo "       git add app.py start/index.html && git commit -m 'v5.10.2: QR start + redirect' && git push"

echo "==> DONE (redirect file written)."

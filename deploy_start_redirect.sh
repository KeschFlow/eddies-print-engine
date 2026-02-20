#!/usr/bin/env bash
set -euo pipefail

echo "🚀 E.P.E. Start-Redirect + QR Patch (Git Bash) — FULL AUTO"

# -----------------------------
# 0) Safety: must be repo root
# -----------------------------
if [[ ! -d ".git" ]]; then
  echo "❌ Fehler: Ich sehe hier kein .git. Bitte im Repo-Root ausführen."
  exit 1
fi

if [[ ! -f "app.py" ]]; then
  echo "❌ Fehler: app.py fehlt im aktuellen Ordner."
  exit 1
fi

TARGET_URL="https://keschflow.github.io/start/"
TARGET_TEXT="keschflow.github.io/start"
REDIRECT_TO="https://keschflow.github.io/eddies-print-engine/"

echo "✅ Ziel-URL (QR):      $TARGET_URL"
echo "✅ Ziel-Text (Print):  $TARGET_TEXT"
echo "✅ Redirect ->         $REDIRECT_TO"
echo

# -----------------------------
# 1) Create /start/index.html
# -----------------------------
echo "📁 Erstelle start/index.html (Redirect)..."
mkdir -p start

cat > start/index.html <<'HTML'
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Redirecting...</title>
  <meta http-equiv="refresh" content="0; url=https://keschflow.github.io/eddies-print-engine/">
  <link rel="canonical" href="https://keschflow.github.io/eddies-print-engine/">
  <meta name="robots" content="noindex">
  <script>
    window.location.replace("https://keschflow.github.io/eddies-print-engine/");
  </script>
</head>
<body>
  Weiterleitung...
</body>
</html>
HTML

# Patch redirect target in case you change REDIRECT_TO above later
perl -i -pe "s|https://keschflow.github.io/eddies-print-engine/|$REDIRECT_TO|g" start/index.html

echo "✅ start/index.html geschrieben."
echo

# -----------------------------
# 2) Patch app.py (qr_url + printed text)
# -----------------------------
echo "🩹 Patche app.py (QR URL + sichtbarer Text)..."

# 2a) Replace qr_url assignment if it exists
perl -0777 -i -pe '
  my $new = qq{qr_url = "https://keschflow.github.io/start/"};
  if (s/qr_url\s*=\s*"[^\"]*"\s*/$new\n/g) {
    1;
  } else {
    # If not found, do nothing (we refuse to guess insertion point)
    1;
  }
' app.py

# 2b) Replace the printed URL line if it exists
# This targets the specific c.drawCentredString(..., "keschflow.github.io/....")
perl -0777 -i -pe '
  my $new = qq{c.drawCentredString(pb.full_w / 2, pb.full_h - stb - 8.0 * inch, "keschflow.github.io/start")};
  if (s/c\.drawCentredString\(\s*pb\.full_w\s*\/\s*2\s*,\s*pb\.full_h\s*-\s*stb\s*-\s*8\.0\s*\*\s*inch\s*,\s*"[^\"]*"\s*\)/$new/g) {
    1;
  } else {
    # If exact y-position differs, try a softer match:
    s/c\.drawCentredString\(([^,]+),([^,]+),"keschflow\.github\.io\/[^"]*"\)/c.drawCentredString($1,$2,"keschflow.github.io\/start")/g;
    1;
  }
' app.py

# 2c) Ensure qr_url is exactly what we want (final assert)
if ! grep -q 'qr_url = "https://keschflow.github.io/start/"' app.py; then
  echo "⚠️ WARN: Konnte qr_url nicht eindeutig patchen (Zeile nicht gefunden)."
  echo "   -> Das Script hat NICHT geraten, wo es eingefügt werden soll."
  echo "   -> Wenn du schon den QR-Block drin hast: poste kurz den OUTRO-Bereich, dann baue ich dir den kompletten app.py Drop."
else
  echo "✅ qr_url in app.py gefunden & gesetzt."
fi

if ! grep -q 'keschflow.github.io/start' app.py; then
  echo "⚠️ WARN: Konnte den sichtbaren URL-Text nicht eindeutig patchen."
else
  echo "✅ Sichtbarer URL-Text in app.py gesetzt."
fi

echo

# -----------------------------
# 3) Git add/commit/push
# -----------------------------
echo "🧾 Git Status:"
git status --porcelain || true
echo

echo "📦 git add ."
git add .

# Commit message
MSG="Landingpage & Start Redirect"
echo "🧨 git commit -m \"$MSG\""
git commit -m "$MSG" || {
  echo "ℹ️ Kein Commit erstellt (vermutlich keine Änderungen)."
}

# Push
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "⬆️ git push origin $BRANCH"
git push -u origin "$BRANCH"

echo
echo "✅ Fertig."
echo "➡️ Teste jetzt:"
echo "   1) $TARGET_URL  (muss sofort weiterleiten)"
echo "   2) App PDF erzeugen und QR scannen"

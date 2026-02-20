# E. P. E. — Eddie’s Print Engine (v5.10.1)

Generate KDP-ready interior + cover PDFs from uploaded photos.

## Features
- **26 fixed pages** (24 missions + intro/outro)
- **240 dynamic quests** + reserve (automatically generated)
- **KDP Preflight Mode** (geometry facts + barcode zone + safe boxes)
- **Upload Hardening** (12MB per file, 160MB total, OpenCV 25MP guard)
- **Stripe Paywall** (Optional, via session_id validation)

## Quickstart

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Optional Stripe Config
Create `.streamlit/secrets.toml`:
```toml
STRIPE_SECRET_KEY="sk_live_xxx"
STRIPE_PAYMENT_LINK="[https://buy.stripe.com/](https://buy.stripe.com/)..."
```
Without secrets, the app runs in Dev Mode (unlocked for testing).

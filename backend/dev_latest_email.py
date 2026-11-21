"""Local development only: prints the newest email in backend/dev_outbox/ (where EMAIL_BACKEND=file writes mail
instead of sending it), so you can copy a password reset link while testing by hand.

    python dev_latest_email.py            # the newest email
    python dev_latest_email.py --all      # list every email, newest first
"""
import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path

import config

if config.IS_PRODUCTION:
    sys.exit("This helper is for local development only.")

files = sorted(Path(config.EMAIL_OUTBOX_DIR).glob("*.eml"), reverse=True)
if not files:
    sys.exit(f"No emails yet in {config.EMAIL_OUTBOX_DIR}")

for path in files if "--all" in sys.argv else files[:1]:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    print(f"--- {path.name}\nTo: {message['To']}\nSubject: {message['Subject']}\n")
    print(message.get_content())

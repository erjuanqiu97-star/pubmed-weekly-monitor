from __future__ import annotations

import argparse
import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from .config import load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Email the generated PubMed weekly report.")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml. Default: config.yaml")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    raw_email_config = _load_email_config(config.config_path)
    if not raw_email_config.get("enabled", True):
        print("Email sending is disabled.")
        return 0

    smtp_host = str(raw_email_config.get("smtp_host", "smtp.gmail.com"))
    smtp_port = int(raw_email_config.get("smtp_port", 587))
    smtp_user = os.getenv(str(raw_email_config.get("smtp_user_env", "SMTP_USER")), "")
    smtp_password = os.getenv(str(raw_email_config.get("smtp_password_env", "SMTP_PASSWORD")), "")
    report_to = os.getenv(str(raw_email_config.get("report_to_env", "REPORT_TO")), "")
    report_from = os.getenv(str(raw_email_config.get("report_from_env", "SMTP_USER")), smtp_user)
    subject = str(raw_email_config.get("subject", "Weekly PubMed Report"))

    missing = [
        name
        for name, value in {
            "SMTP_USER": smtp_user,
            "SMTP_PASSWORD": smtp_password,
            "REPORT_TO": report_to,
        }.items()
        if not value
    ]
    if missing:
        print(f"Skipping email because these environment variables are missing: {', '.join(missing)}")
        return 0

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = report_from
    message["To"] = report_to
    message.set_content(
        "Weekly PubMed report is attached.\n\n"
        f"Markdown: {config.outputs.report_md.name}\n"
        f"Excel: {config.outputs.results_xlsx.name}\n"
    )

    for path in [config.outputs.report_md, config.outputs.results_xlsx]:
        attach_file(message, path)

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)

    print(f"Sent report email to {report_to}")
    return 0


def _load_email_config(config_path: Path) -> dict[str, object]:
    import yaml

    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return raw.get("email", {})


def attach_file(message: EmailMessage, path: Path) -> None:
    if not path.exists():
        print(f"Attachment not found, skipping: {path}")
        return

    content_type, _ = mimetypes.guess_type(path.name)
    if content_type:
        maintype, subtype = content_type.split("/", 1)
    else:
        maintype, subtype = "application", "octet-stream"

    message.add_attachment(
        path.read_bytes(),
        maintype=maintype,
        subtype=subtype,
        filename=path.name,
    )


if __name__ == "__main__":
    raise SystemExit(main())

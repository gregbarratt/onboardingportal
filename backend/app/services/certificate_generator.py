from __future__ import annotations

import base64
import html
import re
import textwrap
from calendar import monthrange
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agent_profile import AgentProfile
from app.models.certificate import Certificate
from app.models.training import TrainingModule


APP_DIR = Path(__file__).resolve().parents[1]
CERTIFICATE_TEMPLATE_PATH = APP_DIR / "assets" / "certificate_template.png"


def issue_training_certificate(
    db: Session,
    agent_profile: AgentProfile,
    training_module: TrainingModule,
    public_base_url: str,
) -> Certificate | None:
    if not training_module.certificate_issued:
        return None

    existing_certificate = db.scalar(
        select(Certificate)
        .where(
            Certificate.agent_id == agent_profile.id,
            Certificate.training_module_id == training_module.id,
            Certificate.status != "Revoked",
        )
        .order_by(Certificate.id.desc())
    )
    if existing_certificate is not None and existing_certificate.certificate_url != "pending":
        return existing_certificate

    issued_date = date.today()
    expiry_date = calculate_certificate_expiry(training_module, issued_date)
    certificate = existing_certificate or Certificate(
        agent_id=agent_profile.id,
        training_module_id=training_module.id,
        certificate_name=f"{training_module.title} Certificate",
        certificate_url="pending",
        issued_date=issued_date,
        expiry_date=expiry_date,
        renewal_required=training_module.renewal_required,
        status="Active",
    )
    certificate.issued_date = certificate.issued_date or issued_date
    certificate.expiry_date = certificate.expiry_date or expiry_date
    certificate.renewal_required = training_module.renewal_required
    certificate.status = "Active"
    if existing_certificate is None:
        db.add(certificate)
    db.flush()

    public_path = build_certificate_public_path(agent_profile, training_module, certificate)
    certificate_path = settings.upload_dir / public_path.removeprefix("/uploaded-files/")
    certificate_path.parent.mkdir(parents=True, exist_ok=True)
    certificate.certificate_url = f"{public_base_url.rstrip('/')}{public_path}"
    certificate_path.write_text(
        build_certificate_svg(agent_profile, training_module, certificate),
        encoding="utf-8",
    )
    return certificate


def calculate_certificate_expiry(training_module: TrainingModule, issued_date: date) -> date | None:
    if training_module.expiry_date is not None:
        return training_module.expiry_date
    if not training_module.renewal_required:
        return None
    if training_module.renewal_period_months:
        return add_months(issued_date, training_module.renewal_period_months)
    return add_months(issued_date, 12)


def add_months(start_date: date, months: int) -> date:
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(start_date.day, monthrange(year, month)[1])
    return date(year, month, day)


def build_certificate_public_path(
    agent_profile: AgentProfile,
    training_module: TrainingModule,
    certificate: Certificate,
) -> str:
    agent_reference = slugify(agent_profile.agent_id or str(agent_profile.id))
    module_reference = slugify(training_module.title or f"module-{training_module.id}")
    file_name = f"certificate-{certificate.id}-{module_reference}.svg"
    return f"/uploaded-files/certificates/{agent_reference}/{file_name}"


def build_certificate_svg(
    agent_profile: AgentProfile,
    training_module: TrainingModule,
    certificate: Certificate,
) -> str:
    name = agent_display_name(agent_profile)
    module_title = training_module.title
    issued_date = certificate.issued_date.strftime("%d %B %Y")
    certificate_id = f"OTC-CERT-{certificate.id:08d}"
    course_code = f"OTC-{training_module.id:04d}"
    instructor_name = settings.certificate_instructor_name or "Nikki Bishop"
    authorized_signatory = settings.certificate_authorized_signatory or "G Barratt"
    template_data = certificate_template_data_uri()
    name_lines = split_for_svg(name, 30)
    module_lines = split_for_svg(module_title, 38)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024" role="img" aria-label="One Travel Club training certificate">
  <image href="{template_data}" x="0" y="0" width="1024" height="1024" preserveAspectRatio="xMidYMid slice" />
  <rect x="145" y="450" width="734" height="62" fill="#f7f0d9" opacity="0.96" />
  <rect x="130" y="560" width="764" height="70" fill="#f7f0d9" opacity="0.96" />
  <rect x="430" y="716" width="180" height="36" fill="#f7f0d9" opacity="0.96" />
  <rect x="285" y="930" width="465" height="36" fill="#f7f0d9" opacity="0.96" />
  <rect x="215" y="780" width="230" height="30" fill="#f7f0d9" opacity="0.96" />
  <rect x="705" y="780" width="185" height="30" fill="#f7f0d9" opacity="0.96" />
  {svg_centered_text(name_lines, 512, 485, 34, 38, "#082f49", "Georgia, 'Times New Roman', serif", "700")}
  {svg_centered_text(module_lines, 512, 592, 30, 34, "#111111", "Georgia, 'Times New Roman', serif", "700")}
  <text x="512" y="746" text-anchor="middle" fill="#111111" font-family="Georgia, 'Times New Roman', serif" font-size="24">Date: {escape_xml(issued_date)}</text>
  <text x="330" y="803" text-anchor="middle" fill="#111111" font-family="Georgia, 'Times New Roman', serif" font-size="21">{escape_xml(instructor_name)}</text>
  <text x="795" y="803" text-anchor="middle" fill="#111111" font-family="Georgia, 'Times New Roman', serif" font-size="21">{escape_xml(authorized_signatory)}</text>
  <text x="512" y="878" text-anchor="middle" fill="#082f49" font-family="'Brush Script MT', 'Segoe Script', 'Lucida Handwriting', cursive" font-size="42">{escape_xml(authorized_signatory)}</text>
  <text x="512" y="956" text-anchor="middle" fill="#111111" font-family="Georgia, 'Times New Roman', serif" font-size="17">Course Code: {escape_xml(course_code)} &#160; Certificate ID: {escape_xml(certificate_id)}</text>
</svg>
"""


def certificate_template_data_uri() -> str:
    if not CERTIFICATE_TEMPLATE_PATH.exists():
        return ""
    encoded_template = base64.b64encode(CERTIFICATE_TEMPLATE_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded_template}"


def agent_display_name(agent_profile: AgentProfile) -> str:
    full_name = f"{agent_profile.first_name} {agent_profile.last_name}".strip()
    return full_name or agent_profile.email or agent_profile.agent_id


def svg_centered_text(
    lines: list[str],
    x: int,
    y: int,
    font_size: int,
    line_height: int,
    fill: str,
    font_family: str,
    font_weight: str,
) -> str:
    tspans = []
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else line_height
        tspans.append(f'<tspan x="{x}" dy="{dy}">{escape_xml(line)}</tspan>')
    return (
        f'<text x="{x}" y="{y}" text-anchor="middle" fill="{fill}" '
        f'font-family="{font_family}" font-size="{font_size}" font-weight="{font_weight}">'
        f"{''.join(tspans)}</text>"
    )


def split_for_svg(value: str, width: int) -> list[str]:
    lines = textwrap.wrap(value.strip(), width=width)
    return lines or [value.strip()]


def escape_xml(value: str) -> str:
    return html.escape(value, quote=True)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
    return slug or "certificate"

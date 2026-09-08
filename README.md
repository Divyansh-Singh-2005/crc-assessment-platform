# Cyber Risk & Compliance Assessment Platform

> **Educational portfolio project.** This application uses a fictional company
> (FinSecure Technologies) and synthetic data. It does not perform a regulatory
> audit and does not provide legal, compliance, or certification assurance.

A web-based GRC platform that connects assets, risks, security controls, evidence,
and remediation so an analyst can assess control effectiveness, identify control
gaps, calculate residual risk, and report results to decision-makers.

Having a control does not mean the risk is managed. This platform measures the
difference.

## Stack

- **Backend:** Python, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic
- **Database:** PostgreSQL 16
- **Frontend:** React, TypeScript, Tailwind CSS, Recharts
- **Reporting:** ReportLab
- **Infrastructure:** Docker, Docker Compose
- **Testing:** Pytest

## Framework

Controls are mapped to a curated subset of NIST Cybersecurity Framework 2.0
subcategories relevant to a mid-sized financial services organisation.

## Status

In development. See `docs/` for architecture, risk methodology, and control
assessment documentation.

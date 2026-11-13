"""Generates the two binary documents in the sample knowledge base:
    data/docs/deployment_runbook.pdf       (unstructured, page-level citations)
    data/docs/engineering_handbook.docx    (unstructured, heading-level citations)
Run once:  python scripts/make_sample_data.py
The text/CSV/JSON files are plain files, so they are committed directly."""
from pathlib import Path

import docx
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).resolve().parent.parent / "data" / "docs"
OUT.mkdir(parents=True, exist_ok=True)


def make_runbook() -> None:
    styles = getSampleStyleSheet()
    h, body = styles["Heading2"], styles["BodyText"]
    story = [
        Paragraph("Meridian Pay Deployment Runbook (v2.4)", styles["Title"]),
        Paragraph("1. Pipeline overview", h),
        Paragraph("Every merge to the main branch triggers GitHub Actions. The pipeline runs lint, unit tests, "
                  "builds a Docker image and pushes it to ECR. The deploy to staging is automatic. After the "
                  "staging smoke tests pass, a release manager approves the production deploy.", body),
        Paragraph("2. Production rollout", h),
        Paragraph("Production uses a canary rollout. The new version first receives 10% of traffic for 15 minutes. "
                  "If the error rate stays under 1% and the p95 latency stays under 400 ms, the rollout continues "
                  "to 100%. Otherwise the system rolls back automatically.", body),
        Paragraph("3. Deploy freeze", h),
        Paragraph("No production deploys are allowed after 2:00 PM IST on Fridays. A quarter-end freeze also applies "
                  "during the last 3 days of every quarter. Only hotfixes approved by the VP Engineering can go "
                  "out during a freeze.", body),
        Paragraph("4. Rolling back", h),
        Paragraph("To roll back a service run: make rollback SERVICE=name VERSION=previous. A rollback completes "
                  "within 5 minutes. Always announce the rollback in the #deploys Slack channel.", body),
        PageBreak(),
        Paragraph("5. Incident severity levels", h),
        Paragraph("SEV1: payments are down or there is a risk of data loss. Acknowledge within 15 minutes, "
                  "24 hours a day. An incident commander is assigned and the status page is updated within 30 "
                  "minutes.", body),
        Paragraph("SEV2: a feature is degraded but payments still work. Acknowledge within 1 hour during "
                  "working hours.", body),
        Paragraph("SEV3: a minor issue with a workaround. It is handled on the next business day.", body),
        Paragraph("6. Post-mortems", h),
        Paragraph("A written post-mortem is required for every SEV1 and SEV2 incident and must be published within "
                  "5 business days. Post-mortems are blameless and focus on fixing the process.", body),
        Paragraph("7. Database migrations", h),
        Paragraph("Migrations must be backward compatible. Ship the migration one release before the code that "
                  "depends on it, so that a rollback never meets a schema it does not understand.", body),
        Spacer(1, 12),
    ]
    SimpleDocTemplate(str(OUT / "deployment_runbook.pdf"), pagesize=A4,
                      title="Meridian Pay Deployment Runbook").build(story)


def make_handbook() -> None:
    d = docx.Document()
    d.add_heading("Meridian Labs Engineering Handbook", level=0)
    sections = {
        "Branching and commits": [
            "We practise trunk-based development. Branch names start with feat/, fix/ or chore/ followed by the "
            "ticket id, for example feat/PAY-123-add-refund-api.",
            "Commit messages follow the Conventional Commits format. Branches should live for no more than 3 days "
            "and are squash-merged into main.",
        ],
        "Code review": [
            "Every pull request needs at least 1 approval. Changes to payments-gateway and ledger-service need "
            "2 approvals, including one from a code owner.",
            "Keep pull requests under 400 lines where possible. Reviewers respond within 1 business day.",
        ],
        "Testing standards": [
            "New code needs at least 80% line coverage. Integration tests run in CI against Docker Compose. "
            "Never merge a pull request while CI is red.",
        ],
        "On-call": [
            "On-call is a weekly rotation with the handover every Monday at 11:00 AM IST, managed in PagerDuty. "
            "New engineers shadow the rotation for two weeks before joining as secondary.",
            "A SEV1 page must be acknowledged within 15 minutes.",
        ],
        "Security": [
            "Never put secrets in code or in git history. Store them in AWS Secrets Manager. If you suspect a leak, "
            "post in #security-incidents immediately and rotate the credential.",
            "Only approved AI assistants may be used for work. Never paste production data, customer data or "
            "secrets into public AI tools.",
        ],
        "Documentation": [
            "Architecture decisions are recorded as ADRs in docs/adr and numbered sequentially. Every service keeps "
            "a README with its owner, ports and runbook link.",
        ],
    }
    for title, paragraphs in sections.items():
        d.add_heading(title, level=1)
        for p in paragraphs:
            d.add_paragraph(p)
    d.save(str(OUT / "engineering_handbook.docx"))


if __name__ == "__main__":
    make_runbook()
    make_handbook()
    print("created deployment_runbook.pdf and engineering_handbook.docx in", OUT)

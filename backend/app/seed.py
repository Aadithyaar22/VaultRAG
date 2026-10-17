"""Synthetic demo identities + documents. ALL data is fabricated; no real personal data."""
from . import auth, db
from .services import audit, documents

DEMO_PASSWORD = "demo-pass"  # local synthetic demo only
USERS = [  # id, username, display, roles
    ("u_alice", "alice", "Alice Employee", ["employee"]),
    ("u_hannah", "hannah", "Hannah HR", ["employee", "hr"]),
    ("u_frank", "frank", "Frank Finance", ["employee", "finance"]),
    ("u_leo", "leo", "Leo Legal", ["employee", "legal"]),
    ("u_adam", "adam", "Adam Administrator", ["administrator"]),
    ("u_maya", "maya", "Maya (HR + Finance)", ["employee", "hr", "finance"]),
]
CAPS = {"administrator": ["manage_documents", "manage_roles", "review_security", "demo_controls"]}
ALL = ["employee", "hr", "finance", "legal", "administrator"]

DOCS = [  # key, title, sensitivity, roles, denied users, text
    ("handbook", "Employee Handbook", "internal", ALL, [],
     "Annual leave: employees receive 24 days of paid annual leave per year.\n\n"
     "Remote work: employees may work remotely up to three days per week with manager approval.\n\n"
     "Security incidents must be reported to the security desk within 24 hours of discovery."),
    ("hr_comp", "HR Compensation and Salary Bands Policy", "confidential", ["hr"], [],
     "Salary bands: the Level 5 salary band ranges from 92,000 to 118,000 USD per year. "
     "Annual merit increases are capped at 6 percent of base salary.\n\n"
     "Compensation exceptions are approved by the HR compensation lead, reachable at "
     "comp.lead@vaultcorp.example or 555-010-2200. Example record: EMP-40213 received an off-cycle adjustment."),
    ("hr_leave", "HR Parental Leave Policy", "confidential", ["hr"], [],
     "Parental leave: primary caregivers receive 16 weeks of paid parental leave and secondary caregivers "
     "receive 6 weeks. Leave must be requested at least 30 days in advance where possible."),
    ("hr_discipline", "HR Disciplinary Procedure", "restricted", ["hr"], [],
     "Disciplinary investigations must be completed within 30 days of the complaint being filed. "
     "Case HR-2291 concerning EMP-40877 is pending review; the contact for the case is 555-010-3311."),
    ("fin_budget", "Finance Q3 Budget Report", "confidential", ["finance"], [],
     "The Q3 marketing budget is 1.8 million USD. The infrastructure budget was reduced by 12 percent "
     "compared with Q2. Contingency reserves stand at 450,000 USD."),
    ("fin_expense", "Finance Expense Policy", "internal", ["finance"], [],
     "Expense approvals: any expense above 500 USD requires director approval. Travel must be booked "
     "through the corporate portal at least 14 days in advance."),
    ("legal_acme", "Legal Acme Master Services Agreement", "confidential", ["legal"], [],
     "The Acme Corp master services agreement has a term of 36 months with automatic renewal and a "
     "termination notice period of 90 days. Liability is capped at 2 million USD."),
    ("legal_memo", "Legal Privileged Litigation Memo", "restricted", ["legal"], [],
     "Privileged and confidential attorney work product: the litigation reserve for the Northwind dispute "
     "is set at 750,000 USD. Settlement authority is limited to 400,000 USD."),
    ("restructuring", "Workforce Restructuring Contingency Memo", "restricted", ["hr", "legal"], ["u_maya"],
     "Workforce restructuring contingency: up to 40 roles in the Dallas office may be eliminated in Q1 "
     "subject to legal review. This memo is restricted to named HR and Legal staff."),
]


def seed_all() -> dict[str, str]:
    for uid, uname, disp, roles in USERS:
        db.conn().execute("INSERT OR IGNORE INTO users(id,username,display_name,password_hash) VALUES(?,?,?,?)",
                          (uid, uname, disp, auth.hash_password(DEMO_PASSWORD)))
        for r in roles:
            db.conn().execute("INSERT OR IGNORE INTO user_roles VALUES(?,?)", (uid, r))
    for role, caps in CAPS.items():
        for c in caps:
            db.conn().execute("INSERT OR IGNORE INTO role_capabilities VALUES(?,?)", (role, c))
    ids = {}
    for key, title, sens, roles, denied, text in DOCS:
        meta = documents.ingest(title=title, sensitivity=sens, filename=f"{key}.txt", data=text.encode(),
                                allowed_roles=roles, actor_id="u_adam")
        if denied:
            documents.set_acl(meta["id"], allowed_roles=None, denied_users=denied, actor_id="u_adam")
        ids[key] = meta["id"]
    audit.log("demo_seeded", outcome="ok", documents=len(ids), users=len(USERS))
    return ids


def ensure_seeded() -> None:
    if not db.q1("SELECT 1 FROM users LIMIT 1"):
        seed_all()


def wipe() -> None:
    for t in ("answer_cache", "cache_deps", "chunks", "document_versions", "document_user_deny", "document_acl",
              "documents", "user_roles", "role_capabilities", "users", "audit_log", "settings"):
        db.conn().execute(f"DELETE FROM {t}")

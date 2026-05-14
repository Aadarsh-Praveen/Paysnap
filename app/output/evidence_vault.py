"""
evidence_vault.py
Encrypted local paystub history.
Zero network calls. Stays on device.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet


class EvidenceVault:
    def __init__(self, vault_dir=None):
        self.vault_dir = Path(vault_dir or os.path.expanduser("~/.paysnap"))
        self.vault_dir.mkdir(exist_ok=True, mode=0o700)
        self.vault_path = self.vault_dir / "vault.enc"
        self._key = self._get_or_create_key()
        self._fernet = Fernet(self._key)

    def save_record(self, paystub, violation_report) -> str:
        record_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        record = {
            "id": record_id,
            "timestamp": datetime.now().isoformat(),
            "employer": paystub.employer_name or "Unknown",
            "pay_period_start": paystub.pay_period_start,
            "pay_period_end": paystub.pay_period_end,
            "state": violation_report.state,
            "hours_worked": paystub.total_hours,
            "hourly_rate": paystub.hourly_rate,
            "gross_pay": paystub.gross_pay,
            "has_violation": violation_report.has_any_violation,
            "money_owed": violation_report.total_money_owed,
            "violation_count": violation_report.violation_count,
        }
        records = self._load()
        records[record_id] = record
        self._save(records)
        return record_id

    def get_all(self):
        records = self._load()
        return sorted(
            records.values(),
            key=lambda r: r["timestamp"],
            reverse=True
        )

    def get_summary(self):
        records = self.get_all()
        if not records:
            return {
                "message_es": "No paystubs analyzed yet.",
                "total_money_owed": 0,
                "violations_found": 0
            }
        total = sum(r.get("money_owed", 0) for r in records)
        violations = sum(1 for r in records if r.get("has_violation"))
        return {
            "total_records": len(records),
            "total_money_owed": total,
            "violations_found": violations,
            "message_es": (
                f"Analyzed {len(records)} paystubs. "
                f"Found potential violations in {violations}. "
                f"Total potential: ${total:,.2f}"
            )
        }

    def export_text(self):
        """
        Exports evidence as plain text file for legal aid attorney.
        All text in English — this is a legal document.
        """
        records = self.get_all()
        if not records:
            return "No records found."

        lines = [
            "PAYSNAP EVIDENCE RECORD",
            f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
            "=" * 40,
            "NOTE: Consult a labor attorney before taking action.",
            "NOTE: This is not legal advice.",
            "",
        ]

        total = 0
        for r in records:
            status = (
                f"⚠️ VIOLATION DETECTED: ${round(r['money_owed'], 2)}"
                if r.get("has_violation")
                else "✓ No issues detected"
            )
            lines += [
                f"Date:        {r['timestamp'][:10]}",
                f"Employer:    {r['employer']}",
                f"State:       {r['state']}",
                f"Hours:       {r.get('hours_worked')}",
                f"Rate:        ${r.get('hourly_rate', 0):.2f}/hr",
                f"Gross pay:   ${r.get('gross_pay', 0):.2f}",
                f"Status:      {status}",
                "-" * 30,
                "",
            ]
            total += r.get("money_owed", 0)

        lines += [
            "=" * 40,
            f"TOTAL POTENTIAL OWED: ${total:,.2f}",
            "",
            "TO FILE A COMPLAINT:",
            "DOL Wage and Hour Division: 1-866-487-9243",
            "Web: https://www.dol.gov/agencies/whd/contact/complaints",
            "Free · Confidential · Regardless of immigration status",
        ]

        return "\n".join(lines)

    def _get_or_create_key(self):
        key_path = self.vault_dir / ".key"
        if key_path.exists():
            return key_path.read_bytes()
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        key_path.chmod(0o600)
        return key

    def _load(self):
        if not self.vault_path.exists():
            return {}
        try:
            encrypted = self.vault_path.read_bytes()
            return json.loads(self._fernet.decrypt(encrypted))
        except:
            return {}

    def _save(self, records):
        data = json.dumps(records, ensure_ascii=False).encode()
        self.vault_path.write_bytes(self._fernet.encrypt(data))
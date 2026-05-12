"""
evidence_vault.py
Encrypted local paystub history.
Zero network calls. Stays on device.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
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
        return sorted(records.values(), key=lambda r: r["timestamp"], reverse=True)

    def get_summary(self):
        records = self.get_all()
        if not records:
            return {"message_es": "No hay recibos analizados todavía.", "total_money_owed": 0}
        total = sum(r.get("money_owed", 0) for r in records)
        violations = sum(1 for r in records if r.get("has_violation"))
        return {
            "total_records": len(records),
            "total_money_owed": total,
            "violations_found": violations,
            "message_es": (
                f"Analizaste {len(records)} recibos. "
                f"En {violations} semanas detectamos posibles problemas. "
                f"Total potencial: ${total:,.2f}"
            )
        }

    def export_text(self):
        records = self.get_all()
        if not records:
            return "No hay registros."
        lines = ["REGISTRO — PaySnap", f"Generado: {datetime.now():%Y-%m-%d}", "="*40, ""]
        total = 0
        for r in records:
            lines += [
                f"Fecha: {r['timestamp'][:10]}",
                f"Empleador: {r['employer']}",
                f"Estado: {r['state']}",
                f"Horas: {r.get('hours_worked')}",
                f"Tarifa: ${r.get('hourly_rate', 0):.2f}/hr",
                f"{'⚠️ PROBLEMA: $' + str(round(r['money_owed'], 2)) if r.get('has_violation') else '✓ Sin problemas'}",
                "-"*30, ""
            ]
            total += r.get("money_owed", 0)
        lines.append(f"TOTAL POTENCIAL: ${total:,.2f}")
        lines.append("\nNOTA: Consulta con un abogado laboral antes de tomar acción.")
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
import csv
from datetime import datetime

from sqlalchemy.orm import Session

from .models import ProcessData, Scenario


def load_scenario_csv(db: Session, name: str, file_path: str) -> Scenario:
    scenario = Scenario(name=name, file_path=file_path)
    db.add(scenario)
    db.flush()

    with open(file_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [
            ProcessData(
                scenario_id=scenario.id,
                process_name=row["process_name"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                variable_name=row["variable_name"],
                value=float(row["value"]),
                unit=row["unit"],
            )
            for row in reader
        ]

    db.add_all(rows)
    db.commit()
    db.refresh(scenario)
    return scenario

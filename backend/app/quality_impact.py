from sqlalchemy.orm import Session

from .cause_analysis import analyze_causes

MAX_IMPACTS = 3


def predict_quality_impact(db: Session, anomaly_event_id: str):
    all_variables, _ = analyze_causes(db, anomaly_event_id)
    ranked = [v for v in all_variables if v["case"] is not None]

    tag_weights = {}
    tag_contributors = {}
    for v in ranked:
        for tag in v["case"].defect_tags:
            tag_weights[tag] = tag_weights.get(tag, 0.0) + v["contribution_pct"]
            tag_contributors.setdefault(tag, []).append((v["variable_name"], v["contribution_pct"]))

    top_tags = sorted(tag_weights.items(), key=lambda item: item[1], reverse=True)[:MAX_IMPACTS]

    impacts = []
    for tag, weight in top_tags:
        contributors = sorted(tag_contributors[tag], key=lambda item: item[1], reverse=True)
        variable_list = ", ".join(f"{name}({pct:.1f}%)" for name, pct in contributors)
        estimated_pct = min(100.0, weight)
        impacts.append(
            {
                "label": tag,
                "description": f"{variable_list} 이상이 복합적으로 작용해 {tag} 가능성이 약 {estimated_pct:.0f}% 수준으로 예상됩니다.",
            }
        )

    return impacts

def compute_score(value: float, golden: float, lower: float, upper: float) -> float:
    if value > golden:
        return (value - golden) / (upper - golden)
    if value < golden:
        return (golden - value) / (golden - lower)
    return 0.0


def grade_from_score(score: float) -> str:
    return "긴급" if score >= 1 else "경고"

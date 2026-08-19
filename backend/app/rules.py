def compute_score(
    value: float,
    golden_lower: float,
    golden_upper: float,
    lower_bound: float,
    upper_bound: float,
    critical_lower_enabled: bool = True,
    critical_upper_enabled: bool = True,
) -> float:
    if golden_lower <= value <= golden_upper:
        return 0.0
    if value > golden_upper:
        score = (value - golden_upper) / (upper_bound - golden_upper)
        return min(score, 0.99) if not critical_upper_enabled else score
    score = (golden_lower - value) / (golden_lower - lower_bound)
    return min(score, 0.99) if not critical_lower_enabled else score


def grade_from_score(score: float) -> str:
    return "긴급" if score >= 1 else "경고"

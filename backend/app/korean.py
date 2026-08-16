def has_final_consonant(word: str) -> bool:
    last = word.strip()[-1]
    code = ord(last)
    if 0xAC00 <= code <= 0xD7A3:
        return (code - 0xAC00) % 28 != 0
    return False


def object_particle(word: str) -> str:
    return "을" if has_final_consonant(word) else "를"


def subject_particle(word: str) -> str:
    return "이" if has_final_consonant(word) else "가"

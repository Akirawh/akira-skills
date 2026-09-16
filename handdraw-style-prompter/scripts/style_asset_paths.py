from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
IMAGES_ROOT = SKILL_ROOT / "images"
INDIVIDUAL_ROOT = IMAGES_ROOT / "individual"


def bucket_name(number: int | str) -> str:
    n = int(number)
    start = ((n - 1) // 200) * 200 + 1
    end = start + 199
    return f"{start:03}-{end:03}"


def bucket_path(number: int | str) -> Path:
    return INDIVIDUAL_ROOT / bucket_name(number)


def single_path(number: int | str) -> Path:
    n = int(number)
    return bucket_path(n) / f"{n:03}.png"


def grid_path(number: int | str) -> Path:
    n = int(number)
    return bucket_path(n) / f"{n:03}_grid.jpg"

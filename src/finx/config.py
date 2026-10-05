import json
from pathlib import Path

SPLIT_FILE = Path(__file__).resolve().parents[2] / "config" / "split.json"


def load_split(path: Path = SPLIT_FILE) -> tuple[Path, dict[str, list[str]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    root = Path(data.pop("root")).expanduser()
    data["test"] = data["test_new_issuer"] + data["test_new_period"]
    return root, data

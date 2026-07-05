from __future__ import annotations

import json
from pathlib import Path


SANDBOX_DIR = Path("/root/.trae-server/ai-agent/sandbox")
PROC_RULE = {"file_inherit_user": "/proc"}


def patch_config(path: Path) -> bool:
    raw = json.loads(path.read_text(encoding="utf-8"))
    permissions = raw.setdefault("permission", [])
    if PROC_RULE in permissions:
        return False
    permissions.append(PROC_RULE)
    path.write_text(json.dumps(raw, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> None:
    patched = []
    for path in sorted(SANDBOX_DIR.glob("*.json")):
        if path.name == "sandbox_impl.json":
            continue
        if patch_config(path):
            patched.append(str(path))
    for item in patched:
        print(f"patched {item}")
    if not patched:
        print("sandbox proc access already present")


if __name__ == "__main__":
    main()

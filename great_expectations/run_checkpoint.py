from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_checkpoint(name: str) -> dict:
    checkpoint_path = Path("great_expectations/checkpoints") / f"{name}.yml"
    return {"name": name, "path": str(checkpoint_path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    args = parser.parse_args()
    print(json.dumps(load_checkpoint(args.checkpoint)))


if __name__ == "__main__":
    main()

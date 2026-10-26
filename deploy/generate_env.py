#!/usr/bin/env python3
"""Create a new production env file without exposing secrets."""

import argparse
import os
import secrets
import tempfile
from pathlib import Path


GENERATED_VALUES = {
    "POSTGRES_PASSWORD": lambda: secrets.token_hex(24),
    "SECRET_KEY": lambda: secrets.token_hex(32),
}

FORCED_VALUES = {
    "APP_ENV": "prod",
    "APP_DEBUG": "false",
    "DOCS_ENABLED": "false",
    "ITC_BASIC_PASSWORD": "",
    "GRAFANA_ADMIN_PASSWORD": "",
}

OBSOLETE_VALUES = {
    "EXPORT_LINK_SECRET",
    "QR_SECRET_KEY",
    "LICENSE_SECRET",
}


def generate_env(template_path: Path, output_path: Path) -> None:
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite existing file: {output_path}")
    if not template_path.is_file():
        raise RuntimeError(f"Template not found: {template_path}")

    values = {
        name: factory() for name, factory in GENERATED_VALUES.items()
    }
    values.update(FORCED_VALUES)
    found = set()
    output_lines = []

    for original in template_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = original.strip()
        if not stripped or stripped.startswith("#") or "=" not in original:
            output_lines.append(original)
            continue

        name = original.split("=", 1)[0].strip()
        if name in OBSOLETE_VALUES:
            continue
        if name in values:
            output_lines.append(f"{name}={values[name]}")
            found.add(name)
        else:
            output_lines.append(original)

    missing = set(GENERATED_VALUES) - found
    if missing:
        raise RuntimeError(
            "Required template variables missing: " + ", ".join(sorted(missing))
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=".env.", dir=output_path.parent, text=True
    )
    temporary_path = Path(temporary_name)
    try:
        os.chmod(temporary_path, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(output_lines) + "\n")
        os.replace(temporary_path, output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate_env(args.template, args.output)
    print("PRODUCTION_ENV_CREATED=1")


if __name__ == "__main__":
    main()

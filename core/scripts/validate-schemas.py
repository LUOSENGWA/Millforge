#!/usr/bin/env python3
"""Schema gate for the Millforge contracts.

The protocol text (``core/protocol/``) and the machine contracts
(``core/schemas/*.json``) describe the same objects: task meta, loop spec,
signal event, decision log, handoff and so on. Until now the schemas had no
consumer at all, so the two could drift silently.

This gate closes that hole. It checks, in order:

1. **Schema integrity** — every ``core/schemas/*.json`` parses, is a valid
   JSON Schema (draft-07), has a unique ``$id``, declares only ``required``
   properties, and every internal ``$ref`` resolves.
2. **Instance conformance** — every instance we ship is validated against
   its schema: the team fixtures (``golden-tests/fixtures/*.json``) against
   ``team.schema.json``, plus any JSON file that names its schema through a
   top-level ``"schema"`` or ``"$schema"`` key holding a Millforge schema id
   (so new instances are covered without editing this script).

Exit code 0 = gate green; 1 = at least one problem (all reported, not just
the first).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "core" / "schemas"
TEAM_FIXTURES = sorted((ROOT / "golden-tests" / "fixtures").glob("*.json"))
INSTANCE_GLOBS = (
    "golden-tests/fixtures/**/*.json",
    "templates/**/*.json",
    "docs/**/*.json",
)

SCHEMA_REF_KEY = "schema"


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _iter_instances() -> list[Path]:
    seen: dict[Path, None] = {}
    for pattern in INSTANCE_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            seen.setdefault(path, None)
    return list(seen)


def _schema_id_of(instance: Any) -> str | None:
    """The Millforge schema id an instance declares for itself, if any."""
    if not isinstance(instance, dict):
        return None
    for key in (SCHEMA_REF_KEY, "$schema"):
        value = instance.get(key)
        if isinstance(value, str) and "millforge/schemas/" in value:
            return value.rsplit("/", 1)[-1]
    return None


def _collect_refs(node: Any, out: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                out.append(value)
            else:
                _collect_refs(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect_refs(item, out)


def _resolve_pointer(document: Any, pointer: str) -> bool:
    """True when ``#/a/b`` resolves inside ``document``."""
    current = document
    for raw in pointer.lstrip("#/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return False
    return True


def check_schemas() -> tuple[dict[str, Any], list[str]]:
    problems: list[str] = []
    schemas: dict[str, Any] = {}
    seen_ids: dict[str, str] = {}

    for path in sorted(SCHEMA_DIR.glob("*.json")):
        rel = path.relative_to(ROOT)
        try:
            document = _load_json(path)
        except json.JSONDecodeError as exc:
            problems.append(f"{rel}: invalid JSON ({exc})")
            continue
        try:
            Draft7Validator.check_schema(document)
        except SchemaError as exc:
            problems.append(f"{rel}: not a valid draft-07 schema ({exc.message})")
            continue

        schema_id = document.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            problems.append(f"{rel}: missing $id")
        elif schema_id in seen_ids:
            problems.append(
                f"{rel}: duplicate $id {schema_id!r} (also in {seen_ids[schema_id]})"
            )
        else:
            seen_ids[schema_id] = str(rel)

        properties = set((document.get("properties") or {}).keys())
        for name in document.get("required") or []:
            if name not in properties:
                problems.append(f"{rel}: required {name!r} is not declared in properties")

        refs: list[str] = []
        _collect_refs(document, refs)
        for ref in refs:
            if not ref.startswith("#"):
                problems.append(f"{rel}: external $ref {ref!r} is not allowed")
                continue
            if not _resolve_pointer(document, ref):
                problems.append(f"{rel}: unresolved $ref {ref!r}")

        schemas[path.name] = document

    return schemas, problems


def check_registry(schemas: dict[str, Any]) -> list[str]:
    """Every schema must be registered in core/schemas/README.md.

    An unregistered schema is an orphan: nobody knows which protocol clause it
    encodes or who is supposed to produce instances of it.
    """
    registry = SCHEMA_DIR / "README.md"
    if not registry.is_file():
        return [f"{registry.relative_to(ROOT)}: missing schema registry"]
    text = registry.read_text(encoding="utf-8")
    missing = [name for name in schemas if name not in text]
    return [
        f"{registry.relative_to(ROOT)}: schema {name} is not registered "
        "(add a row: schema / protocol source / writer-reader / instance)"
        for name in sorted(missing)
    ]


def check_instances(schemas: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    validators: dict[str, Draft7Validator] = {}

    def validator_for(schema_name: str) -> Draft7Validator | None:
        document = schemas.get(schema_name)
        if document is None:
            return None
        if schema_name not in validators:
            validators[schema_name] = Draft7Validator(document)
        return validators[schema_name]

    def validate(path: Path, schema_name: str, instance: Any) -> None:
        validator = validator_for(schema_name)
        if validator is None:
            problems.append(f"{path.relative_to(ROOT)}: unknown schema {schema_name!r}")
            return
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
        for error in errors[:5]:
            where = "/".join(str(part) for part in error.path) or "<root>"
            problems.append(
                f"{path.relative_to(ROOT)} [{schema_name}] at {where}: {error.message}"
            )

    for path in _iter_instances():
        try:
            instance = _load_json(path)
        except json.JSONDecodeError as exc:
            problems.append(f"{path.relative_to(ROOT)}: invalid JSON ({exc})")
            continue
        declared = _schema_id_of(instance)
        if declared:
            validate(path, declared, instance)
            continue
        # Team definitions are the instances that historically lived without
        # a marker: anything shaped like a team document is validated as one.
        if isinstance(instance, dict) and {"name", "roles", "roster"} <= set(instance):
            validate(path, "team.schema.json", instance)

    return problems


def main() -> int:
    schemas, problems = check_schemas()
    problems.extend(check_registry(schemas))
    problems.extend(check_instances(schemas))
    if problems:
        print(json.dumps({"ok": False, "problems": problems}, ensure_ascii=False, indent=1))
        return 1
    print(
        json.dumps(
            {"ok": True, "schemas": len(schemas), "instances": len(_iter_instances())},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

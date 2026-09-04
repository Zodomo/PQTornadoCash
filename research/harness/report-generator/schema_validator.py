"""Focused JSON Schema validator for benchmark-run.schema.json."""

from __future__ import annotations

import datetime as _datetime
import json
import math
import re
from pathlib import Path
from typing import Any


class SchemaLoadError(ValueError):
    """A schema or benchmark JSON document cannot be loaded."""


def load_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-JSON numeric constant {value}")

    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream, parse_constant=reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise SchemaLoadError(f"cannot load JSON {path}: {exc}") from exc


def _resolve_pointer(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise SchemaLoadError(f"only local schema references are supported: {reference}")
    value: Any = root
    for encoded in reference[2:].split("/"):
        key = encoded.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or key not in value:
            raise SchemaLoadError(f"unresolved schema reference: {reference}")
        value = value[key]
    if not isinstance(value, dict):
        raise SchemaLoadError(f"schema reference does not name an object: {reference}")
    return value


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    raise SchemaLoadError(f"unsupported schema type: {expected}")


def _date_time_valid(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T.+(?:Z|[+-]\d{2}:\d{2})", value):
        return False
    try:
        parsed = _datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def validate_document(document: Any, schema: dict[str, Any]) -> list[dict[str, str]]:
    """Return deterministic path-keyword-message errors for the schema subset used by the root run schema."""
    errors: list[dict[str, str]] = []

    def error(path: str, keyword: str, message: str) -> None:
        errors.append({"path": path, "keyword": keyword, "message": message})

    def visit(value: Any, current: dict[str, Any], path: str) -> None:
        if "$ref" in current:
            visit(value, _resolve_pointer(schema, current["$ref"]), path)
            return
        if "const" in current and value != current["const"]:
            error(path, "const", f"must equal {current['const']!r}")
        if "enum" in current and value not in current["enum"]:
            error(path, "enum", f"must be one of {current['enum']!r}")

        expected = current.get("type")
        if expected is not None:
            types = [expected] if isinstance(expected, str) else expected
            if not isinstance(types, list) or not all(isinstance(item, str) for item in types):
                raise SchemaLoadError(f"invalid type declaration at {path}")
            if not any(_matches_type(value, item) for item in types):
                error(path, "type", f"must have type {' or '.join(types)}")
                return

        if isinstance(value, dict):
            required = current.get("required", [])
            for name in required:
                if name not in value:
                    error(path, "required", f"missing required property {name!r}")
            properties = current.get("properties", {})
            for name in sorted(value):
                child_path = f"{path}.{name}"
                if name in properties:
                    visit(value[name], properties[name], child_path)
                else:
                    additional = current.get("additionalProperties", True)
                    if additional is False:
                        error(child_path, "additionalProperties", "property is not allowed")
                    elif isinstance(additional, dict):
                        visit(value[name], additional, child_path)

        if isinstance(value, list):
            if "minItems" in current and len(value) < current["minItems"]:
                error(path, "minItems", f"must contain at least {current['minItems']} items")
            items = current.get("items")
            if isinstance(items, dict):
                for index, item in enumerate(value):
                    visit(item, items, f"{path}[{index}]")

        if isinstance(value, str):
            if "minLength" in current and len(value) < current["minLength"]:
                error(path, "minLength", f"must contain at least {current['minLength']} characters")
            pattern = current.get("pattern")
            if pattern is not None and re.search(pattern, value) is None:
                error(path, "pattern", f"must match {pattern!r}")
            if current.get("format") == "date-time" and not _date_time_valid(value):
                error(path, "format", "must be an RFC 3339 date-time with timezone")

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in current and value < current["minimum"]:
                error(path, "minimum", f"must be at least {current['minimum']}")

    visit(document, schema, "$")
    errors.sort(key=lambda item: (item["path"], item["keyword"], item["message"]))
    return errors

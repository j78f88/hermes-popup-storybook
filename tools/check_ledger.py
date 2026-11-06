#!/usr/bin/env python3
"""Validate fact ledgers with the kit's JSON schema."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "templates" / "fact-ledger.schema.json"
CLAIM_TOKEN = re.compile(r"(?<![A-Za-z0-9])\d+(?:,\d{3})*(?:\.\d+)?(?![A-Za-z0-9])")
TYPE_NAMES = {
    "array": list,
    "boolean": bool,
    "null": type(None),
    "number": (int, float),
    "object": dict,
    "string": str,
}


def value_matches(value, type_name):
    """Return whether a JSON value matches one declared JSON Schema type."""
    if type_name == "number" and isinstance(value, bool):
        return False
    return isinstance(value, TYPE_NAMES[type_name])


def validate_value(value, schema, where="$"):
    """Validate the JSON Schema subset used by the fact ledger."""
    errors = []
    declared = schema.get("type")
    allowed = declared if isinstance(declared, list) else [declared] if declared else []
    if allowed and not any(value_matches(value, name) for name in allowed):
        expected = " or ".join(allowed)
        return [f"{where}: expected {expected}"]

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{where}: missing required field '{name}'")
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in properties:
                    errors.append(f"{where}: unexpected field '{name}'")
        for name, child in value.items():
            if name in properties:
                errors.extend(validate_value(child, properties[name], f"{where}.{name}"))

    if isinstance(value, list) and "items" in schema:
        for index, child in enumerate(value):
            errors.extend(validate_value(child, schema["items"], f"{where}[{index}]"))

    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        errors.append(f"{where}: must not be empty")
    return errors


def ledger_paths(values):
    """Drop copied schema files from a shell-expanded research glob."""
    return [Path(value) for value in values if not value.endswith(".schema.json")]


def claim_tokens(text):
    """Extract normalized numeric and date-like tokens from prose."""
    return {match.group(0).replace(",", "") for match in CLAIM_TOKEN.finditer(str(text or ""))}


def story_fields(chapter, prefix):
    """Return (field_path, text) pairs for one chapter or finale entry."""
    if not isinstance(chapter, dict):
        return []
    if isinstance(prefix, int):
        prefix = f"chapters[{prefix}]"
    fields = []
    text_list = chapter.get("text", [])
    if isinstance(text_list, list):
        for paragraph_index, paragraph in enumerate(text_list):
            fields.append((f"{prefix}.text[{paragraph_index}]", paragraph))
    for gadget in ("tab", "flap"):
        gadget_obj = chapter.get(gadget)
        text = gadget_obj.get("text") if isinstance(gadget_obj, dict) else None
        if text:
            fields.append((f"{prefix}.{gadget}.text", text))
    return fields


def matching_evidence(story, chapter, ledgers):
    """Collect normalized claim tokens backed by chapter facts, sources, or ledgers."""
    if not isinstance(chapter, dict):
        return set()
    facts_list = [fact for fact in (chapter.get("facts") or []) if isinstance(fact, dict)]
    source_ids = {
        fact.get("source")
        for fact in facts_list
        if isinstance(fact.get("source"), str) and fact.get("source")
    }
    chapter_number = chapter.get("number")
    values = [chapter.get("when", "")]
    for fact in facts_list:
        values.extend((fact.get("label", ""), fact.get("value", "")))
    sources_map = story.get("sources") if isinstance(story, dict) and isinstance(story.get("sources"), dict) else {}
    for source_id in source_ids:
        source = sources_map.get(source_id, {})
        if isinstance(source, dict):
            values.extend((source.get("ref", ""), source.get("excerpt", "")))
    for ledger in ledgers:
        if not isinstance(ledger, dict):
            continue
        ledger_facts = ledger.get("facts", [])
        if not isinstance(ledger_facts, list):
            continue
        for fact in ledger_facts:
            if not isinstance(fact, dict):
                continue
            fact_source = fact.get("source")
            matches_source = isinstance(fact_source, str) and fact_source in source_ids
            matches_chapter = chapter_number is not None and fact.get("chapter") == chapter_number
            if matches_source or matches_chapter:
                values.extend(
                    fact.get(key, "")
                    for key in ("claim", "value", "ref", "excerpt", "date")
                )
                if isinstance(fact_source, dict):
                    values.extend(
                        fact_source.get(key, "")
                        for key in ("ref", "excerpt")
                    )
    return claim_tokens(" ".join(str(value) for value in values))


def claim_findings(story, ledgers):
    """Return unbacked numeric or date-like tokens across written chapters and finale."""
    if not isinstance(story, dict):
        return []
    findings = []
    chapters = story.get("chapters", [])
    if isinstance(chapters, list):
        for index, chapter in enumerate(chapters):
            if not isinstance(chapter, dict) or chapter.get("status", "written") != "written":
                continue
            allowed = matching_evidence(story, chapter, ledgers)
            for field, text in story_fields(chapter, f"chapters[{index}]"):
                for token in sorted(claim_tokens(text) - allowed):
                    findings.append({"chapter": chapter.get("number", index + 1), "field": field, "token": token})
    finale = story.get("finale")
    if isinstance(finale, dict) and finale.get("status", "written") == "written":
        allowed = matching_evidence(story, finale, ledgers)
        for field, text in story_fields(finale, "finale"):
            for token in sorted(claim_tokens(text) - allowed):
                findings.append({"chapter": "finale", "field": field, "token": token})
    return findings


LEGACY_LANE_KEYS = {"lane", "facts", "moments", "gaps", "chapter_notes", "stats", "models"}


def validate_legacy_lane_ledger(ledger):
    """Validate pre-template lane ledgers that carry a top-level 'lane' key."""
    errors = []
    extra = sorted(set(ledger) - LEGACY_LANE_KEYS)
    if extra:
        errors.append(f"$: unexpected field '{extra[0]}'")
    if not isinstance(ledger.get("lane"), str) or not ledger["lane"]:
        errors.append("$: 'lane' must be a non-empty string")
    facts = ledger.get("facts", [])
    if not isinstance(facts, list):
        return errors + ["$.facts: expected array"]
    for index, fact in enumerate(facts):
        where = f"$.facts[{index}]"
        if not isinstance(fact, dict):
            errors.append(f"{where}: expected object")
            continue
        for key in ("id", "claim", "value", "source"):
            if key not in fact:
                errors.append(f"{where}: missing required field '{key}'")
        source = fact.get("source")
        if isinstance(source, dict):
            for key in ("kind", "ref"):
                if not isinstance(source.get(key), str) or not source.get(key):
                    errors.append(f"{where}.source: missing required field '{key}'")
        elif source is not None and not isinstance(source, str):
            errors.append(f"{where}.source: expected string or object")
    return errors


def check_files(paths, schema_path=DEFAULT_SCHEMA, story_path=None, allow_legacy=True):
    """Return validation errors, the total fact count, and claim findings."""
    errors = []
    facts = 0
    claims = []
    try:
        schema = json.loads(Path(schema_path).read_text())
    except (OSError, json.JSONDecodeError) as error:
        return [f"{schema_path}: cannot read schema: {error}"], facts, claims

    story = None
    source_ids = None
    if story_path:
        try:
            story = json.loads(Path(story_path).read_text())
            sources_obj = story.get("sources", {}) if isinstance(story, dict) else {}
            source_ids = set(sources_obj) if isinstance(sources_obj, dict) else set()
        except (OSError, json.JSONDecodeError) as error:
            return [f"{story_path}: cannot read story: {error}"], facts, claims

    loaded_ledgers = []
    default_schema_resolved = Path(schema_path).resolve() == DEFAULT_SCHEMA.resolve()
    for path in paths:
        try:
            ledger = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{path}: cannot read ledger: {error}")
            continue
        loaded_ledgers.append(ledger)
        if allow_legacy and default_schema_resolved and isinstance(ledger, dict) and "lane" in ledger and "meta" not in ledger:
            file_errors = validate_legacy_lane_ledger(ledger)
        else:
            file_errors = validate_value(ledger, schema)
        errors.extend(f"{path}: {error}" for error in file_errors)
        entries = ledger.get("facts", []) if isinstance(ledger, dict) else []
        facts += len(entries) if isinstance(entries, list) else 0
        if source_ids is not None and isinstance(entries, list):
            for index, fact in enumerate(entries):
                if (
                    isinstance(fact, dict)
                    and isinstance(fact.get("source"), str)
                    and fact["source"] not in source_ids
                ):
                    errors.append(
                        f"{path}: $.facts[{index}].source: "
                        f"'{fact['source']}' is not in {story_path} sources"
                    )
    if story is not None:
        claims = claim_findings(story, loaded_ledgers)
    return errors, facts, claims


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledgers", nargs="+", help="ledger JSON files; copied schema files are ignored")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help="fact ledger JSON schema")
    parser.add_argument("--story", help="story JSON used to check source IDs")
    parser.add_argument(
        "--claims",
        choices=("off", "report", "strict"),
        default="report",
        help="check numeric and date-like prose claims against page evidence",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    paths = ledger_paths(args.ledgers)
    if not paths:
        print("FAIL: no ledger JSON files found", file=sys.stderr)
        return 1
    errors, facts, claims = check_files(
        paths,
        args.schema,
        args.story,
        allow_legacy=(args.claims != "strict"),
    )
    for error in errors:
        print(f"ERROR {error}")
    claim_suffix = ""
    if args.claims == "report":
        for item in claims:
            print(f"WARN claim chapter {item['chapter']} {item['field']}: unsupported token {item['token']}")
        if args.story:
            claim_suffix = f", {len(claims)} claim warnings"
    elif args.claims == "strict":
        for item in claims:
            print(f"ERROR claim chapter {item['chapter']} {item['field']}: unsupported token {item['token']}")
        if args.story:
            claim_suffix = f", {len(claims)} claim errors"
    total_errors = len(errors) + (len(claims) if args.claims == "strict" else 0)
    if total_errors:
        print(f"FAIL: {len(paths)} ledger files, {facts} facts, {total_errors} errors{claim_suffix}")
        return 1
    print(f"PASS: {len(paths)} ledger files, {facts} facts, 0 errors{claim_suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

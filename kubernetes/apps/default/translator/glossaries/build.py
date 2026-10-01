"""Build public terminology payloads without reading runtime configuration."""

import argparse
import csv
import json
import logging
import string
from pathlib import Path
from typing import TypedDict

LOGGER = logging.getLogger(__name__)
DIRECTORY = Path(__file__).resolve().parent
TOPICS = {
    "family-law": "UK–France | Family law",
    "personal-tax": "UK–France | Personal taxes",
    "household": "UK–France | Household invoices, payslips & utilities",
}


class Payload(TypedDict):
    name: str
    source_language: str
    target_language: str
    shared: bool
    entries: list[dict[str, str]]


def variants(source: str, language: str) -> list[str]:
    spellings = {source, source[:1].upper() + source[1:], source.upper()}
    if language == "en":
        spellings.add(string.capwords(source))
    return sorted(spellings | {term.replace("'", "’") for term in spellings})


def replacement(source: str, target: str) -> str:
    if source.isupper():
        return target.upper()
    if source[:1].isupper():
        return target[:1].upper() + target[1:]
    return target


def build_payload(topic: str, source_language: str) -> Payload:
    target_language = "fr" if source_language == "en" else "en"
    stem = f"{topic}-{source_language}-{target_language}"
    references = json.loads((DIRECTORY / "sources.json").read_text())[
        "references"
    ]
    entries: dict[str, dict[str, str]] = {}
    with (DIRECTORY / f"{stem}.tsv").open(
        newline="", encoding="utf-8"
    ) as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    for row in rows:
        if not row["scope_note"] or any(
            reference not in references
            for reference in row["references"].split(",")
        ):
            raise ValueError(f"Missing provenance: {stem}")
        preserve = row["source"] == row["target"]
        for source in variants(row["source"], source_language):
            target = source if preserve else replacement(source, row["target"])
            keep = source == target
            entry = {
                "source": source,
                "target": "" if keep else target,
                "mode": "preserve" if keep else "translate",
            }
            if source in entries and entries[source] != entry:
                raise ValueError(f"Conflicting variant: {stem}: {source}")
            entries[source] = entry
    return {
        "name": (
            f"{TOPICS[topic]} | "
            f"{source_language.upper()} → {target_language.upper()}"
        ),
        "source_language": source_language,
        "target_language": target_language,
        "shared": True,
        "entries": [entries[source] for source in sorted(entries)],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    for topic in TOPICS:
        for language in ("en", "fr"):
            payload = build_payload(topic, language)
            target = payload["target_language"]
            path = DIRECTORY / f"{topic}-{language}-{target}.json"
            rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            if arguments.check:
                if path.read_text(encoding="utf-8") != rendered:
                    raise ValueError(f"Stale generated payload: {path.name}")
            else:
                path.write_text(rendered, encoding="utf-8")
            LOGGER.info("%s: %s entries", path.name, len(payload["entries"]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()

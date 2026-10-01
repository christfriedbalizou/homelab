"""Validate public content against Translator's real domain and matcher."""

import json
import logging
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from translator.domain.glossaries import (
    GlossaryContent,
    GlossaryLimits,
    GlossarySnapshot,
    GlossaryWrite,
    TermRule,
)
from translator.domain.ingestion import Language
from translator.translation.quality import PreparedTranslation
from translator.translation.terminology import TerminologyMatcher

DIRECTORY = Path(__file__).resolve().parent
LOGGER = logging.getLogger(__name__)


def main() -> None:
    limits = GlossaryLimits()
    combined: dict[str, dict[str, TermRule]] = {"en": {}, "fr": {}}
    glossaries = [
        GlossaryWrite.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(DIRECTORY.glob("*-??-??.json"))
    ]
    assert len(glossaries) == 6
    rules_checked = 0
    for glossary in glossaries:
        content = GlossaryContent(name=glossary.name, entries=glossary.entries)
        assert glossary.shared
        assert len(content.entries) <= limits.max_entries
        assert (
            len(content.model_dump_json().encode()) <= limits.max_content_bytes
        )
        rules = tuple(glossary.entries)
        matcher = TerminologyMatcher(rules)
        for rule in rules:
            group = combined[glossary.source_language.value]
            assert rule.source not in group or group[rule.source] == rule
            group[rule.source] = rule
            prepared = PreparedTranslation.prepare(
                rule.source, terminology=matcher
            )
            assert "".join(prepared.parts) == rule.replacement
            rules_checked += 1
    for source, entries in combined.items():
        snapshot = GlossarySnapshot(
            source_language=Language(source),
            target_language=Language.FR if source == "en" else Language.EN,
            entries=list(entries.values()),
            revisions={
                uuid5(NAMESPACE_URL, glossary.name): 1
                for glossary in glossaries
                if glossary.source_language.value == source
            },
        )
        size = len(snapshot.model_dump_json().encode())
        assert size <= 1048576
        LOGGER.info(
            "%s: %s unique rules, %s snapshot bytes",
            source,
            len(entries),
            size,
        )
    checks = json.loads(
        (DIRECTORY / "checks.json").read_text(encoding="utf-8")
    )
    for index, case in enumerate(checks):
        prepared = PreparedTranslation.prepare(
            case["source"],
            terminology=tuple(combined[case["direction"]].values()),
        )
        assert "".join(prepared.parts) == case["expected"], f"Case {index + 1}"
    LOGGER.info(
        "%s rules and %s representative cases passed",
        rules_checked,
        len(checks),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()

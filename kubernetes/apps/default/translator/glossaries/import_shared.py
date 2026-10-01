"""Operator-only import using the deployed app's permission/encryption services.

Read six public GlossaryWrite payloads as a JSON list on stdin. Default mode
checks without writes. Run only in the matching Translator runtime; never
copy production settings, identities or keys into this content directory.
"""

import argparse
import asyncio
import json
import logging
import sys
from collections import Counter
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from translator.config.settings import Settings
from translator.db.engine import create_database_engine, create_session_factory
from translator.db.models import UserModel
from translator.domain.glossaries import (
    GlossaryContent,
    GlossaryLimits,
    GlossaryResponse,
    GlossaryWrite,
)
from translator.domain.users import UserRole
from translator.services.glossaries import (
    glossary_permissions,
    list_glossaries,
    save_glossary,
    select_glossaries,
)
from translator.storage.crypto import load_master_key


async def existing_glossaries(
    session: AsyncSession, owner: UUID, key: bytes, limits: GlossaryLimits
) -> list[GlossaryResponse]:
    records: list[GlossaryResponse] = []
    offset: int | None = 0
    while offset is not None:
        page = await list_glossaries(session, owner, key, offset, limits)
        records.extend(page.glossaries)
        offset = page.next_offset
    return records


def same_content(record: GlossaryResponse, payload: GlossaryWrite) -> bool:
    return all(
        getattr(record, field) == getattr(payload, field)
        for field in GlossaryWrite.model_fields
    )


async def import_payloads(
    payloads: list[GlossaryWrite], apply: bool
) -> dict[str, object]:
    settings = Settings.model_validate({})
    if settings.ingestion is None:
        raise ValueError("Ingestion configuration required")
    if len(payloads) != 6 or len({item.name for item in payloads}) != 6:
        raise ValueError("Six distinct glossaries required")
    pairs = Counter(
        (item.source_language.value, item.target_language.value)
        for item in payloads
    )
    if pairs != {("en", "fr"): 3, ("fr", "en"): 3}:
        raise ValueError("Three glossaries per direction required")
    for payload in payloads:
        content = GlossaryContent(name=payload.name, entries=payload.entries)
        if (
            not payload.shared
            or not payload.name.startswith("UK–France | ")
            or len(payload.entries) > settings.glossary.max_entries
            or len(content.model_dump_json().encode())
            > settings.glossary.max_content_bytes
        ):
            raise ValueError("Invalid public content or capacity exceeded")
    key = load_master_key(settings.ingestion.master_key_file)
    engine = create_database_engine(
        settings.database_url, operation_timeout_seconds=15
    )
    created = 0
    matched = 0
    identifiers: dict[str, list[UUID]] = {"en": [], "fr": []}
    snapshots: dict[str, dict[str, int]] = {}
    try:
        async with (
            create_session_factory(engine)() as session,
            session.begin(),
        ):
            administrators = list(
                await session.scalars(
                    select(UserModel.id).where(
                        UserModel.role == UserRole.ADMINISTRATOR,
                        UserModel.active.is_(True),
                        UserModel.deletion_requested.is_(False),
                    )
                )
            )
            if len(administrators) != 1:
                raise ValueError("A unique active administrator is required")
            owner = administrators[0]
            await glossary_permissions(session, owner, lock=apply)
            existing = await existing_glossaries(
                session, owner, key, settings.glossary
            )
            for payload in payloads:
                matches = [row for row in existing if row.name == payload.name]
                if matches:
                    if len(matches) != 1 or not same_content(
                        matches[0], payload
                    ):
                        raise ValueError(
                            "Existing glossary differs; no overwrite"
                        )
                    record = matches[0]
                    matched += 1
                elif apply:
                    record = await save_glossary(
                        session, owner, key, payload, limits=settings.glossary
                    )
                    if not same_content(record, payload):
                        raise ValueError("Encrypted round-trip mismatch")
                    created += 1
                else:
                    continue
                identifiers[payload.source_language.value].append(record.id)
            for source, selected in identifiers.items():
                if len(selected) == 3:
                    snapshot = await select_glossaries(
                        session,
                        owner,
                        selected,
                        key,
                        max_snapshot_bytes=(
                            settings.ingestion.max_glossary_snapshot_bytes
                        ),
                    )
                    if snapshot is None:
                        raise ValueError("Snapshot missing")
                    snapshots[source] = {
                        "entries": len(snapshot.entries),
                        "bytes": len(snapshot.model_dump_json().encode()),
                    }
    finally:
        await engine.dispose()
    return {
        "mode": "apply" if apply else "check",
        "created": created,
        "identical_existing": matched,
        "missing": 6 - created - matched,
        "snapshots": snapshots,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    logging.disable(logging.CRITICAL)
    try:
        encoded = sys.stdin.buffer.read(1048577)
        if len(encoded) > 1048576:
            raise ValueError("Input too large")
        payloads = TypeAdapter(list[GlossaryWrite]).validate_json(encoded)
        result = asyncio.run(import_payloads(payloads, arguments.apply))
        sys.stdout.write(json.dumps(result) + "\n")
        return 0
    except Exception:
        sys.stderr.write("Glossary operation failed; details suppressed.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

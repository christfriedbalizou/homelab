"""Verify a matched release and reserve the operator identity before serving."""

import argparse
import asyncio
import hashlib
import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select, text
from translator.config.settings import Settings
from translator.db.engine import create_database_engine, create_session_factory
from translator.db.models import (
    ApplicationStateModel,
    AuditEventModel,
    TranslationProviderModel,
    UserIdentityModel,
    UserModel,
)
from translator.domain.users import UserRole
from translator.services.users import BOOTSTRAP_ADMINISTRATOR_STATE_KEY
from translator.storage.crypto import encrypt_blob
from translator.translation.policy import (
    ProviderConfiguration,
    ProviderDestinationPolicy,
)

LOGGER = logging.getLogger(__name__)


def verify_release(settings: Settings) -> None:
    source = settings.source_distribution
    if (
        source is None
        or settings.translation is None
        or settings.ingestion is None
    ):
        raise RuntimeError("release_configuration_missing")
    revision = (
        Path("/usr/share/translator/source-revision").read_text().strip()
    )
    if revision != source.revision:
        raise RuntimeError("release_source_revision_mismatch")
    with source.archive.open("rb") as archive:
        digest = hashlib.file_digest(archive, "sha256").hexdigest()
    if digest != source.sha256:
        raise RuntimeError("release_source_checksum_mismatch")
    for path in (
        settings.ingestion.master_key_file,
        settings.translation.master_key_file,
    ):
        if len(path.read_bytes()) != 32:
            raise RuntimeError("invalid_deployment_key")
    if settings.ingestion.storage_backend == "s3":
        # The initial cutover has no documents. Fail closed if a local writer
        # creates one before the Recreate rollout stops the old deployment.
        if any(settings.ingestion.local_storage_path.iterdir()):
            raise RuntimeError("local_documents_require_s3_migration")


async def bootstrap(settings: Settings) -> None:
    subject = Path("/run/secrets/bootstrap-admin-subject").read_text().strip()
    UUID(subject)
    issuer = str(settings.oidc_issuer).rstrip("/")
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(70423918)")
            )
            identity = await session.scalar(
                select(UserIdentityModel).where(
                    UserIdentityModel.issuer == issuer,
                    UserIdentityModel.subject == subject,
                )
            )
            if identity is None:
                count = await session.scalar(select(func.count(UserModel.id)))
                if count:
                    raise RuntimeError("existing_database_requires_review")
                user = UserModel(role=UserRole.ADMINISTRATOR.value)
                session.add(user)
                await session.flush()
                identity = UserIdentityModel(
                    user_id=user.id, issuer=issuer, subject=subject
                )
                session.add(identity)
                session.add(
                    ApplicationStateModel(
                        key=BOOTSTRAP_ADMINISTRATOR_STATE_KEY, value="claimed"
                    )
                )
                session.add(
                    AuditEventModel(
                        actor_user_id=user.id,
                        target_user_id=user.id,
                        event_type="deployment_administrator_reserved",
                    )
                )
                await session.flush()
            provider_id = settings.translation_provider_id
            if provider_id is None or settings.translation is None:
                raise RuntimeError("deployment_provider_missing")
            destinations = settings.translation.allowed_provider_base_urls
            if len(destinations) != 2:
                raise RuntimeError("deployment_requires_two_provider_urls")
            providers = (
                (
                    provider_id,
                    ProviderConfiguration(
                        kind="local",
                        user_selectable=True,
                        base_url=destinations[0],
                        model="qwen3-local",
                        concurrency=1,
                        read_timeout_seconds=180,
                        overall_timeout_seconds=300,
                    ),
                    "litellm-api-key",
                ),
                (
                    UUID(
                        Path("/run/secrets/public-provider-id")
                        .read_text()
                        .strip()
                    ),
                    ProviderConfiguration(
                        kind="remote",
                        user_selectable=True,
                        base_url=destinations[1],
                        model="openai-gpt-6-luna-cloud",
                        concurrency=1,
                        read_timeout_seconds=180,
                        overall_timeout_seconds=300,
                    ),
                    "public-litellm-api-key",
                ),
            )
            for selected_id, configuration, key_name in providers:
                ProviderDestinationPolicy(
                    settings.translation.allowed_provider_base_urls
                ).validate(configuration)
                existing = await session.get(
                    TranslationProviderModel, selected_id
                )
                if existing is not None:
                    continue
                credential = (
                    (Path("/run/secrets") / key_name).read_bytes().strip()
                )
                encrypted = encrypt_blob(
                    credential,
                    settings.translation.master_key_file.read_bytes(),
                    owner_id="application",
                    blob_id=str(selected_id),
                    content_role="provider-secret",
                ).decode("ascii")
                session.add(
                    TranslationProviderModel(
                        id=selected_id,
                        configuration=configuration.model_dump_json(),
                        encrypted_secret=encrypted,
                        revision=1,
                    )
                )
                session.add(
                    AuditEventModel(
                        actor_user_id=identity.user_id,
                        event_type="deployment_provider_created",
                    )
                )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    arguments = parser.parse_args()
    configured = Settings()
    verify_release(configured)
    if not arguments.verify_only:
        asyncio.run(bootstrap(configured))
    LOGGER.info("Deployment identity and provider verified")

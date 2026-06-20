#!/usr/bin/env python3

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

import yaml

SOPS_SUFFIXES = (".sops.yaml", ".sops.yml")
DEFAULT_ALLOWED_EMPTY_KEYS = {
    "stringData.FORGEJO__STORAGE__MINIO_LOCATION",
    "stringData.smtp-password",
    "stringData.smtp-username",
}


@dataclass(frozen=True)
class EmptySecretValue:
    file: Path
    document: int
    secret: str
    field: str
    key: str

    def format(self) -> str:
        doc = f" document {self.document}" if self.document > 1 else ""
        return (
            f"{self.file}:{doc} {self.secret}: "
            f"{self.field}.{self.key} is empty"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate rendered SOPS Secret manifests before encryption."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Rendered files or directories to scan.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        type=Path,
        help="File or directory to skip. Can be passed more than once.",
    )
    parser.add_argument(
        "--allow-empty-key",
        action="append",
        default=[],
        help=(
            "Secret key allowed to render empty. Use KEY or field.KEY, "
            "for example smtp-username or stringData.smtp-username. "
            "Can be passed more than once."
        ),
    )
    return parser.parse_args()


def resolve_paths(paths: Iterable[Path]) -> set[Path]:
    return {path.resolve() for path in paths}


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def is_excluded(path: Path, excluded: set[Path]) -> bool:
    resolved = path.resolve()
    return any(
        resolved == item or is_relative_to(resolved, item)
        for item in excluded
    )


def iter_sops_files(
    paths: Iterable[Path],
    excluded: set[Path],
) -> Iterator[Path]:
    for path in paths:
        if not path.exists() or is_excluded(path, excluded):
            continue
        if path.is_file():
            if path.name.endswith(SOPS_SUFFIXES) and not path.name.endswith(
                ".j2"
            ):
                yield path
            continue
        for file in sorted(path.rglob("*.sops.y*ml")):
            if (
                file.is_file()
                and not file.name.endswith(".j2")
                and not is_excluded(file, excluded)
            ):
                yield file


def secret_name(document: dict[str, Any]) -> str:
    metadata = document.get("metadata") or {}
    namespace = metadata.get("namespace") or "default"
    name = metadata.get("name") or "<unnamed>"
    return f"{namespace}/{name}"


def empty_keys(value: Any) -> Iterator[tuple[str, Any]]:
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        if item is None or item == "":
            yield str(key), item


def is_allowed_empty(
    field: str,
    key: str,
    allowed_empty_keys: set[str],
) -> bool:
    return key in allowed_empty_keys or f"{field}.{key}" in allowed_empty_keys


def validate_file(
    path: Path,
    allowed_empty_keys: set[str],
) -> tuple[list[EmptySecretValue], str | None]:
    findings: list[EmptySecretValue] = []
    try:
        with path.open("r", encoding="utf-8") as file:
            documents = list(yaml.safe_load_all(file))
    except yaml.YAMLError as error:
        return findings, f"{path}: failed to parse YAML: {error}"

    for index, document in enumerate(documents, start=1):
        if not isinstance(document, dict) or document.get("kind") != "Secret":
            continue

        name = secret_name(document)
        for field in ("stringData", "data"):
            for key, _ in empty_keys(document.get(field)):
                if is_allowed_empty(field, key, allowed_empty_keys):
                    continue
                findings.append(
                    EmptySecretValue(
                        file=path,
                        document=index,
                        secret=name,
                        field=field,
                        key=key,
                    )
                )

    return findings, None


def main() -> int:
    args = parse_args()
    excluded = resolve_paths(args.exclude)
    allowed_empty_keys = DEFAULT_ALLOWED_EMPTY_KEYS | set(args.allow_empty_key)

    print("=== Validating rendered SOPS secrets ===")

    findings: list[EmptySecretValue] = []
    parse_errors: list[str] = []

    for file in iter_sops_files(args.paths, excluded):
        file_findings, parse_error = validate_file(file, allowed_empty_keys)
        findings.extend(file_findings)
        if parse_error:
            parse_errors.append(parse_error)

    for parse_error in parse_errors:
        print(parse_error, file=sys.stderr)

    for finding in findings:
        print(finding.format(), file=sys.stderr)

    if parse_errors or findings:
        print(
            "Rendered SOPS secrets contain empty values; update "
            "bootstrap/vars/config.yaml "
            "or the relevant template before encrypting.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run locally with: uv run --with pyyaml --with jinja2 python check.py."""

from pathlib import Path
import tempfile

import jinja2
import yaml

from bootstrap import configure, INCLUDE, KEY


def main():
    source = Path(__file__).parent
    automation = yaml.safe_load((source / "automations.yaml").read_text())[0]
    template = jinja2.Environment(undefined=jinja2.StrictUndefined).from_string(
        automation["conditions"][0]["value_template"]
    )
    person = {
        "id": "test-person",
        "camera": "entrance",
        "label": "person",
        "false_positive": False,
        "entered_zones": ["front_door_private_area"],
        "has_snapshot": True,
    }

    def check(before, after, expected, kind="update"):
        actual = template.render(trigger={"payload_json": {
            "type": kind, "before": before, "after": after,
        }}).strip() == "True"
        assert actual == expected, (before, after)

    outside = {**person, "entered_zones": []}
    check(outside, person, True)
    check(person, person, False)  # No repeat for subsequent snapshots/updates.
    check(person, person, True, "new")
    check(outside, outside, False)
    check({}, {**person, "label": "umbrella"}, False)
    check({}, {**person, "camera": "other"}, False)
    check({}, {**person, "false_positive": True}, False)
    no_snapshot = {**person, "has_snapshot": False}
    check(outside, no_snapshot, False)
    check(no_snapshot, person, True)  # Snapshot may arrive after zone entry.
    check(person, person, False, "end")
    check({}, {}, False)

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        config = root / "configuration.yaml"
        original = "automation: !include automations.yaml\nhttp:\n  password: !secret password\n"
        config.write_text(original)
        configure(root)
        updated = config.read_text()
        assert updated.startswith(original)
        assert f"{KEY}: !include {INCLUDE}" in updated
        configure(root)
        assert config.read_text() == updated  # Idempotent across pod restarts.
        assert (root / ".configuration-backups/before-gate-notifications.yaml").read_text() == original
        config.write_text(f"{KEY}: !include different.yaml\n")
        try:
            configure(root)
        except ValueError:
            pass
        else:
            raise AssertionError("Conflicting include must not be overwritten")
    print("Notification filtering, delayed snapshots, deduplication and safe bootstrap checks passed.")


if __name__ == "__main__":
    main()

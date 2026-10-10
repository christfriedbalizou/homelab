"""Add the GitOps automation include once, preserving the user's HA configuration."""

from pathlib import Path
import shutil
import yaml


KEY = "automation gate_notifications"
INCLUDE = "/gitops-gate-notifications/automations.yaml"


def configure(config_dir=Path("/config")):
    config = config_dir / "configuration.yaml"
    original = config.read_text()
    document = yaml.compose(original)
    if not isinstance(document, yaml.MappingNode):
        raise ValueError("Home Assistant configuration must be a mapping")
    matches = [value for key, value in document.value if key.value == KEY]
    if matches:
        if len(matches) != 1 or matches[0].tag != "!include" or matches[0].value != INCLUDE:
            raise ValueError("Conflicting gate notification include; manual review required")
        return
    backup = config_dir / ".configuration-backups" / "before-gate-notifications.yaml"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        raise ValueError("Previous gate notification backup exists; manual review required")
    shutil.copy2(config, backup)
    backup.chmod(0o600)
    # Keep permissions/ownership and every existing setting intact.
    with config.open("a") as target:
        target.write(f"\n# Repository-managed Frigate notification.\n{KEY}: !include {INCLUDE}\n")


if __name__ == "__main__":
    configure()

"""Set bounded-transcode options without replacing unrelated Jellyfin settings."""
import os
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET


def configure(path):
    path = Path(path)
    if path.exists():
        tree = ET.parse(path)  # Invalid XML fails before touching the original.
        backup = path.with_name(path.name + ".before-transcode-hardening")
        if not backup.exists():
            shutil.copy2(path, backup)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        tree = ET.ElementTree(ET.Element("EncodingOptions"))
    root = tree.getroot()
    for name, value in {
        "TranscodingTempPath": "/transcode",
        "EnableThrottling": "true",
        "ThrottleDelaySeconds": "60",
        "EnableSegmentDeletion": "true",
        "SegmentKeepSeconds": "60",
    }.items():
        element = root.find(name)
        if element is None:
            element = ET.SubElement(root, name)
        element.text = value
    temporary = path.with_name(path.name + ".tmp")
    tree.write(temporary, encoding="utf-8", xml_declaration=True)
    os.chmod(temporary, 0o600)
    temporary.replace(path)


if __name__ == "__main__":
    configure("/config/config/encoding.xml")

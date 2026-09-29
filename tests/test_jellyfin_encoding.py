import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

SOURCE = Path(__file__).resolve().parents[1] / 'kubernetes/apps/media/jellyfin/app/configure-encoding.py'
spec = importlib.util.spec_from_file_location('encoding_config', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EncodingMigrationTests(unittest.TestCase):
    def test_preserves_hardware_settings_and_original_backup_on_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'encoding.xml'
            original = '<EncodingOptions><HardwareAccelerationType>nvenc</HardwareAccelerationType><EnableThrottling>false</EnableThrottling></EncodingOptions>'
            path.write_text(original)
            module.configure(path)
            module.configure(path)
            root = ET.parse(path).getroot()
            self.assertEqual(root.findtext('HardwareAccelerationType'), 'nvenc')
            self.assertEqual(root.findtext('EnableThrottling'), 'true')
            self.assertEqual(len(root.findall('EnableThrottling')), 1)
            self.assertEqual(path.with_name(path.name + '.before-transcode-hardening').read_text(), original)

    def test_invalid_existing_configuration_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'encoding.xml'
            path.write_text('<broken')
            with self.assertRaises(ET.ParseError):
                module.configure(path)
            self.assertEqual(path.read_text(), '<broken')

    def test_first_start_creates_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config' / 'encoding.xml'
            module.configure(path)
            self.assertEqual(ET.parse(path).getroot().findtext('EnableSegmentDeletion'), 'true')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()

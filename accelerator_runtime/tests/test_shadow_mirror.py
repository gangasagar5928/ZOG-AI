"""
Unit tests for HostPinnedShadowMirror.
"""

import unittest
from src.model.member1_model import create_or_load_member1_model
from src.model.shadow_mirror import HostPinnedShadowMirror


class TestHostPinnedShadowMirror(unittest.TestCase):

    def setUp(self):
        self.model = create_or_load_member1_model()
        self.mirror = HostPinnedShadowMirror(self.model, pin_memory=False)

    def test_allocation_and_metadata(self):
        """Shadow mirror should mirror all parameters and track byte footprints."""
        buffers = self.mirror.get_all_buffers()
        self.assertGreater(len(buffers), 0)
        self.assertGreater(self.mirror.total_param_bytes, 0)

        summary = self.mirror.get_summary()
        self.assertIn("total_bytes", summary)
        self.assertIn("total_mb", summary)

    def test_integrity_check(self):
        """Golden checksums should detect when parameters are unaltered vs corrupted."""
        is_intact, corrupted = self.mirror.verify_integrity(self.model)
        self.assertTrue(is_intact)
        self.assertEqual(len(corrupted), 0)


if __name__ == "__main__":
    unittest.main()

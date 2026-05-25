"""Tests for terrain utility functions in main.py.

Targets:
    - get_ground_y() with normal range, edge cases, segment mapping.
"""

import pytest

from main import get_ground_y, TERRAIN_SEGMENT, LEVEL_WIDTH


class TestGetGroundY:
    """Tests for get_ground_y(terrain, x)."""

    def test_normal_range(self, sample_terrain):
        """get_ground_y returns the correct height for mid-level x."""
        # At x=0, segment 0 -> terrain[0] = 500
        assert get_ground_y(sample_terrain, 0) == 500

        # At x=1000, segment 50 -> terrain[50] = 400 (the bump)
        assert get_ground_y(sample_terrain, 1000) == 400

        # At x=1020 (segment 51) -> back to 500
        assert get_ground_y(sample_terrain, 1020) == 500

    def test_edge_x_zero(self, sample_terrain):
        """get_ground_y handles x=0 correctly (segment 0)."""
        assert get_ground_y(sample_terrain, 0) == 500

    def test_edge_x_level_width_minus_one(self, sample_terrain):
        """get_ground_y handles x=LEVEL_WIDTH-1 correctly (last segment)."""
        assert get_ground_y(sample_terrain, LEVEL_WIDTH - 1) == 500

    def test_negative_x_clamped(self, sample_terrain):
        """get_ground_y clamps negative x to segment 0."""
        assert get_ground_y(sample_terrain, -1) == 500
        assert get_ground_y(sample_terrain, -1000) == 500

    def test_oversized_x_clamped(self, sample_terrain):
        """get_ground_y clamps x beyond LEVEL_WIDTH to last segment."""
        assert get_ground_y(sample_terrain, LEVEL_WIDTH) == 500
        assert get_ground_y(sample_terrain, LEVEL_WIDTH + 1000) == 500

    def test_segment_mapping_via_integer_division(self, sample_terrain):
        """Segment index is x // TERRAIN_SEGMENT.

        Verify boundaries around the bump at segment 50.
        """
        # Segment 49: x in [980, 999]
        assert get_ground_y(sample_terrain, 980) == 500
        assert get_ground_y(sample_terrain, 999) == 500

        # Segment 50: x in [1000, 1019] -> terrain[50] = 400
        assert get_ground_y(sample_terrain, 1000) == 400
        assert get_ground_y(sample_terrain, 1019) == 400

        # Segment 51: x in [1020, 1039] -> back to 500
        assert get_ground_y(sample_terrain, 1020) == 500
        assert get_ground_y(sample_terrain, 1039) == 500

    def test_known_bump_segment(self, sample_terrain):
        """The bump at segment 50 returns 400, all others return 500."""
        for seg_idx in range(len(sample_terrain)):
            x = seg_idx * TERRAIN_SEGMENT  # left edge of segment
            y = get_ground_y(sample_terrain, x)
            if seg_idx == 50:
                assert y == 400, f"Segment {seg_idx} should be 400, got {y}"
            else:
                assert y == 500, f"Segment {seg_idx} should be 500, got {y}"

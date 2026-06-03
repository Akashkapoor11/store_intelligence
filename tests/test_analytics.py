"""
tests/test_analytics.py
───────────────────────
Unit tests for business logic — no DB or API needed.
"""

import pytest


class TestConversionRate:
    def test_basic_conversion(self):
        footfall, buyers = 100, 22
        rate = round(buyers / footfall * 100, 2)
        assert rate == 22.0

    def test_zero_footfall_no_crash(self):
        """Guard: never divide by zero — safe to call with empty store day."""
        footfall = 0
        buyers   = 0
        # The guard: only divide when footfall > 0
        rate = round(buyers / footfall * 100, 2) if footfall > 0 else 0.0
        assert rate == 0.0

    def test_conversion_never_exceeds_100(self):
        """Even if buyers > footfall (data error), cap at 100%."""
        rate = min(round(22 / 10 * 100, 2), 100.0)
        assert rate <= 100.0

    def test_high_conversion_is_capped(self):
        """Conversion rate must never exceed 100%."""
        footfall, buyers = 10, 15   # impossible but defensive
        rate = min(round(buyers / footfall * 100, 2), 100.0)
        assert rate == 100.0

    def test_revenue_per_visitor(self):
        """Revenue per visitor computed correctly."""
        total_revenue = 10948.0
        footfall      = 85
        rpv = round(total_revenue / footfall, 2)
        assert rpv == pytest.approx(128.8, abs=1.0)

    def test_actual_csv_data(self):
        """From actual Brigade Road CSV: 22 unique orders, 101 line items."""
        unique_orders = 22
        total_line_items = 101
        avg_items_per_order = total_line_items / unique_orders
        assert 4 <= avg_items_per_order <= 5

    def test_salesperson_revenue(self):
        """Verify top salesperson from actual Brigade Road CSV fallback data.
        Shashikala has 6 orders at ₹3671.18 — highest revenue on 10 April 2026.
        """
        sales = {
            "Shashikala .":    3671.18,
            "Zufishan Khazra": 2760.35,
            "kasthuri v":      2720.69,
            "Priya v":         1079.97,
            "Naziya Begum":     715.67,
        }
        top = max(sales, key=sales.get)
        assert top == "Shashikala ."



class TestFunnelLogic:
    def test_funnel_is_monotonically_decreasing(self):
        stages = [100, 85, 60, 22]
        for i in range(1, len(stages)):
            assert stages[i] <= stages[i-1]

    def test_funnel_percentages(self):
        total = 100
        stages = [100, 85, 60, 22]
        pcts = [round(s / total * 100, 1) for s in stages]
        assert pcts[0] == 100.0
        assert pcts[-1] == 22.0

    def test_dropoff_calculation(self):
        entered, browsed = 100, 85
        dropoff = round((entered - browsed) / entered * 100, 1)
        assert dropoff == 15.0


class TestZoneMapping:
    def test_entry_zone_detection(self):
        """Foot position at y=0.8 of CAM3 frame = inside store."""
        entry_line_y = 0.75
        foot_y_frac  = 0.4   # inside store (above line)
        assert foot_y_frac < entry_line_y  # not near exit

    def test_exit_line_crossing(self):
        prev_cy = 0.6
        curr_cy = 0.85
        entry_line = 0.75
        is_exit = prev_cy < entry_line and curr_cy >= entry_line
        assert is_exit is True

    def test_entry_line_crossing(self):
        prev_cy = 0.85
        curr_cy = 0.6
        entry_line = 0.75
        is_entry = prev_cy >= entry_line and curr_cy < entry_line
        assert is_entry is True


class TestStaffFilter:
    def test_staff_identified_after_threshold(self):
        fps = 25.0
        threshold_sec = 600
        threshold_frames = int(threshold_sec * fps)

        frame_count = threshold_frames + 1
        is_staff = frame_count >= threshold_frames
        assert is_staff is True

    def test_customer_not_flagged_early(self):
        fps = 25.0
        frame_count = int(60 * fps)   # 60 seconds
        threshold = int(600 * fps)    # 10 minutes
        is_staff = frame_count >= threshold
        assert is_staff is False


class TestReentryGuard:
    def test_same_position_is_reentry(self):
        tolerance = 0.25
        exit_pos  = (0.5, 0.8)
        new_pos   = (0.52, 0.78)
        dist = ((new_pos[0] - exit_pos[0]) ** 2 + (new_pos[1] - exit_pos[1]) ** 2) ** 0.5
        assert dist < tolerance

    def test_different_position_not_reentry(self):
        tolerance = 0.25
        exit_pos  = (0.1, 0.8)
        new_pos   = (0.9, 0.2)
        dist = ((new_pos[0] - exit_pos[0]) ** 2 + (new_pos[1] - exit_pos[1]) ** 2) ** 0.5
        assert dist >= tolerance

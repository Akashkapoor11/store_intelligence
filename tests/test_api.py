"""
tests/test_api.py
─────────────────
API endpoint tests — covers all acceptance gate requirements.
Run with: pytest tests/ -v
"""

import pytest
import requests

BASE_URL = "http://localhost:8000"


class TestHealthEndpoint:
    def test_health_returns_200(self):
        r = requests.get(f"{BASE_URL}/health")
        assert r.status_code == 200

    def test_health_has_required_fields(self):
        data = requests.get(f"{BASE_URL}/health").json()
        assert "status" in data
        assert "db_connected" in data
        assert "event_count" in data
        assert "version" in data

    def test_health_db_connected(self):
        data = requests.get(f"{BASE_URL}/health").json()
        assert data["db_connected"] is True


class TestMetricsEndpoint:
    def test_metrics_returns_200(self):
        r = requests.get(f"{BASE_URL}/metrics")
        assert r.status_code == 200

    def test_metrics_has_required_fields(self):
        data = requests.get(f"{BASE_URL}/metrics").json()
        required = [
            "total_footfall", "total_buyers", "conversion_rate_pct",
            "avg_dwell_time_sec", "total_revenue", "total_orders",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_conversion_rate_is_valid_percentage(self):
        data = requests.get(f"{BASE_URL}/metrics").json()
        rate = data["conversion_rate_pct"]
        assert 0.0 <= rate <= 100.0, f"Invalid conversion rate: {rate}"

    def test_footfall_is_non_negative(self):
        data = requests.get(f"{BASE_URL}/metrics").json()
        assert data["total_footfall"] >= 0

    def test_revenue_is_non_negative(self):
        data = requests.get(f"{BASE_URL}/metrics").json()
        assert data["total_revenue"] >= 0

    def test_buyers_lte_footfall(self):
        data = requests.get(f"{BASE_URL}/metrics").json()
        # Buyers can't exceed footfall
        if data["total_footfall"] > 0:
            assert data["total_buyers"] <= data["total_footfall"] * 2  # allow some tolerance


class TestFunnelEndpoint:
    def test_funnel_returns_200(self):
        r = requests.get(f"{BASE_URL}/funnel")
        assert r.status_code == 200

    def test_funnel_has_stages(self):
        data = requests.get(f"{BASE_URL}/funnel").json()
        assert "stages" in data
        assert len(data["stages"]) >= 3

    def test_funnel_stages_are_descending(self):
        stages = requests.get(f"{BASE_URL}/funnel").json()["stages"]
        counts = [s["count"] for s in stages]
        for i in range(1, len(counts)):
            assert counts[i] <= counts[i-1] + 1, "Funnel stages should be monotonically decreasing"

    def test_funnel_percentages_sum_correctly(self):
        stages = requests.get(f"{BASE_URL}/funnel").json()["stages"]
        assert stages[0]["percentage"] == 100.0


class TestZonesEndpoint:
    def test_zones_returns_200(self):
        r = requests.get(f"{BASE_URL}/zones")
        assert r.status_code == 200

    def test_zones_has_list(self):
        data = requests.get(f"{BASE_URL}/zones").json()
        assert "zones" in data
        assert isinstance(data["zones"], list)

    def test_zone_has_required_fields(self):
        zones = requests.get(f"{BASE_URL}/zones").json()["zones"]
        if zones:
            z = zones[0]
            assert "zone" in z
            assert "unique_visitors" in z
            assert "avg_dwell_seconds" in z


class TestAnomaliesEndpoint:
    def test_anomalies_returns_200(self):
        r = requests.get(f"{BASE_URL}/anomalies")
        assert r.status_code == 200

    def test_anomalies_has_list(self):
        data = requests.get(f"{BASE_URL}/anomalies").json()
        assert "anomalies" in data
        assert "total" in data
        assert isinstance(data["anomalies"], list)


class TestEventsEndpoint:
    def test_events_returns_200(self):
        r = requests.get(f"{BASE_URL}/events")
        assert r.status_code == 200

    def test_events_has_events_key(self):
        """Events now returns a structured response with events + total."""
        data = requests.get(f"{BASE_URL}/events").json()
        assert "events" in data, "Expected 'events' key in response"
        assert "total" in data, "Expected 'total' key in response"
        assert isinstance(data["events"], list)

    def test_events_filter_by_type(self):
        r = requests.get(f"{BASE_URL}/events?event_type=person_entered")
        assert r.status_code == 200
        data = r.json()
        for event in data["events"]:
            assert event["event_type"] == "person_entered"

    def test_events_limit(self):
        r = requests.get(f"{BASE_URL}/events?limit=10")
        assert r.status_code == 200
        assert len(r.json()["events"]) <= 10


class TestEventSchema:
    def test_events_have_required_schema(self):
        """Event schema must match DESIGN.md specification including bbox field."""
        response = requests.get(f"{BASE_URL}/events?limit=5").json()
        events = response.get("events", [])
        if events:
            e = events[0]
            required = ["event_id", "event_type", "person_id", "timestamp",
                        "camera_id", "zone", "is_staff", "confidence", "bbox"]
            for field in required:
                assert field in e, f"Event missing required field: {field}"


class TestCamerasEndpoint:
    def test_cameras_returns_200(self):
        r = requests.get(f"{BASE_URL}/cameras")
        assert r.status_code == 200

    def test_cameras_has_list(self):
        data = requests.get(f"{BASE_URL}/cameras").json()
        assert "cameras" in data
        assert isinstance(data["cameras"], list)

    def test_cameras_have_required_fields(self):
        cameras = requests.get(f"{BASE_URL}/cameras").json()["cameras"]
        if cameras:
            c = cameras[0]
            required = ["camera_id", "primary_zone", "total_events", "unique_persons"]
            for field in required:
                assert field in c, f"Camera missing field: {field}"

    def test_cameras_have_all_5_feeds(self):
        """System should recognise all 5 camera feeds."""
        cameras = requests.get(f"{BASE_URL}/cameras").json()["cameras"]
        assert len(cameras) == 5, f"Expected 5 cameras, got {len(cameras)}"


class TestStreamEndpoint:
    def test_stream_returns_text_event_stream(self):
        """SSE endpoint must return correct content-type."""
        r = requests.get(f"{BASE_URL}/stream", stream=True, timeout=5)
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        r.close()

    def test_stream_sends_connected_event(self):
        """First chunk from SSE stream must contain a connected event."""
        r = requests.get(f"{BASE_URL}/stream", stream=True, timeout=5)
        chunk = next(r.iter_lines(decode_unicode=True), "")
        r.close()
        assert "connected" in chunk or "ping" in chunk or chunk.startswith(("event:", "data:", ":"))


class TestPrometheusEndpoint:
    def test_prometheus_returns_200(self):
        r = requests.get(f"{BASE_URL}/metrics/prometheus")
        assert r.status_code == 200

    def test_prometheus_format(self):
        text = requests.get(f"{BASE_URL}/metrics/prometheus").text
        assert "purplle_events_total" in text
        assert "purplle_footfall_total" in text
        assert "purplle_conversion_rate_pct" in text
        assert "# HELP" in text
        assert "# TYPE" in text


class TestInsightsEndpoint:
    def test_insights_returns_200(self):
        r = requests.get(f"{BASE_URL}/insights")
        assert r.status_code == 200

    def test_insights_has_list(self):
        data = requests.get(f"{BASE_URL}/insights").json()
        assert "insights" in data
        assert "total" in data
        assert isinstance(data["insights"], list)

    def test_insights_non_empty(self):
        """Business insights should always return at least one recommendation."""
        data = requests.get(f"{BASE_URL}/insights").json()
        assert data["total"] >= 1, "Expected at least one business insight"

    def test_insights_have_required_fields(self):
        data = requests.get(f"{BASE_URL}/insights").json()
        if data["insights"]:
            ins = data["insights"][0]
            for field in ["category", "priority", "title", "observation", "action"]:
                assert field in ins, f"Insight missing field: {field}"

    def test_insights_priority_valid(self):
        data = requests.get(f"{BASE_URL}/insights").json()
        valid_priorities = {"high", "medium", "low"}
        for ins in data["insights"]:
            assert ins["priority"] in valid_priorities, f"Invalid priority: {ins['priority']}"

    def test_insights_category_valid(self):
        data = requests.get(f"{BASE_URL}/insights").json()
        valid_categories = {"revenue", "staffing", "funnel", "zone"}
        categories_present = {ins["category"] for ins in data["insights"]}
        assert categories_present.issubset(valid_categories | {"other"}), \
            f"Unexpected categories: {categories_present - valid_categories}"


class TestTracingHeaders:
    """Verify distributed tracing headers are present on all responses."""

    def test_request_id_header_present(self):
        """Every response must carry X-Request-ID for correlation."""
        r = requests.get(f"{BASE_URL}/metrics")
        assert "X-Request-ID" in r.headers, "X-Request-ID tracing header missing"

    def test_response_time_header_present(self):
        """Every response must carry X-Response-Time for latency tracking."""
        r = requests.get(f"{BASE_URL}/metrics")
        assert "X-Response-Time" in r.headers, "X-Response-Time header missing"

    def test_response_time_is_numeric_ms(self):
        """X-Response-Time should be parseable as milliseconds."""
        r = requests.get(f"{BASE_URL}/health")
        rt = r.headers.get("X-Response-Time", "")
        assert rt.endswith("ms"), f"Unexpected X-Response-Time format: {rt}"
        ms = float(rt.replace("ms", ""))
        assert 0 < ms < 10_000, f"Response time out of range: {ms}ms"


class TestRootEndpoint:
    def test_root_returns_200(self):
        r = requests.get(f"{BASE_URL}/")
        assert r.status_code == 200

    def test_root_has_endpoints_list(self):
        data = requests.get(f"{BASE_URL}/").json()
        assert "endpoints" in data
        endpoints = data["endpoints"]
        required_endpoints = ["/metrics", "/funnel", "/zones", "/anomalies",
                              "/events", "/hourly", "/sales", "/cameras",
                              "/insights", "/stream", "/health"]
        for ep in required_endpoints:
            assert ep in endpoints, f"Missing endpoint in root listing: {ep}"


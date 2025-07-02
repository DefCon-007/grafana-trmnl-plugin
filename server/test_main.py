import json
import os
import unittest
from unittest.mock import patch

from main import app


class TestRenderEndpoint(unittest.TestCase):
    def setUp(self):
        """Set up test client"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Create test data directory path
        self.test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")

    def load_test_data(self, filename):
        """Load test data from JSON file"""
        filepath = os.path.join(self.test_data_dir, filename)
        with open(filepath, "r") as f:
            return json.load(f)

    @patch("main._get_panel_data")
    def test_render_stat_panel(self, mock_get_panel_data):
        """Test rendering a stat panel"""
        # Load test data
        test_data = self.load_test_data("stat_panel_data.json")
        mock_get_panel_data.return_value = test_data

        # Make request
        response = self.client.post(
            "/render",
            json={
                "grafana_token": "test_token",
                "panel_url": "test_url",
                "full_html": False,
            },
        )

        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertIn("html", response_data)
        self.assertIn("generated_at", response_data)

        # Check that HTML contains expected elements for stat panel
        html_content = response_data["html"]
        self.assertIn("chart", html_content)
        # Check for stat panel specific elements
        self.assertTrue(
            "1,234" in html_content
            or "1234" in html_content
            or "stat" in html_content.lower()
        )

    @patch("main._get_panel_data")
    def test_render_gauge_panel(self, mock_get_panel_data):
        """Test rendering a gauge panel"""
        test_data = self.load_test_data("gauge_panel_data.json")
        mock_get_panel_data.return_value = test_data

        response = self.client.post(
            "/render",
            json={
                "grafana_token": "test_token",
                "panel_url": "test_url",
                "full_html": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertIn("html", response_data)

        # Check for gauge-specific elements
        html_content = response_data["html"]
        self.assertIn("gauge", html_content.lower())
        self.assertIn("chart", html_content)

    @patch("main._get_panel_data")
    def test_render_timeseries_panel(self, mock_get_panel_data):
        """Test rendering a timeseries panel"""
        test_data = self.load_test_data("timeseries_panel_data.json")
        mock_get_panel_data.return_value = test_data

        response = self.client.post(
            "/render",
            json={
                "grafana_token": "test_token",
                "panel_url": "test_url",
                "full_html": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertIn("html", response_data)

        # Check for timeseries-specific elements
        html_content = response_data["html"]
        self.assertIn("chart", html_content)
        self.assertIn("LineChart", html_content or "line" in html_content.lower())

    @patch("main._get_panel_data")
    def test_render_bar_gauge_panel(self, mock_get_panel_data):
        """Test rendering a bar gauge panel"""
        test_data = self.load_test_data("bar_gauge_panel_data.json")
        mock_get_panel_data.return_value = test_data

        response = self.client.post(
            "/render",
            json={
                "grafana_token": "test_token",
                "panel_url": "test_url",
                "full_html": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertIn("html", response_data)

        # Check for bar chart elements
        html_content = response_data["html"]
        self.assertIn("BarChart", html_content)

    @patch("main._get_panel_data")
    def test_render_piechart_panel(self, mock_get_panel_data):
        """Test rendering a pie chart panel"""
        test_data = self.load_test_data("piechart_panel_data.json")
        mock_get_panel_data.return_value = test_data

        response = self.client.post(
            "/render",
            json={
                "grafana_token": "test_token",
                "panel_url": "test_url",
                "full_html": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertIn("html", response_data)

        # Check for pie chart elements
        html_content = response_data["html"]
        self.assertIn("PieChart", html_content)

    @patch("main._get_panel_data")
    def test_render_table_panel(self, mock_get_panel_data):
        """Test rendering a table panel"""
        test_data = self.load_test_data("table_panel_data.json")
        mock_get_panel_data.return_value = test_data

        response = self.client.post(
            "/render",
            json={
                "grafana_token": "test_token",
                "panel_url": "test_url",
                "full_html": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertIn("html", response_data)

        # Check for table/column chart elements
        html_content = response_data["html"]
        self.assertIn("ColumnChart", html_content)

    @patch("main._get_panel_data")
    def test_render_full_html(self, mock_get_panel_data):
        """Test rendering with full_html=True"""
        test_data = self.load_test_data("stat_panel_data.json")
        mock_get_panel_data.return_value = test_data

        response = self.client.post(
            "/render",
            json={
                "grafana_token": "test_token",
                "panel_url": "test_url",
                "full_html": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        # Should return HTML content directly, not JSON
        self.assertEqual(response.content_type, "text/html; charset=utf-8")

        # Check for full HTML structure
        html_content = response.get_data(as_text=True)
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn("<html>", html_content)
        self.assertIn("<head>", html_content)
        self.assertIn("<body", html_content)  # Allow for body tag with attributes

    @patch("main._get_panel_data")
    def test_render_multi_series_timeseries(self, mock_get_panel_data):
        """Test rendering a multi-series timeseries panel"""
        test_data = self.load_test_data("multi_series_timeseries_data.json")
        mock_get_panel_data.return_value = test_data

        response = self.client.post(
            "/render",
            json={
                "grafana_token": "test_token",
                "panel_url": "test_url",
                "full_html": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertIn("html", response_data)

        # Check for multi-series elements
        html_content = response_data["html"]
        self.assertIn("chart", html_content)
        # Should use Highcharts for multi-series
        self.assertIn("Highcharts.chart", html_content)

    def test_render_missing_data(self):
        """Test render endpoint with missing request data"""
        response = self.client.post("/render", json={})

        # Should return error due to missing required fields
        self.assertNotEqual(response.status_code, 200)

    def test_render_invalid_json(self):
        """Test render endpoint with invalid JSON"""
        response = self.client.post(
            "/render", data="invalid json", content_type="application/json"
        )

        # Should return error due to invalid JSON
        self.assertNotEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()

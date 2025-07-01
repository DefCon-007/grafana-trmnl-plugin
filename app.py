from flask import Flask, jsonify, request
from grafana_utils import (
    apply_template_variables,
    get_dashboard_metadata,
    parse_panel_url,
    query_grafana_panel,
)
from html_utils import CHART_TYPE_MAP, generate_html

app = Flask(__name__)


@app.route("/render", methods=["POST"])
def render_chart():
    try:
        data = request.get_json()
        token = data["grafana_token"]
        panel_url = data["panel_url"]
        full_html = data.get("full_html", False)

        # Get time range from request body, with defaults
        fr = data.get("from", "now-6h")
        to = data.get("to", "now")

        # Parse URL and extract variables
        host, uid, panel_id, variables = parse_panel_url(panel_url)

        if not uid or not panel_id:
            return jsonify({"error": "Invalid panel_url"}), 400

        # Fetch dashboard metadata
        dashboard = get_dashboard_metadata(host, uid, token)

        panel = next(
            (p for p in dashboard["dashboard"]["panels"] if str(p["id"]) == panel_id),
            None,
        )

        if not panel:
            return jsonify({"error": "Panel not found"}), 404

        targets = panel.get("targets", [])
        if not targets:
            return jsonify({"error": "No targets found in panel"}), 400

        panel_type = panel.get("type", "timeseries").lower()
        chartkick_type = CHART_TYPE_MAP.get(panel_type, "LineChart")
        original_panel_type = panel_type

        # Apply template variables to targets
        processed_targets = apply_template_variables(targets, variables)

        # Query Grafana and process response
        response_data, data_series, detected_chart_type = query_grafana_panel(
            host, token, processed_targets, fr, to, original_panel_type
        )

        # Use detected chart type if available
        if detected_chart_type:
            chartkick_type = detected_chart_type

        # Generate HTML
        html = generate_html(
            chartkick_type,
            data_series,
            title=panel.get("title", "Grafana Panel"),
            original_panel_type=original_panel_type,
            full_html=full_html,
        )
        return html

    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/query", methods=["POST"])
def query_panel():
    """
    Endpoint that returns raw query results from Grafana panel
    without HTML rendering
    """
    try:
        data = request.get_json()
        token = data["grafana_token"]
        panel_url = data["panel_url"]

        # Get time range from request body, with defaults
        fr = data.get("from", "now-6h")
        to = data.get("to", "now")

        # Parse URL and extract variables
        host, uid, panel_id, variables = parse_panel_url(panel_url)

        if not uid or not panel_id:
            return jsonify({"error": "Invalid panel_url"}), 400

        # Fetch dashboard metadata
        dashboard = get_dashboard_metadata(host, uid, token)

        panel = next(
            (p for p in dashboard["dashboard"]["panels"] if str(p["id"]) == panel_id),
            None,
        )

        if not panel:
            return jsonify({"error": "Panel not found"}), 404

        targets = panel.get("targets", [])
        if not targets:
            return jsonify({"error": "No targets found in panel"}), 400

        panel_type = panel.get("type", "timeseries").lower()
        original_panel_type = panel_type

        # Apply template variables to targets
        processed_targets = apply_template_variables(targets, variables)

        # Query Grafana and process response
        response_data, data_series, detected_chart_type = query_grafana_panel(
            host, token, processed_targets, fr, to, original_panel_type
        )

        # Return structured data
        return jsonify(
            {
                "panel_type": panel_type,
                "panel_title": panel.get("title", "Grafana Panel"),
                "detected_chart_type": detected_chart_type,
                "data_series": data_series,
                "raw_response": response_data,
                "processed_targets": processed_targets,
                "variables": variables,
            }
        )

    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


if __name__ == "__main__":
    app.run(debug=True)

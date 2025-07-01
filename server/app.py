import logging
import traceback
from datetime import datetime

from exceptions import (
    DashboardMetadataException,
    GrafanaException,
    GrafanaQueryException,
    InvalidPanelUrlException,
    NoTargetsException,
    PanelNotFoundException,
)
from flask import Flask, jsonify, make_response, request
from grafana_utils import (
    apply_template_variables,
    get_dashboard_metadata,
    parse_panel_url,
    query_grafana_panel,
)
from html_utils import CHART_TYPE_MAP, generate_html

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_error_html(error_message, title="Error"):
    """Generate HTML for error messages"""
    return f"""
    <div style="padding: 20px; font-family: Arial, sans-serif;">
        <h2 style="color: #d32f2f;">{title}</h2>
        <p style="color: #666;">{error_message}</p>
    </div>
    """


@app.errorhandler(GrafanaException)
def handle_grafana_exception(error):
    """Centralized error handler for custom Grafana exceptions"""
    logger.error(f"Grafana exception: {error.message}")

    # Check if this is a render request that should return HTML format
    if request.endpoint == "render_chart" and request.method == "POST":
        try:
            data = request.get_json()
            full_html = data.get("full_html", False) if data else False

            if not full_html:
                # Return error in the same format as success response
                error_html = generate_error_html(error.message)
                return jsonify(
                    {"html": error_html, "generated_at": datetime.now().isoformat()}
                ), error.status_code
            else:
                # Return full HTML response
                error_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Error</title>
    <meta charset="utf-8">
</head>
<body>
    {generate_error_html(error.message)}
</body>
</html>"""
                response = make_response(error_html)
                response.headers["Content-Type"] = "text/html; charset=utf-8"
                return response, error.status_code
        except Exception:
            # If we can't determine the format, default to JSON
            pass

    # Default JSON error response
    return jsonify({"error": error.message}), error.status_code


@app.errorhandler(Exception)
def handle_general_exception(error):
    """Handler for unexpected exceptions"""
    error_msg = str(error)
    stack_trace = traceback.format_exc()

    logger.error(f"Unexpected exception: {error_msg}")
    logger.error(f"Stack trace:\n{stack_trace}")

    # Check if this is a render request that should return HTML format
    if request.endpoint == "render_chart" and request.method == "POST":
        try:
            data = request.get_json()
            full_html = data.get("full_html", False) if data else False

            if not full_html:
                # Return error in the same format as success response
                error_html = generate_error_html(f"Internal server error: {error_msg}")
                return jsonify(
                    {"html": error_html, "generated_at": datetime.now().isoformat()}
                ), 500
            else:
                # Return full HTML response
                error_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Error</title>
    <meta charset="utf-8">
</head>
<body>
    {generate_error_html(f"Internal server error: {error_msg}")}
</body>
</html>"""
                response = make_response(error_html)
                response.headers["Content-Type"] = "text/html; charset=utf-8"
                return response, 500
        except Exception:
            # If we can't determine the format, default to JSON
            pass

    # Default JSON error response
    return jsonify({"error": error_msg, "traceback": stack_trace}), 500


@app.route("/render", methods=["POST"])
def render_chart():
    data = request.get_json()
    logger.info(f"Render request data: {data}")
    token = data["grafana_token"]
    panel_url = data["panel_url"]
    full_html = data.get("full_html", False)

    # Get time range from request body, with defaults
    fr = data.get("from", "now-6h")
    to = data.get("to", "now")

    # Parse URL and extract variables
    host, uid, panel_id, variables = parse_panel_url(panel_url)

    if not uid or not panel_id:
        raise InvalidPanelUrlException()

    # Fetch dashboard metadata
    try:
        dashboard = get_dashboard_metadata(host, uid, token)
    except Exception as e:
        raise DashboardMetadataException(f"Error fetching dashboard metadata: {str(e)}")

    panel = next(
        (p for p in dashboard["dashboard"]["panels"] if str(p["id"]) == panel_id),
        None,
    )

    if not panel:
        raise PanelNotFoundException()

    targets = panel.get("targets", [])
    if not targets:
        raise NoTargetsException()

    panel_type = panel.get("type", "timeseries").lower()
    chartkick_type = CHART_TYPE_MAP.get(panel_type, "LineChart")
    original_panel_type = panel_type

    # Apply template variables to targets
    processed_targets = apply_template_variables(targets, variables)

    # Query Grafana and process response
    try:
        response_data, data_series, detected_chart_type = query_grafana_panel(
            host, token, processed_targets, fr, to, original_panel_type
        )
    except Exception as e:
        raise GrafanaQueryException(f"Error querying Grafana panel: {str(e)}")

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
    if full_html:
        response = make_response(html)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response
    else:
        return {"html": html, "generated_at": datetime.now().isoformat()}


@app.route("/query", methods=["POST"])
def query_panel():
    """
    Endpoint that returns raw query results from Grafana panel
    without HTML rendering
    """
    data = request.get_json()
    token = data["grafana_token"]
    panel_url = data["panel_url"]

    # Get time range from request body, with defaults
    fr = data.get("from", "now-6h")
    to = data.get("to", "now")

    # Parse URL and extract variables
    host, uid, panel_id, variables = parse_panel_url(panel_url)

    if not uid or not panel_id:
        raise InvalidPanelUrlException()

    # Fetch dashboard metadata
    try:
        dashboard = get_dashboard_metadata(host, uid, token)
    except Exception as e:
        raise DashboardMetadataException(f"Error fetching dashboard metadata: {str(e)}")

    panel = next(
        (p for p in dashboard["dashboard"]["panels"] if str(p["id"]) == panel_id),
        None,
    )

    if not panel:
        raise PanelNotFoundException()

    targets = panel.get("targets", [])
    if not targets:
        raise NoTargetsException()

    panel_type = panel.get("type", "timeseries").lower()
    original_panel_type = panel_type

    # Apply template variables to targets
    processed_targets = apply_template_variables(targets, variables)

    # Query Grafana and process response
    try:
        response_data, data_series, detected_chart_type = query_grafana_panel(
            host, token, processed_targets, fr, to, original_panel_type
        )
    except Exception as e:
        raise GrafanaQueryException(f"Error querying Grafana panel: {str(e)}")

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


if __name__ == "__main__":
    app.run(debug=True)

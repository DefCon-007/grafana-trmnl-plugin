import logging
import os
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
from html_utils import generate_html

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


def _get_panel_data(data):
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

    return {
        "panel_type": panel_type,
        "panel_title": panel.get("title", "Grafana Panel"),
        "detected_chart_type": detected_chart_type,
        "data_series": data_series,
        "raw_response": response_data,
        "processed_targets": processed_targets,
        "variables": variables,
    }


@app.route("/", methods=["GET"])
def index():
    """
    Home page that explains what this server can do
    """
    html_content = (
        """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Grafana TRMNL Plugin Server</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 800px; background: white; padding: 30px; border-radius: 8px; """
        + """box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; border-bottom: 2px solid #007acc; padding-bottom: 10px; }
            h2 { color: #007acc; margin-top: 30px; }
            .endpoint { background: #f8f9fa; padding: 15px; """
        + """border-left: 4px solid #007acc; margin: 15px 0; }
            .method { color: #28a745; font-weight: bold; }
            code { background: #e9ecef; padding: 2px 6px; border-radius: 3px; """
        + """font-family: 'Courier New', monospace; }
            pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }
            .status { color: #28a745; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔗 Grafana TRMNL Plugin Server</h1>
            <p><span class="status">✅ Server is running</span> - Ready to process Grafana panel requests</p>

            <h2>📋 What This Server Does</h2>
            <p>This server converts Grafana dashboard panels into HTML format suitable for display on TRMNL devices. It fetches data from Grafana APIs and generates clean, readable HTML charts.</p>

            <h2>🚀 Available Endpoints</h2>

            <div class="endpoint">
                <h3><span class="method">POST</span> /render</h3>
                <p><strong>Purpose:</strong> Render a Grafana panel as HTML</p>
                <p><strong>Required fields:</strong></p>
                <ul>
                    <li><code>grafana_token</code> - Your Grafana API token</li>
                    <li><code>panel_url</code> - URL to the Grafana panel</li>
                </ul>
                <p><strong>Optional fields:</strong></p>
                <ul>
                    <li><code>from</code> - Start time (default: "now-6h")</li>
                    <li><code>to</code> - End time (default: "now")</li>
                    <li><code>full_html</code> - Return complete HTML page (default: false)</li>
                </ul>
                <p><strong>Response:</strong> HTML content or JSON with HTML snippet</p>
            </div>

            <div class="endpoint">
                <h3><span class="method">POST</span> /query</h3>
                <p><strong>Purpose:</strong> Get raw query results from a Grafana panel without HTML rendering</p>
                <p><strong>Required fields:</strong> Same as /render endpoint</p>
                <p><strong>Response:</strong> JSON with raw panel data, series, and metadata</p>
            </div>

            <h2>💡 Example Usage</h2>
            <pre><code>curl -X POST http://localhost:8080/render \\
  -H "Content-Type: application/json" \\
  -d '{
    "grafana_token": "your-api-token",
    "panel_url": "https://your-grafana.com/d/dashboard-uid?orgId=1&viewPanel=1",
    "from": "now-1h",
    "to": "now",
    "full_html": false
  }'</code></pre>

            <h2>🔧 Features</h2>
            <ul>
                <li>✅ Supports multiple chart types (timeseries, bar, pie, etc.)</li>
                <li>✅ Template variable support</li>
                <li>✅ Automatic chart type detection</li>
                <li>✅ Error handling with detailed messages</li>
                <li>✅ Both JSON and full HTML response formats</li>
                <li>✅ Configurable time ranges</li>
            </ul>

            <h2>🐳 Docker</h2>
            <p>This server is designed to run in Docker containers and exposes port 8080.</p>

            <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; text-align: center;">
                <p>Grafana TRMNL Plugin Server - Convert Grafana panels to TRMNL-ready HTML</p>
            </footer>
        </div>
    </body>
    </html>
    """
    )

    response = make_response(html_content)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response


@app.route("/render", methods=["POST"])
def render_chart():
    data = request.get_json()
    full_html = data.get("full_html", False)

    panel_data = _get_panel_data(data)

    detected_chart_type = panel_data["detected_chart_type"]
    data_series = panel_data["data_series"]
    panel_type = panel_data["panel_type"]
    panel_title = panel_data["panel_title"]

    # Generate HTML
    html = generate_html(
        detected_chart_type,
        data_series,
        title=panel_title,
        original_panel_type=panel_type,
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

    panel_data = _get_panel_data(data)

    # Return structured data
    return jsonify(panel_data)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

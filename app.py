import datetime

# from pprint import pprint as print
from urllib.parse import parse_qs, urlparse

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

CHART_TYPE_MAP = {
    "timeseries": "LineChart",
    "graph": "LineChart",
    "stat": "ColumnChart",
    "gauge": "ColumnChart",
    "bar gauge": "BarChart",
    "table": "ColumnChart",
    "piechart": "PieChart",
}


def generate_html(
    chart_type, data_series, title="Grafana Panel", original_panel_type=None
):
    # Check if this is a single stat value
    is_stat = isinstance(data_series, dict) and "stat_value" in data_series
    is_gauge = is_stat and (
        original_panel_type == "gauge"
        if original_panel_type
        else chart_type in ["gauge", "Gauge"]
    )

    # Determine if we have multiple series (only for non-stat data)
    is_multi_series = (
        not is_stat and isinstance(data_series, dict) and len(data_series) > 1
    )

    if is_stat:
        # For stat/gauge panels, create a simple data structure
        stat_value = data_series["stat_value"]
        formatted_value = (
            f"{stat_value:,}"
            if isinstance(stat_value, (int, float))
            else str(stat_value)
        )

        if is_gauge:
            # For gauge, we need the numeric value for the gauge chart
            chart_data = {
                "value": float(stat_value)
                if isinstance(stat_value, (int, float))
                else 0
            }
        else:
            # For regular stat, we need both raw and formatted
            chart_data = {"value": stat_value, "formatted": formatted_value}
    elif is_multi_series:
        # Multi-series configuration
        series_config = []
        colors = ["#000000", "#666666", "#999999", "#CCCCCC"]
        patterns = [
            None,  # First series uses solid color
            "https://usetrmnl.com/images/grayscale/gray-5.png",
            "https://usetrmnl.com/images/grayscale/gray-3.png",
            "https://usetrmnl.com/images/grayscale/gray-1.png",
        ]

        for i, (series_name, series_data) in enumerate(data_series.items()):
            color_config = colors[i % len(colors)]
            pattern = patterns[i % len(patterns)]

            if pattern and i > 0:
                color_config = {
                    "pattern": {"image": pattern, "width": 12, "height": 12}
                }

            series_config.append(
                {
                    "name": series_name,
                    "data": series_data,
                    "lineWidth": 4 if i == 0 else 3,
                    "color": color_config,
                    "zIndex": len(data_series) - i,
                }
            )

        chart_data = series_config
    else:
        # Single series - use original format
        if isinstance(data_series, dict):
            chart_data = list(data_series.values())[0]
        else:
            chart_data = data_series

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>{title}</title>
      <script src="https://code.highcharts.com/highcharts.js"></script>
      <script src="https://code.highcharts.com/highcharts-more.js"></script>
      <script src="https://code.highcharts.com/modules/pattern-fill.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/chartkick@5.0.1/dist/chartkick.min.js"></script>
      <style>
        body {{
          font-family: sans-serif;
          padding: 40px;
        }}
        #chart {{
          height: 500px;
        }}
        .stat-container {{
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          height: 500px;
          text-align: center;
        }}
        .stat-value {{
          font-size: 120px;
          font-weight: bold;
          color: #000000;
          line-height: 1;
          font-family: 'Helvetica Neue', Arial, sans-serif;
        }}
        .stat-title {{
          font-size: 18px;
          color: #000000;
          margin-bottom: 20px;
        }}
      </style>
    </head>
    <body>
      <h2>{title}</h2>
      {
        f'''<div class="stat-container">
          <div class="stat-value">{chart_data["formatted"]}</div>
        </div>'''
        if is_stat and not is_gauge
        else '<div id="chart"></div>'
    }
      <script>
        var chartData = {chart_data};

        {
        ""
        if is_stat and not is_gauge
        else '''
        // Gauge chart configuration
        Highcharts.chart("chart", {
          chart: {
            type: "gauge",
            height: 500,
            animation: false,
            spacing: [10, 10, 5, 10]
          },
          title: {
            text: null
          },
          pane: {
            startAngle: -150,
            endAngle: 150,
            background: {
              backgroundColor: "transparent",
              borderWidth: 0
            }
          },
          plotOptions: {
            gauge: {
              animation: false,
              pivot: {
                backgroundColor: "transparent"
              },
              dial: {
                backgroundColor: "transparent",
                baseWidth: 0
              }
            }
          },
          yAxis: {
            min: 0,
            max: 100,
            minorTickInterval: 0,
            tickColor: "#000000",
            tickLength: 40,
            tickPixelInterval: 40,
            tickWidth: 2,
            lineWidth: 0,
            title: {
              text: null
            },
            labels: {
              distance: 15,
              style: {
                fontSize: "16px",
                color: "#000000"
              }
            },
            plotBands: [{
              from: 1,
              to: chartData.value,
              color: {
                pattern: {
                  image: "https://usetrmnl.com/images/grayscale/gray-2.png",
                  width: 12,
                  height: 12
                }
              },
              innerRadius: "82%",
              borderRadius: "50%"
            }, {
              from: chartData.value + 1,
              to: 100,
              color: {
                pattern: {
                  image: "https://usetrmnl.com/images/grayscale/gray-5.png",
                  width: 12,
                  height: 12
                }
              },
              innerRadius: "82%",
              borderRadius: "50%"
            }]
          },
          series: [{
            name: "Value",
            data: [chartData.value],
            dataLabels: {
              format: "{point.y:.2f}",
              borderWidth: 0,
              style: {
                fontSize: "2em",
                fontWeight: "400",
                color: "#000000"
              }
            }
          }],
          credits: {
            enabled: false
          }
        });
        '''
        if is_gauge
        else f'''
        // Multi-series Highcharts configuration
        Highcharts.chart("chart", {{
          chart: {{
            type: "{"line" if chart_type == "LineChart" else "column"}",
            height: 500,
            animation: false,
            spacing: [10, 10, 5, 10]
          }},
          title: {{
            text: null
          }},
          plotOptions: {{
            series: {{
              animation: false,
              enableMouseTracking: true,
              marker: {{
                enabled: false
              }}
            }}
          }},
          series: chartData,
          tooltip: {{
            enabled: true,
            shared: true
          }},
          legend: {{
            enabled: true,
            align: "left",
            verticalAlign: "top",
            layout: "horizontal"
          }},
          yAxis: {{
            labels: {{
              style: {{ fontSize: "12px", color: "#000000" }}
            }},
            gridLineDashStyle: "shortdot",
            gridLineWidth: 1,
            gridLineColor: "#000000",
            tickAmount: 6,
            title: {{
              text: null
            }}
          }},
          xAxis: {{
            type: "datetime",
            labels: {{
              style: {{ fontSize: "12px", color: "#000000" }}
            }},
            lineWidth: 0,
            gridLineDashStyle: "dot",
            tickWidth: 1,
            tickLength: 0,
            gridLineWidth: 1,
            gridLineColor: "#000000",
            tickPixelInterval: 120,
            title: {{
              text: null
            }}
          }},
          credits: {{
            enabled: false
          }}
        }});
        '''
        if is_multi_series
        else f'''
        // Single series Chartkick configuration
        new Chartkick.{chart_type}("chart", chartData, {{
          adapter: "highcharts",
          curve: true,
          colors: ["#000"],
          points: false,
          library: {{
            chart: {{
              animation: false
            }},
            plotOptions: {{
              series: {{
                animation: false,
                lineWidth: 3
              }}
            }},
            yAxis: {{
              gridLineDashStyle: "shortdot",
              tickAmount: 6
            }},
            xAxis: {{
              type: "datetime",
              gridLineDashStyle: "dot",
              tickPixelInterval: 120
            }}
          }}
        }});
        '''
    }
      </script>
    </body>
    </html>
    """


def apply_template_variables(data, variables):
    """Apply template variables to nested JSON data structure"""
    if not variables:
        return data

    def replace_variables_in_string(text):
        """Replace template variables in a string"""
        if not isinstance(text, str):
            return text

        result = text
        for var_name, var_value in variables.items():
            # Convert single values to list for consistent processing
            var_values = [var_value] if not isinstance(var_value, list) else var_value

            # Handle ${var-name} format (URL format)
            placeholder = f"${{var-{var_name}}}"
            if placeholder in result:
                result = result.replace(placeholder, var_values[0])

            # Handle ${name} format (dashboard JSON format)
            placeholder = f"${{{var_name}}}"
            if placeholder in result:
                # If multiple values, join with pipe for regex
                if len(var_values) > 1:
                    var_value_str = "|".join(var_values)
                    # For multi-value vars in Prometheus, often used in regex
                    result = result.replace(placeholder, f"({var_value_str})")
                else:
                    result = result.replace(placeholder, var_values[0])

            # Handle $name format (simple format)
            placeholder = f"${var_name}"
            if placeholder in result:
                # If multiple values, join with pipe for regex
                if len(var_values) > 1:
                    var_value_str = "|".join(var_values)
                    # For multi-value vars in Prometheus, often used in regex
                    result = result.replace(placeholder, f"({var_value_str})")
                else:
                    result = result.replace(placeholder, var_values[0])

        return result

    def process_data(obj):
        """Recursively process data structure"""
        if isinstance(obj, dict):
            return {key: process_data(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [process_data(item) for item in obj]
        elif isinstance(obj, str):
            return replace_variables_in_string(obj)
        else:
            return obj

    return process_data(data)


def parse_panel_url(panel_url):
    parsed = urlparse(panel_url)
    path_parts = parsed.path.strip("/").split("/")
    uid = path_parts[1] if len(path_parts) >= 2 else None
    query_params = parse_qs(parsed.query)
    panel_id_raw = query_params.get("viewPanel", [None])[0]
    panel_id = panel_id_raw.split("-")[-1] if panel_id_raw else None
    host = f"https://{parsed.netloc}"

    # Extract variables from URL
    variables = {}
    for key, values in query_params.items():
        if key.startswith("var-"):
            var_name = key[4:]  # Remove 'var-' prefix
            variables[var_name] = values  # Keep as list like in test.py

    return host, uid, panel_id, variables


def get_dashboard_metadata(host, uid, token):
    dash_res = requests.get(
        f"{host}/api/dashboards/uid/{uid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    dash_res.raise_for_status()
    return dash_res.json()


def process_series_data(x_vals, y_vals, processed_targets, ref_id):
    """Process x and y values into chart data format"""
    # Check if x_vals contains timestamps or categorical data
    is_time_series = True
    if x_vals:
        first_val = x_vals[0]
        if isinstance(first_val, str) or (
            isinstance(first_val, (int, float)) and first_val < 1000000000
        ):
            is_time_series = False

    # Check target format preference
    target_format = "time_series"
    for target in processed_targets:
        if target.get("refId") == ref_id:
            target_format = target.get("format", "time_series")
            break

    if target_format == "table" or not is_time_series:
        # Categorical data (pie charts, bar charts, etc.)
        return [[str(x), y] for x, y in zip(x_vals, y_vals)]
    else:
        # Time series data
        return [
            [
                datetime.datetime.fromtimestamp(float(x) / 1000).isoformat(),
                float(y) if y is not None else 0,
            ]
            for x, y in zip(x_vals, y_vals)
            if x is not None and y is not None
        ]


def get_series_name_from_labels(frame, ref_id):
    """Extract series name from frame labels"""
    if "schema" in frame and "fields" in frame["schema"]:
        for field in frame["schema"]["fields"]:
            if field.get("type") == "number" and "labels" in field:
                labels = field["labels"]
                if "pod" in labels:
                    pod_name = labels["pod"]
                    if "resource-allocator" in pod_name:
                        parts = pod_name.split("-")
                        if len(parts) >= 3:
                            return f"{parts[-2][-4:]}-{parts[-1]}"
                        else:
                            return pod_name
                    else:
                        return pod_name
                elif "__name__" in labels:
                    return labels["__name__"]
                else:
                    # Use all meaningful labels to create name
                    label_parts = []
                    for k, v in labels.items():
                        if k not in ["__name__", "job", "instance"]:
                            label_parts.append(f"{k}={v}")
                    if label_parts:
                        return ", ".join(label_parts)
                break
    return ref_id


@app.route("/render", methods=["POST"])
def render_chart():
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

        chartkick_type = CHART_TYPE_MAP.get(panel_type, "LineChart")
        original_panel_type = (
            panel_type  # Preserve original panel type for gauge detection
        )

        processed_targets = apply_template_variables(targets, variables)

        query_url = f"{host}/api/ds/query"

        # Use targets directly with variable substitution applied
        query_payload = {
            "queries": processed_targets,
            "from": str(fr),
            "to": str(to),
        }

        query_res = requests.post(
            query_url, json=query_payload, headers={"Authorization": f"Bearer {token}"}
        )
        response_data = query_res.json()
        query_res.raise_for_status()
        # Handle different response structures - support multiple series
        data_series = {}
        print(response_data)
        if "results" in response_data:
            # Process all series in the response
            for ref_id, result in response_data["results"].items():
                if "frames" in result and result["frames"]:
                    # Each frame can be a separate series (especially with labels)
                    for frame in result["frames"]:
                        if "data" in frame and "values" in frame["data"]:
                            values = frame["data"]["values"]

                            # Check if this is a single value stat (like COUNT(*))
                            if len(values) == 1 and len(values[0]) == 1:
                                # Single stat value - but preserve original type for gauge detection
                                if original_panel_type != "gauge":
                                    chartkick_type = "stat"
                                stat_value = values[0][0]
                                data_series["stat_value"] = stat_value
                            elif len(values) >= 2:
                                x_vals = values[0]  # Time/category column

                                # Get field names from schema for series names
                                field_names = []
                                if "schema" in frame and "fields" in frame["schema"]:
                                    field_names = [
                                        field.get("name", f"Series {i}")
                                        for i, field in enumerate(
                                            frame["schema"]["fields"]
                                        )
                                    ]

                                # Check if this is multi-column data (more than 2 columns)
                                if len(values) > 2 and len(field_names) > 2:
                                    # Multi-column time series - each column after first is a series
                                    for i in range(1, len(values)):
                                        y_vals = values[i]
                                        series_name = (
                                            field_names[i]
                                            if i < len(field_names)
                                            else f"Series {i}"
                                        )

                                        # Clean up series names
                                        series_name = (
                                            series_name.replace("_true", "")
                                            .replace("_", " ")
                                            .title()
                                        )

                                        frame_data = process_series_data(
                                            x_vals, y_vals, processed_targets, ref_id
                                        )
                                        if frame_data:
                                            data_series[series_name] = frame_data
                                else:
                                    # Single series - process normally
                                    y_vals = values[1]
                                    series_name = get_series_name_from_labels(
                                        frame, ref_id
                                    )

                                    # If no labels found, try to get name from target legendFormat
                                    if series_name == ref_id:
                                        for target in processed_targets:
                                            if target.get("refId") == ref_id:
                                                legend_format = target.get(
                                                    "legendFormat", ""
                                                )
                                                if (
                                                    legend_format
                                                    and "{{" not in legend_format
                                                ):
                                                    series_name = legend_format
                                                elif target.get("expr"):
                                                    expr = target.get("expr", "")[:40]
                                                    series_name = (
                                                        f"{expr}..."
                                                        if len(expr) == 40
                                                        else expr
                                                    )
                                                break

                                    frame_data = process_series_data(
                                        x_vals, y_vals, processed_targets, ref_id
                                    )
                                    if frame_data:
                                        data_series[series_name] = frame_data
                elif "series" in result:
                    # Time series format - each series is separate
                    for series in result["series"]:
                        series_data = []
                        series_name = ref_id

                        # Try to get series name from tags/labels
                        if "tags" in series:
                            tags = series["tags"]
                            if "pod" in tags:
                                pod_name = tags["pod"]
                                if "resource-allocator" in pod_name:
                                    parts = pod_name.split("-")
                                    if len(parts) >= 3:
                                        series_name = f"{parts[-2][-4:]}-{parts[-1]}"
                                    else:
                                        series_name = pod_name
                                else:
                                    series_name = pod_name

                        for datapoint in series.get("datapoints", []):
                            if len(datapoint) >= 2 and datapoint[0] is not None:
                                value, timestamp = datapoint[0], datapoint[1]
                                series_data.append(
                                    [
                                        datetime.datetime.fromtimestamp(
                                            timestamp / 1000
                                        ).isoformat(),
                                        value,
                                    ]
                                )

                        # Add this series if it has data
                        if series_data:
                            data_series[series_name] = series_data

        # If no series data found, create empty single series
        if not data_series:
            data_series = {"No Data": []}

        html = generate_html(
            chartkick_type,
            data_series,
            title=panel.get("title", "Grafana Panel"),
            original_panel_type=original_panel_type,
        )
        return html

    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


if __name__ == "__main__":
    app.run(debug=True)

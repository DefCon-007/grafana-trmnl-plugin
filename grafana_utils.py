import datetime
from urllib.parse import parse_qs, urlparse

import requests

# Chart type mapping for proper chart type detection
CHART_TYPE_MAP = {
    "timeseries": "LineChart",
    "graph": "LineChart",
    "stat": "ColumnChart",
    "gauge": "ColumnChart",
    "bar gauge": "BarChart",
    "table": "ColumnChart",
    "piechart": "PieChart",
}


def parse_panel_url(panel_url):
    """Parse Grafana panel URL to extract host, UID, panel ID, and variables"""
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
            variables[var_name] = values  # Keep as list

    return host, uid, panel_id, variables


def get_dashboard_metadata(host, uid, token):
    """Fetch dashboard metadata from Grafana API"""
    dash_res = requests.get(
        f"{host}/api/dashboards/uid/{uid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    dash_res.raise_for_status()
    return dash_res.json()


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


def query_grafana_panel(host, token, processed_targets, fr, to, original_panel_type):
    """Query Grafana API and process the response into structured data"""
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

    # Process the response data
    data_series = {}
    # Use original panel type to determine correct chart type instead of defaulting to LineChart
    chartkick_type = CHART_TYPE_MAP.get(original_panel_type, "LineChart")

    if "results" in response_data:
        # Process all series in the response
        for ref_id, result in response_data["results"].items():
            if "frames" in result and result["frames"]:
                # Each frame can be a separate series
                for frame in result["frames"]:
                    if "data" in frame and "values" in frame["data"]:
                        values = frame["data"]["values"]

                        # Check if this is a single value stat (like COUNT(*))
                        if len(values) == 1 and len(values[0]) == 1:
                            # Single stat value - preserve original type for gauge detection
                            if original_panel_type == "gauge":
                                chartkick_type = (
                                    "gauge"  # Keep as gauge for special handling
                                )
                            else:
                                chartkick_type = (
                                    "stat"  # Mark as stat for special handling
                                )
                            stat_value = values[0][0]
                            data_series["stat_value"] = stat_value
                        elif len(values) >= 2:
                            x_vals = values[0]  # Time/category column

                            # Get field names from schema for series names
                            field_names = []
                            if "schema" in frame and "fields" in frame["schema"]:
                                field_names = [
                                    field.get("name", f"Series {i}")
                                    for i, field in enumerate(frame["schema"]["fields"])
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
                                series_name = get_series_name_from_labels(frame, ref_id)

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

    return response_data, data_series, chartkick_type

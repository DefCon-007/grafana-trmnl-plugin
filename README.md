# Grafana Panel Renderer

A Flask-based server that renders Grafana dashboard panels as HTML visualizations optimized for TRMNL displays.

It can be accessed from https://grafana-trmnl.defcon007.com

It is currently deployed using Google Cloud App Engine. 

## Architecture

The application has been refactored into a modular structure:

### Core Files

- **`app.py`** - Main Flask application with route definitions
- **`grafana_utils.py`** - Grafana API operations and data processing
- **`html_utils.py`** - HTML chart generation and rendering
- **`requirements.txt`** - Python dependencies

### Endpoints

#### POST /render
Returns an HTML page with the panel visualization.

**Request:**
```json
{
  "grafana_token": "your_grafana_api_token",
  "panel_url": "https://grafana.example.com/d/dashboard-uid/name?viewPanel=123",
  "from": "now-6h",
  "to": "now"
}
```

**Response:** HTML page with embedded chart

#### POST /query
Returns raw query results and processed data as JSON.

**Request:** Same as `/render`

**Response:**
```json
{
  "panel_type": "timeseries",
  "panel_title": "Panel Title",
  "detected_chart_type": "LineChart",
  "data_series": {...},
  "raw_response": {...},
  "processed_targets": [...],
  "variables": {...}
}
```

## Features

- **Multi-series support**: Handles multiple data series with proper legends
- **Chart types**: Time series, stat panels, gauges, pie charts
- **Template variables**: Full support for Grafana template variable substitution
- **TRMNL optimized**: Black/white styling, patterns, no animations
- **Modular design**: Separated concerns for better maintainability
- **Highcharts-native**: All visualizations use Highcharts built-in functionality, no custom CSS

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the server:
   ```bash
   python main.py
   ```

3. Send POST requests to `http://localhost:5000/render` or `http://localhost:5000/query`

## Module Details

### grafana_utils.py
- `parse_panel_url()` - Extract host, UID, panel ID, and variables from Grafana URLs
- `get_dashboard_metadata()` - Fetch dashboard configuration from Grafana API
- `apply_template_variables()` - Replace template variables in queries
- `query_grafana_panel()` - Execute queries and process responses
- `process_series_data()` - Convert raw data to chart format
- `get_series_name_from_labels()` - Extract meaningful series names


### html_utils.py
- `generate_html()` - Create HTML with appropriate chart visualization
- `CHART_TYPE_MAP` - Panel type to chart type mapping
- Supports: Highcharts for all chart types including multi-series, gauges, and stat panels
- No custom CSS styling - everything uses Highcharts built-in functionality

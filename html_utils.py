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
    chart_type,
    data_series,
    title="Grafana Panel",
    original_panel_type=None,
    full_html=False,
):
    """Generate HTML with appropriate chart visualization based on data type"""
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
        # Multi-series configuration with TRMNL background classes
        series_config = []
        colors = ["#000000", "#666666", "#999999", "#CCCCCC"]
        # Use TRMNL background patterns instead of PNG URLs
        bg_patterns = [
            None,  # First series uses solid color
            "bg--gray-5",
            "bg--gray-3",
            "bg--gray-1",
        ]

        for i, (series_name, series_data) in enumerate(data_series.items()):
            color_config = colors[i % len(colors)]
            bg_pattern = bg_patterns[i % len(bg_patterns)]

            # For series with patterns, we'll handle this in the chart configuration
            series_config.append(
                {
                    "name": series_name,
                    "data": series_data,
                    "lineWidth": 4 if i == 0 else 3,
                    "color": color_config,
                    "zIndex": len(data_series) - i,
                    "bgPattern": bg_pattern,  # Store pattern class for later use
                }
            )

        chart_data = series_config
    else:
        # Single series - use original format
        if isinstance(data_series, dict):
            chart_data = list(data_series.values())[0]
        else:
            chart_data = data_series

    base_html = f"""
      <script src="https://code.highcharts.com/highcharts.js"></script>
      <script src="https://code.highcharts.com/highcharts-more.js"></script>
      <script src="https://code.highcharts.com/modules/pattern-fill.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/chartkick@5.0.1/dist/chartkick.min.js"></script>

      <div class="view view--full">
        <div class="layout layout--col gap--space-between">
          <div id="chart" class="w--full h--64"></div>
        </div>
        <div class="title_bar">
          <img class="image" src="/images/plugins/trmnl--render.svg" />
          <span class="title">{title}</span>
        </div>
      </div>

      <script>
        var chartData = {chart_data};

        {
        '''
        // Stat panel configuration using Highcharts
        Highcharts.chart("chart", {
          chart: {
            type: "line",
            animation: false,
            backgroundColor: "transparent"
          },
          title: {
            text: null
          },
          xAxis: {
            visible: false
          },
          yAxis: {
            visible: false
          },
          legend: {
            enabled: false
          },
          plotOptions: {
            series: {
              animation: false,
              enableMouseTracking: false,
              states: {
                hover: {
                  enabled: false
                }
              }
            }
          },
          series: [{
            data: [0],
            showInLegend: false,
            marker: {
              enabled: false
            },
            lineWidth: 0,
            dataLabels: {
              enabled: true,
              formatter: function() {
                return chartData.formatted;
              },
              style: {
                fontSize: "120px",
                fontWeight: "bold",
                color: "#000000",
                textOutline: "none"
              },
              x: 0,
              y: 0,
              verticalAlign: "middle",
              align: "center"
            }
          }],
          credits: {
            enabled: false
          }
        });
        '''
        if is_stat and not is_gauge
        else '''
        // Gauge chart configuration
        Highcharts.chart("chart", {
          chart: {
            type: "gauge",
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
              color: "#666666",  // Use gray color instead of pattern for gauge fill
              innerRadius: "82%",
              borderRadius: "50%"
            }, {
              from: chartData.value + 1,
              to: 100,
              color: "#CCCCCC",  // Light gray for remaining portion
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
              style: {{ fontSize: "16px", color: "#000000" }}
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
              style: {{ fontSize: "16px", color: "#000000" }}
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
        var createChart = function() {{
          new Chartkick.{chart_type}("chart", chartData, {{
            adapter: "highcharts",
            curve: true,
            colors: ["#000000"],
            points: false,
            library: {{
              chart: {{
                animation: false
              }},
              plotOptions: {{
                series: {{
                  animation: false,
                  lineWidth: 4
                }}
              }},
              yAxis: {{
                labels: {{
                  style: {{
                    fontSize: "16px",
                    color: "#000000"
                  }}
                }},
                gridLineDashStyle: "shortdot",
                gridLineWidth: 1,
                gridLineColor: "#000000",
                tickAmount: 5
              }},
              xAxis: {{
                type: "datetime",
                labels: {{
                  style: {{
                    fontSize: "16px",
                    color: "#000000"
                  }}
                }},
                lineWidth: 0,
                gridLineDashStyle: "dot",
                tickWidth: 1,
                tickLength: 0,
                gridLineWidth: 1,
                gridLineColor: "#000000",
                tickPixelInterval: 120
              }}
            }}
          }});
        }};

        // Ensure chart loads properly
        if ("Chartkick" in window) {{
          createChart();
        }} else {{
          window.addEventListener("chartkick:load", createChart, true);
        }}
        '''
    }
      </script>
    """

    if full_html:
        return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>{title}</title>
      <link rel="stylesheet" href="https://usetrmnl.com/css/latest/plugins.css">
      <script src="https://usetrmnl.com/js/latest/plugins.js"></script>
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;350;375;400;450;600;700&display=swap" rel="stylesheet">
    </head>
    <body class="environment trmnl">
    <div class="screen">
      {base_html}
      </div>
    </body>
    </html>
    """
    else:
        return base_html

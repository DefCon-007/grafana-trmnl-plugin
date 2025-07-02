# Testing Guide for Grafana TRMNL Plugin Server

This directory contains comprehensive unit tests for the Grafana TRMNL Plugin Server's render endpoint.

## Test Structure

### Test Files
- `test_main.py` - Main test suite for the render endpoint
- `test_data/` - Directory containing JSON test data files for different panel types
- `requirements-test.txt` - Test dependencies

### Test Data Files
The tests use mock data stored in JSON files that simulate the return value of `_get_panel_data()`:

- `stat_panel_data.json` - Single stat value panel
- `gauge_panel_data.json` - Gauge panel with percentage value
- `timeseries_panel_data.json` - Single series time-series data
- `multi_series_timeseries_data.json` - Multi-series time-series data
- `bar_gauge_panel_data.json` - Bar chart data
- `piechart_panel_data.json` - Pie chart data
- `table_panel_data.json` - Table/column chart data

## Running Tests

### Prerequisites
Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Run Tests

#### Option 1: Using pytest directly
```bash
python -m pytest test_main.py -v
```

#### Option 2: Using the test runner script
```bash
python run_tests.py
```

#### Option 3: With coverage reporting
```bash
python -m pytest test_main.py -v --cov=main --cov=html_utils --cov=grafana_utils --cov-report=term-missing
```

## Test Coverage

The test suite covers:

### Panel Types Tested
- ✅ Stat panels (single values)
- ✅ Gauge panels (percentage displays)
- ✅ Timeseries panels (line charts)
- ✅ Multi-series timeseries
- ✅ Bar gauge panels
- ✅ Pie chart panels
- ✅ Table panels

### Response Formats Tested
- ✅ JSON response (`full_html=false`)
- ✅ Full HTML response (`full_html=true`)

### Error Conditions Tested
- ✅ Missing request data
- ✅ Invalid JSON input

### Key Test Features

1. **Mocked Dependencies**: Uses `@patch` to mock `_get_panel_data()` function
2. **Real Data Simulation**: JSON files contain realistic panel data structures
3. **HTML Validation**: Tests verify that correct chart types and elements are generated
4. **Error Handling**: Tests cover error scenarios and edge cases

## Test Data Structure

Each JSON test file follows this structure:
```json
{
    "panel_type": "stat|gauge|timeseries|bar gauge|piechart|table",
    "panel_title": "Panel Title",
    "data_series": {
        // Panel-specific data structure
    },
    "raw_response": {
        // Simulated Grafana API response
    },
    "processed_targets": [
        // Query targets
    ],
    "variables": {}
}
```

## Adding New Tests

To add tests for new panel types:

1. Create a new JSON file in `test_data/` with the appropriate data structure
2. Add a new test method in `TestRenderEndpoint` class
3. Follow the pattern of existing tests:
   - Mock `_get_panel_data`
   - Load test data from JSON
   - Make request to `/render` endpoint
   - Assert response structure and content

## Example Test Method

```python
@patch('main._get_panel_data')
def test_render_new_panel_type(self, mock_get_panel_data):
    """Test rendering a new panel type"""
    test_data = self.load_test_data('new_panel_data.json')
    mock_get_panel_data.return_value = test_data

    response = self.client.post('/render', json={
        'grafana_token': 'test_token',
        'panel_url': 'test_url',
        'full_html': False
    })

    self.assertEqual(response.status_code, 200)
    response_data = response.get_json()
    self.assertIn('html', response_data)

    # Panel-specific assertions
    html_content = response_data['html']
    self.assertIn('expected_chart_type', html_content)
```
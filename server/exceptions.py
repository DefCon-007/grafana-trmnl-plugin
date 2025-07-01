class GrafanaException(Exception):
    """Base exception for Grafana-related errors"""

    def __init__(self, message, status_code=500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InvalidPanelUrlException(GrafanaException):
    """Raised when the panel URL is invalid or malformed"""

    def __init__(self, message="Invalid panel_url"):
        super().__init__(message, status_code=400)


class PanelNotFoundException(GrafanaException):
    """Raised when the specified panel is not found in the dashboard"""

    def __init__(self, message="Panel not found"):
        super().__init__(message, status_code=404)


class NoTargetsException(GrafanaException):
    """Raised when no targets are found in the panel"""

    def __init__(self, message="No targets found in panel"):
        super().__init__(message, status_code=400)


class GrafanaQueryException(GrafanaException):
    """Raised when there's an error querying Grafana"""

    def __init__(self, message="Error querying Grafana"):
        super().__init__(message, status_code=500)


class DashboardMetadataException(GrafanaException):
    """Raised when there's an error fetching dashboard metadata"""

    def __init__(self, message="Error fetching dashboard metadata"):
        super().__init__(message, status_code=500)

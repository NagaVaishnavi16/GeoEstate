"""Response contract for operational health checks."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Expose application and database availability without sensitive detail."""

    status: str
    database: bool
    postgis: bool
    version: str

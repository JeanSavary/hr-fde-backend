from fastapi import APIRouter, Security
from app.models.analytics import AnalyticsResponse
from app.services.analytics_service import get_analytics
from app.routes._auth import verify_api_key

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get(
    "",
    response_model=AnalyticsResponse,
    dependencies=[Security(verify_api_key)],
)
async def analytics():
    """Aggregated analytics for the dashboard."""
    return get_analytics()

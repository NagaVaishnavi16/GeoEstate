"""Descriptive analytics orchestration without HTTP or database implementation details."""

from decimal import Decimal, ROUND_HALF_UP

from app.repositories.market_insights import MarketInsightsRepository
from app.schemas.insights import (
    AmenityPriceMetricResponse,
    InsightStatementResponse,
    LocalityPriceMetricResponse,
    MarketInsightsResponse,
    PriceDistributionResponse,
    PriceRateOutlierResponse,
    ScorePriceMetricResponse,
)


class MarketInsightsService:
    """Build a small, truthful analytics payload for the frontend."""

    def __init__(self, repository: MarketInsightsRepository) -> None:
        self._repository = repository

    async def get_insights(self) -> MarketInsightsResponse:
        """Compose database aggregates without inferring causation or returns."""
        distribution, localities, scores, outliers, amenities = await self._load_all()
        response = MarketInsightsResponse(
            price_per_sqft_distribution=PriceDistributionResponse(
                listing_count=distribution[0], minimum=distribution[1], first_quartile=distribution[2],
                median=distribution[3], third_quartile=distribution[4], maximum=distribution[5],
            ),
            locality_price_metrics=[
                LocalityPriceMetricResponse(
                    locality=item.locality, total_listings=item.total_listings, average_price_lakh=item.average_price_lakh,
                    median_price_lakh=item.median_price_lakh, average_price_per_sqft=item.average_price_per_sqft,
                ) for item in localities
            ],
            score_price_metrics=[
                ScorePriceMetricResponse(score=label, scored_listings=count, average_score=average_score,
                    average_price_lakh=average_price, average_price_per_sqft=average_rate)
                for label, count, average_score, average_price, average_rate in scores
            ],
            rate_outliers=[
                PriceRateOutlierResponse(property_id=property_record.property_id, locality=property_record.location,
                    price_lakh=property_record.price_lakh, rate_per_sqft=property_record.rate_per_sqft,
                    locality_average_price_per_sqft=locality_rate, rate_to_locality_average=ratio)
                for property_record, locality_rate, ratio in outliers
            ],
            amenity_price_metrics=[
                AmenityPriceMetricResponse(amenity=label, listings_with_verified_distance=count,
                    average_price_lakh=average_price, average_price_per_sqft=average_rate, average_distance_m=average_distance)
                for label, count, average_price, average_rate, average_distance in amenities
            ],
            statements=[],
        )
        return response.model_copy(update={"statements": self._statements(response)})

    async def _load_all(self):
        """Keep independent SQL aggregations readable and service-level composition simple."""
        return (
            await self._repository.price_distribution(),
            await self._repository.locality_price_metrics(limit=5),
            await self._repository.score_price_metrics(),
            await self._repository.rate_outliers(limit=4),
            await self._repository.amenity_price_metrics(),
        )

    @staticmethod
    def _statements(response: MarketInsightsResponse) -> list[InsightStatementResponse]:
        """Generate no more than four strictly descriptive, supported observations."""
        statements: list[InsightStatementResponse] = []
        rates = response.locality_price_metrics
        if rates:
            leader = rates[0]
            statements.append(InsightStatementResponse(text=(
                f"Among localities with at least three listings, {leader.locality} has the highest current average rate "
                f"in this view at ₹{leader.average_price_per_sqft:,.0f} per sq ft."
            )))
        distribution = response.price_per_sqft_distribution
        if distribution.median is not None:
            statements.append(InsightStatementResponse(text=(
                f"The current median recorded rate is ₹{distribution.median:,.0f} per sq ft across {distribution.listing_count:,} listings with rate data."
            )))
        metro = next((item for item in response.amenity_price_metrics if item.amenity == "Metro" and item.listings_with_verified_distance), None)
        if metro and metro.average_distance_m is not None:
            statements.append(InsightStatementResponse(text=(
                f"{metro.listings_with_verified_distance:,} listings currently have a verified metro distance, averaging {metro.average_distance_m:,.0f} m."
            )))
        connectivity = next((item for item in response.score_price_metrics if item.score == "Connectivity" and item.scored_listings), None)
        if connectivity and connectivity.average_score is not None:
            statements.append(InsightStatementResponse(text=(
                f"Connectivity scores are available for {connectivity.scored_listings:,} listings; their current average is {connectivity.average_score:.0f}/100."
            )))
        return statements[:4]

import { ScorePill } from "./ScorePill";

const amenityIcons = { metro: "M", hospital: "+", school: "S", park: "✦" };

function formatPrice(priceLakh) {
  const numeric = Number(priceLakh);
  return numeric >= 100 ? `₹${(numeric / 100).toFixed(numeric % 100 ? 1 : 0)} Cr` : `₹${numeric.toFixed(numeric % 1 ? 1 : 0)} L`;
}

function distance(value) {
  if (value === null || value === undefined) return null;
  return value < 1000 ? `${value} m` : `${(value / 1000).toFixed(1)} km`;
}

function Amenity({ kind, name, distanceM, parkCount }) {
  if (!name && distanceM === null) return null;
  return (
    <li>
      <span className={`amenity-icon ${kind}`}>{amenityIcons[kind]}</span>
      <span>{name ?? "Nearby location"}{distance(distanceM) ? ` · ${distance(distanceM)}` : ""}{kind === "park" && parkCount !== null && parkCount !== undefined ? ` · ${parkCount} nearby` : ""}</span>
    </li>
  );
}

export function PropertyCard({ property, isSelected, onSelect }) {
  return (
    <article className={`property-card ${isSelected ? "selected" : ""}`} onClick={() => onSelect(property.property_id)}>
      <div className="card-topline">
        <span className="status-tag">{property.building_status || "Listing"}</span>
        <span className="rate">{property.rate_per_sqft ? `₹${Number(property.rate_per_sqft).toLocaleString("en-IN")}/sq ft` : "Rate unavailable"}</span>
      </div>
      <h3>{property.title || `${property.bedrooms ?? ""} BHK Home`}</h3>
      <p className="location">⌖ {property.location}</p>
      <div className="property-facts">
        <strong>{formatPrice(property.price_lakh)}</strong>
        <span>{property.area_sqft?.toLocaleString("en-IN")} sq ft</span>
        {property.bedrooms !== null && property.bedrooms !== undefined && <span>{property.bedrooms} BHK</span>}
      </div>
      <div className="score-grid">
        <ScorePill scoreKey="investment_score" value={property.investment_score} />
        <ScorePill scoreKey="connectivity_score" value={property.connectivity_score} />
        <ScorePill scoreKey="green_score" value={property.green_score} />
        <ScorePill scoreKey="liveability_score" value={property.liveability_score} />
      </div>
      <ul className="amenity-list" aria-label="Nearby places">
        <Amenity kind="metro" name={property.nearest_metro} distanceM={property.nearest_metro_distance_m} />
        <Amenity kind="hospital" name={property.nearest_hospital} distanceM={property.nearest_hospital_distance_m} />
        <Amenity kind="school" name={property.nearest_school} distanceM={property.nearest_school_distance_m} />
        <Amenity kind="park" name={property.nearest_park} distanceM={property.nearest_park_distance_m} parkCount={property.nearby_park_count} />
      </ul>
    </article>
  );
}

function formatPrice(value) {
  const numeric = Number(value);
  return numeric >= 100 ? `₹${(numeric / 100).toFixed(1)} Cr` : `₹${numeric.toFixed(numeric % 1 ? 1 : 0)} L`;
}

function formatDistance(value) {
  return value < 1000 ? `${value} m` : `${(value / 1000).toFixed(1)} km`;
}

function ScatterPlot({ properties, xKey, yKey, xLabel, yLabel, selectedId, onSelect }) {
  const points = properties.filter((property) => property[xKey] !== null && property[xKey] !== undefined && Number.isFinite(Number(property[xKey])) && property[yKey] !== null && property[yKey] !== undefined && Number.isFinite(Number(property[yKey])));
  if (points.length < 2) return <div className="chart-empty">Not enough matching listings with both values to draw this comparison.</div>;
  const xValues = points.map((property) => Number(property[xKey]));
  const yValues = points.map((property) => Number(property[yKey]));
  const xMin = Math.min(...xValues); const xMax = Math.max(...xValues);
  const yMin = Math.min(...yValues); const yMax = Math.max(...yValues);
  const scale = (value, min, max, start, size) => max === min ? start + size / 2 : start + ((value - min) / (max - min)) * size;
  return <figure className="scatter-card"><figcaption><strong>{yLabel} vs {xLabel}</strong><span>Each point is one returned listing</span></figcaption><svg viewBox="0 0 360 228" role="img" aria-label={`${yLabel} compared with ${xLabel} for the search results`}><line x1="42" y1="18" x2="42" y2="190" className="chart-axis" /><line x1="42" y1="190" x2="342" y2="190" className="chart-axis" /><text x="42" y="211" className="chart-label">{xMin.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</text><text x="290" y="211" className="chart-label">{xMax.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</text><text x="4" y="184" className="chart-label">{yMin.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</text><text x="4" y="27" className="chart-label">{yMax.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</text><text x="192" y="226" className="chart-axis-title">{xLabel}</text><text x="13" y="106" className="chart-axis-title" transform="rotate(-90 13 106)">{yLabel}</text>{points.map((property) => { const x = scale(Number(property[xKey]), xMin, xMax, 42, 300); const y = 190 - scale(Number(property[yKey]), yMin, yMax, 0, 172); const selected = property.property_id === selectedId; return <circle key={property.property_id} cx={x} cy={y} r={selected ? 7 : 5} className={selected ? "chart-point selected-point" : "chart-point"} onClick={() => onSelect(property.property_id)}><title>{`${property.title}, ${formatPrice(property.price_lakh)}`}</title></circle>; })}</svg><p className="chart-legend"><i /> Orange point: selected listing</p></figure>;
}

function buildInsights(properties) {
  const insights = [];
  const priced = properties.filter((property) => Number.isFinite(Number(property.price_lakh)));
  if (priced.length) { const prices = priced.map((property) => Number(property.price_lakh)); insights.push(`The ${formatPrice(Math.max(...prices) - Math.min(...prices))} price spread gives room to compare trade-offs within this same shortlist, rather than across the broader market.`); }
  const rated = properties.filter((property) => property.rate_per_sqft !== null && property.rate_per_sqft !== undefined);
  if (rated.length) { const lowest = rated.reduce((current, property) => Number(property.rate_per_sqft) < Number(current.rate_per_sqft) ? property : current); const highest = rated.reduce((current, property) => Number(property.rate_per_sqft) > Number(current.rate_per_sqft) ? property : current); insights.push(`${lowest.location} is the lower recorded rate option in this result set, while ${highest.location} is the higher one; compare area and status alongside rate.`); }
  const metro = properties.filter((property) => property.nearest_metro_distance_m !== null && property.nearest_metro_distance_m !== undefined);
  if (metro.length) { const closest = metro.reduce((current, property) => Number(property.nearest_metro_distance_m) < Number(current.nearest_metro_distance_m) ? property : current); insights.push(`${closest.nearest_metro ?? "The closest verified metro"} is closest to one returned home at ${formatDistance(Number(closest.nearest_metro_distance_m))}; use the nearby-place details to weigh commute convenience.`); }
  const scores = ["investment_score", "connectivity_score", "green_score", "liveability_score"];
  const scored = properties.flatMap((property) => scores.filter((key) => property[key] !== null && property[key] !== undefined).map((key) => ({ property, key, value: Number(property[key]) })));
  if (scored.length) { const strongest = scored.reduce((current, item) => item.value > current.value ? item : current); const label = strongest.key.replace("_score", "").replace(/^./, (letter) => letter.toUpperCase()); insights.push(`${label} is the strongest available indicator for a ${strongest.property.title} in ${strongest.property.location}; it is a comparative heuristic, not a prediction.`); }
  return insights.slice(0, 4);
}

export function SearchInsights({ properties, selectedId, onSelect }) {
  const insights = buildInsights(properties);
  return <section className="search-insights" aria-labelledby="search-insights-heading"><header><div><p className="eyebrow">SEARCH INSIGHTS</p><h2 id="search-insights-heading">Where these homes fall on price and size.</h2></div><p>Calculated only from this shortlist. Descriptive, not predictive.</p></header><div className="search-insight-statements">{insights.map((insight) => <p key={insight}>✦ {insight}</p>)}</div><div className="scatter-grid"><ScatterPlot properties={properties} xKey="area_sqft" yKey="price_lakh" xLabel="Area (sq ft)" yLabel="Price (₹ lakh)" selectedId={selectedId} onSelect={onSelect} /><ScatterPlot properties={properties} xKey="price_lakh" yKey="investment_score" xLabel="Price (₹ lakh)" yLabel="Investment score" selectedId={selectedId} onSelect={onSelect} /></div></section>;
}

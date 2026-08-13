function rupees(value) {
  return value === null || value === undefined ? "—" : `₹${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function InsightsPanel({ insights, error }) {
  if (error || !insights) return null;
  const distribution = insights.price_per_sqft_distribution;
  return (
    <section className="insights-panel market-context" aria-labelledby="market-context-heading">
      <details>
        <summary><span><p className="eyebrow">MARKET CONTEXT</p><h2 id="market-context-heading">Citywide context</h2></span><small>Optional whole-dataset view</small></summary>
        <p className="insights-disclaimer">Current listing data only. These patterns are descriptive and do not imply returns or causation.</p>
        <div className="insights-grid">
          <article className="insight-card distribution-card"><h3>Price / sq ft distribution</h3><p className="card-caption">{distribution.listing_count.toLocaleString("en-IN")} listings with recorded rates</p><div className="distribution-scale"><span>{rupees(distribution.minimum)}</span><span>{rupees(distribution.first_quartile)}</span><span>{rupees(distribution.median)}</span><span>{rupees(distribution.third_quartile)}</span><span>{rupees(distribution.maximum)}</span></div><div className="distribution-line" /><div className="distribution-labels"><span>Min</span><span>Q1</span><strong>Median</strong><span>Q3</span><span>Max</span></div></article>
          <article className="insight-card"><h3>Locality price / sq ft</h3><p className="card-caption">Highest current averages; min. 3 listings</p><div className="mini-bars">{insights.locality_price_metrics.map((item, index) => <div key={item.locality}><span>{item.locality}</span><strong>{rupees(item.average_price_per_sqft)}</strong><i style={{ width: `${Math.max(18, 100 - index * 15)}%` }} /></div>)}</div></article>
          <article className="insight-card"><h3>Score & price coverage</h3><p className="card-caption">Average price for listings with each available score</p><div className="metric-table">{insights.score_price_metrics.map((item) => <div key={item.score}><span>{item.score}</span><b>{item.average_score === null ? "—" : `${Number(item.average_score).toFixed(0)}/100`}</b><em>{rupees(item.average_price_lakh)} L</em></div>)}</div></article>
        </div>
      </details>
    </section>
  );
}

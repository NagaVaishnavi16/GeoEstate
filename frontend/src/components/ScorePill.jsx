const scoreMetadata = {
  investment_score: { label: "Investment", helper: "Value indicator — not a return prediction", tone: "gold" },
  connectivity_score: { label: "Connectivity", helper: "Nearby metro, hospital, and school access", tone: "blue" },
  green_score: { label: "Green", helper: "Park proximity and nearby park count", tone: "green" },
  liveability_score: { label: "Liveability", helper: "Connectivity, green access, and amenity availability", tone: "violet" },
};

export function ScorePill({ scoreKey, value }) {
  const meta = scoreMetadata[scoreKey];
  if (value === null || value === undefined) {
    return <span className="score-pill score-muted" title={`${meta.label}: insufficient verified data`}>{meta.label} —</span>;
  }
  return <span className={`score-pill ${meta.tone}`} title={meta.helper}>{meta.label} {Number(value).toFixed(0)}</span>;
}

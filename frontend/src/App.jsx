import { useEffect, useState } from "react";
import { getInsights } from "./api/insights";
import { InsightsPanel } from "./components/InsightsPanel";
import { SearchInsights } from "./components/SearchInsights";
import { naturalSearch, ApiError } from "./api/propertySearch";
import { PropertyCard } from "./components/PropertyCard";
import { PropertyMap } from "./components/PropertyMap";
import { SearchBar } from "./components/SearchBar";

const exampleQuery = "Show me 3 BHK apartments under 1 crore in Gachibowli near metro";

function Filters({ filters }) {
  if (!filters) return null;
  const values = [filters.locality, filters.bhk && `${filters.bhk} BHK`, filters.price_max && `Under ₹${Number(filters.price_max).toLocaleString("en-IN")}`, filters.nearby?.metro && "Near metro"].filter(Boolean);
  return values.length ? <div className="filter-row">{values.map((value) => <span key={value}>{value}</span>)}</div> : null;
}

export default function App() {
  const [query, setQuery] = useState(exampleQuery);
  const [searchState, setSearchState] = useState({ status: "idle", results: [], total: 0, filters: null, message: "" });
  const [selectedId, setSelectedId] = useState(null);
  const [insights, setInsights] = useState(null);
  const [insightsError, setInsightsError] = useState(false);

  useEffect(() => {
    getInsights().then(setInsights).catch(() => setInsightsError(true));
  }, []);

  async function submit(event) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    setSearchState({ status: "loading", results: [], total: 0, filters: null, message: "" });
    try {
      const response = await naturalSearch(trimmed);
      if (response.status === "completed") {
        setSearchState({ status: "completed", results: response.results, total: response.total_results, filters: response.extracted_filters, message: "" });
        setSelectedId(response.results[0]?.property_id ?? null);
      } else if (response.status === "needs_clarification") {
        setSearchState({ status: "clarification", results: [], total: 0, filters: null, message: response.message });
      } else {
        setSearchState({ status: "invalid", results: [], total: 0, filters: null, message: response.message || "Please try a more specific property search." });
      }
    } catch (error) {
      setSearchState({ status: "error", results: [], total: 0, filters: null, message: error instanceof ApiError ? error.message : "Unable to reach the property service." });
    }
  }

  const { status, results, total, filters, message } = searchState;
  return (
    <main>
      <section className="hero">
        <nav><span className="brand-mark">G</span><strong>GeoEstate</strong><span className="nav-label">Intelligence</span><span className="beta">Property search</span></nav>
        <div className="hero-content">
          <p className="eyebrow">HYDERABAD · EXPLAINABLE SEARCH</p>
          <h1>Find a home by simply<br /><em>describing what matters.</em></h1>
          <p className="hero-copy">Search real listings using natural language, with verified nearby places and transparent intelligence indicators.</p>
          <SearchBar value={query} onChange={setQuery} onSubmit={submit} isLoading={status === "loading"} />
          <button className="example-query" onClick={() => setQuery(exampleQuery)}>Try: “{exampleQuery}”</button>
        </div>
      </section>

      <section className="results-shell">
        {status === "idle" && <div className="welcome-state"><span>✦</span><h2>Your next home starts with a sentence.</h2><p>Try the suggested query to explore enriched Hyderabad listings.</p></div>}
        {status === "loading" && <div className="notice loading"><span className="spinner" /> Understanding your preferences and finding homes…</div>}
        {(status === "error" || status === "invalid" || status === "clarification") && <div className="notice error"><strong>{status === "clarification" ? "A quick clarification" : "Search needs attention"}</strong><p>{message}</p></div>}
        {status === "completed" && <>
          <header className="results-header"><div><p className="eyebrow">SEARCH RESULTS</p><h2>{total ? `${total} homes found` : "No matching homes"}</h2></div><Filters filters={filters} /></header>
          {total === 0 ? <div className="empty-state"><h3>No exact matches yet.</h3><p>Try broadening your budget, area, or nearby-place preference.</p></div> : <div className="results-layout">
            <div className="card-list">{results.map((property) => <PropertyCard key={property.property_id} property={property} isSelected={property.property_id === selectedId} onSelect={setSelectedId} />)}</div>
            <PropertyMap properties={results} selectedId={selectedId} onSelect={setSelectedId} />
          </div>}
          {total > 0 && <SearchInsights properties={results} selectedId={selectedId} onSelect={setSelectedId} />}
        </>}
      </section>
      {status === "completed" && <InsightsPanel insights={insights} error={insightsError} />}
    </main>
  );
}

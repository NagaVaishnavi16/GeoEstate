export function SearchBar({ value, onChange, onSubmit, isLoading }) {
  return (
    <form className="search-form" onSubmit={onSubmit}>
      <label className="visually-hidden" htmlFor="natural-query">Describe the home you want</label>
      <span className="search-icon" aria-hidden="true">⌕</span>
      <input
        id="natural-query"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Describe the home you want…"
        maxLength="1000"
        disabled={isLoading}
      />
      <button type="submit" disabled={isLoading || !value.trim()}>
        {isLoading ? "Searching…" : "Search homes"}
      </button>
    </form>
  );
}

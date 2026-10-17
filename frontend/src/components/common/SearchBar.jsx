// search box used above the lists
function SearchBar({ value, onChange, placeholder = "Search..." }) {
  return (
    <div className="search-bar">
      <input type="text" placeholder={placeholder} value={value} onChange={(event) => onChange(event.target.value)} />
      <span className="search-caret">⌕</span>
    </div>
  );
}

export default SearchBar;

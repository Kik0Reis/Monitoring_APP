// dropdown filter above a list, the first option (empty value) means no filter
// options: [{ value, label }]
function FilterSelect({ value, onChange, allLabel, options }) {
  return (
    <select className="filter-select" value={value} onChange={(event) => onChange(event.target.value)}>
      <option value="">{allLabel}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

export default FilterSelect;

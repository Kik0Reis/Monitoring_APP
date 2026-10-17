import MultiSelect from "../../../components/common/MultiSelect";
import PickerInput from "../../../components/common/PickerInput";

// the filter control of one column, which control it is depends on the filter type of the column
function FilterCell({ column, value, options, onChange }) {
  const label = `Filter by ${column.header}`;

  if (column.filter === "text") {
    return (
      <input
        type="search"
        className="alerts-filter-input"
        placeholder="Filter…"
        aria-label={label}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }

  if (column.filter === "select") {
    return (
      <select
        className="alerts-filter-input"
        aria-label={label}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }

  if (column.filter === "multiselect") {
    return <MultiSelect ariaLabel={label} options={options} value={value ?? []} onChange={onChange} />;
  }

  if (column.filter === "date" || column.filter === "time") {
    const range = value ?? {};

    return (
      <div className="alerts-filter-range">
        {["from", "to"].map((side) => (
          <label key={side} className="alerts-filter-field">
            <span>{side === "from" ? "From" : "To"}</span>
            <PickerInput
              mode={column.filter}
              className="alerts-filter-input"
              ariaLabel={`${column.header} ${side}`}
              value={range[side] ?? ""}
              onChange={(next) => onChange({ ...range, [side]: next })}
            />
          </label>
        ))}
      </div>
    );
  }

  return null;
}

export default FilterCell;

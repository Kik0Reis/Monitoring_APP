/**
 * Renders one form field inside a CrudModal, based on a small config
 * object instead of hand-written markup repeated on every page.
 *
 * field: {
 *   name, label, type: 'text'|'textarea'|'select'|'checkbox'|'number'|'password',
 *   placeholder, options?: [{value, label}], maxLength?, min?, max?, hidden?,
 *   hint? (short note rendered under the field, e.g. "Restart X to apply")
 * }
 */
function FormField({ field, value, onChange, disabled }) {
  if (field.hidden) {
    return null;
  }

  const id = `field-${field.name}`;

  const hint = field.hint ? <p className="form-field-hint">{field.hint}</p> : null;

  if (field.type === "checkbox") {
    return (
      <div className="form-field checkbox-field">
        <label htmlFor={id}>
          <input
            id={id}
            name={field.name}
            type="checkbox"
            checked={Boolean(value)}
            onChange={onChange}
            disabled={disabled}
          />
          {field.label}
        </label>
        {hint}
      </div>
    );
  }

  if (field.type === "select") {
    return (
      <div className="form-field">
        <label htmlFor={id}>{field.label}</label>
        <select
          id={id}
          name={field.name}
          value={value ?? ""}
          onChange={onChange}
          disabled={disabled}
        >
          <option value="">{field.placeholder || `Select ${field.label.toLowerCase()}`}</option>
          {(field.options || []).map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {hint}
      </div>
    );
  }

  if (field.type === "textarea") {
    return (
      <div className="form-field">
        <label htmlFor={id}>{field.label}</label>
        <textarea
          id={id}
          name={field.name}
          value={value ?? ""}
          onChange={onChange}
          placeholder={field.placeholder}
          disabled={disabled}
          rows={3}
        />
        {hint}
      </div>
    );
  }

  if (field.type === "number") {
    return (
      <div className="form-field">
        <label htmlFor={id}>{field.label}</label>
        <input
          id={id}
          name={field.name}
          type="number"
          value={value ?? ""}
          onChange={onChange}
          placeholder={field.placeholder}
          min={field.min}
          max={field.max}
          disabled={disabled}
        />
        {hint}
      </div>
    );
  }

  return (
    <div className="form-field">
      <label htmlFor={id}>{field.label}</label>
      <input
        id={id}
        name={field.name}
        type={field.type === "password" ? "password" : "text"}
        value={value ?? ""}
        onChange={onChange}
        placeholder={field.placeholder}
        maxLength={field.maxLength}
        disabled={disabled}
        autoComplete={field.type === "password" ? "new-password" : undefined}
      />
      {hint}
    </div>
  );
}

export default FormField;

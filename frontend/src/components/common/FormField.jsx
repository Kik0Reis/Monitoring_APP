/**
 * Renders one form field inside a CrudModal, based on a small config
 * object instead of hand-written markup repeated on every page.
 *
 * field: {
 *   name, label, type: 'text'|'textarea'|'select'|'checkbox',
 *   placeholder, options?: [{value, label}], maxLength?, hidden?
 * }
 */
function FormField({ field, value, onChange, disabled }) {
  if (field.hidden) {
    return null;
  }

  const id = `field-${field.name}`;

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
      </div>
    );
  }

  return (
    <div className="form-field">
      <label htmlFor={id}>{field.label}</label>
      <input
        id={id}
        name={field.name}
        type="text"
        value={value ?? ""}
        onChange={onChange}
        placeholder={field.placeholder}
        maxLength={field.maxLength}
        disabled={disabled}
      />
    </div>
  );
}

export default FormField;

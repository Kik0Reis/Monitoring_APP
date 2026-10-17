// label, input and optional hint of one form field
function FieldShell({ field, id, hint, children, labelFirst = true }) {
  return (
    <div className={`form-field ${field.type === "checkbox" ? "checkbox-field" : ""}`}>
      {labelFirst && <label htmlFor={id}>{field.label}</label>}
      {children}
      {hint}
    </div>
  );
}

// one field of a form modal, drawn from a small config object
// field: { name, label, type (text, textarea, select, checkbox, number, password), placeholder,
//          options [{ value, label }], maxLength, min, max, hidden, hint }
function FormField({ field, value, onChange, disabled }) {
  if (field.hidden) {
    return null;
  }

  const id = `field-${field.name}`;
  const hint = field.hint ? <p className="form-field-hint">{field.hint}</p> : null;
  const common = { id, name: field.name, onChange, disabled };

  if (field.type === "checkbox") {
    return (
      <FieldShell field={field} id={id} hint={hint} labelFirst={false}>
        <label htmlFor={id}>
          <input {...common} type="checkbox" checked={Boolean(value)} />
          {field.label}
        </label>
      </FieldShell>
    );
  }

  if (field.type === "select") {
    return (
      <FieldShell field={field} id={id} hint={hint}>
        <select {...common} value={value ?? ""}>
          <option value="">{field.placeholder || `Select ${field.label.toLowerCase()}`}</option>
          {(field.options || []).map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </FieldShell>
    );
  }

  if (field.type === "textarea") {
    return (
      <FieldShell field={field} id={id} hint={hint}>
        <textarea {...common} value={value ?? ""} placeholder={field.placeholder} rows={3} />
      </FieldShell>
    );
  }

  if (field.type === "number") {
    return (
      <FieldShell field={field} id={id} hint={hint}>
        <input
          {...common}
          type="number"
          value={value ?? ""}
          placeholder={field.placeholder}
          min={field.min}
          max={field.max}
        />
      </FieldShell>
    );
  }

  return (
    <FieldShell field={field} id={id} hint={hint}>
      <input
        {...common}
        type={field.type === "password" ? "password" : "text"}
        value={value ?? ""}
        placeholder={field.placeholder}
        maxLength={field.maxLength}
        autoComplete={field.type === "password" ? "new-password" : undefined}
      />
    </FieldShell>
  );
}

export default FormField;

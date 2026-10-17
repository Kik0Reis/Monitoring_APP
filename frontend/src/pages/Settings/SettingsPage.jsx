import { useEffect, useState } from "react";

import FormField from "../../components/common/FormField";
import PageHeader from "../../components/common/PageHeader";
import { settingsApi } from "../../services/api";
import { EMPTY_FORM, SECTIONS, buildPayload } from "./settingsFields";

import "./Settings.css";

// the settings page, the values are saved in the backend .env file
function SettingsPage() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  // loads the current settings once, the password is never sent back by the api
  useEffect(() => {
    let ignore = false;

    // loads the current settings
    async function load() {
      try {
        const data = await settingsApi.get();
        if (!ignore) setForm({ ...EMPTY_FORM, ...data, mqtt_password: "" });
      } catch (err) {
        if (!ignore) setError(err.message || "Failed to load settings.");
      } finally {
        if (!ignore) setLoading(false);
      }
    }

    load();

    return () => {
      ignore = true;
    };
  }, []);

  // copies what was typed into the form and hides the saved message
  function handleChange(event) {
    const { name, type, value, checked } = event.target;

    setForm((previous) => ({ ...previous, [name]: type === "checkbox" ? checked : value }));
    setSaved(false);
  }

  // saves the settings and shows the values the backend stored
  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSaved(false);

    try {
      const data = await settingsApi.update(buildPayload(form));
      setForm({ ...EMPTY_FORM, ...data, mqtt_password: "" });
      setSaved(true);
    } catch (err) {
      setError(err.message || "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page settings-page">
      <PageHeader eyebrow="Configuration" title="Settings" />

      {error && <p className="error-message">{error}</p>}
      {saved && <p className="settings-saved-message">Saved.</p>}

      {loading ? (
        <p>Loading...</p>
      ) : (
        <form onSubmit={handleSubmit}>
          {SECTIONS.map((section) => (
            <section className="detail-section" key={section.title}>
              <div className="detail-section-header">
                <h3>{section.title}</h3>
              </div>

              <p className="settings-section-hint">{section.hint}</p>

              <div className="settings-grid">
                {section.fields.map((field) => (
                  <FormField
                    key={field.name}
                    field={{
                      ...field,
                      placeholder: typeof field.placeholder === "function" ? field.placeholder(form) : field.placeholder,
                    }}
                    value={form[field.name]}
                    onChange={handleChange}
                    disabled={saving}
                  />
                ))}
              </div>
            </section>
          ))}

          <div className="settings-actions">
            <button type="submit" className="primary-button" disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default SettingsPage;

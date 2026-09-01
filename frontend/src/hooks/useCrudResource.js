import { useCallback, useEffect, useState } from "react";

/**
 * Centralizes the CRUD + search + pagination logic that used to be
 * copy-pasted (with small drifting differences) across every list page
 * (Countries, Clients, Locations, Devices, Cameras).
 *
 * A resource page only needs to describe *what* it is (its API client,
 * its empty form shape, how to turn form state into an API payload) and
 * gets loading/search/pagination/create/edit/delete for free.
 *
 * @param {object} config
 * @param {object} config.api - { list, get, create, update, delete }
 * @param {object} config.emptyFormData - shape used to reset the form
 * @param {(formData: object) => object} [config.mapFormToPayload] - defaults to identity
 * @param {(formData: object) => string|null} [config.validate] - return an error message, or null
 * @param {(item: object) => object} [config.mapItemToFormData] - defaults to identity
 * @param {Record<string, string|number>} [config.filters] - fixed filters always sent to the API
 *        (e.g. { country: countryId } when this list lives inside a drilldown page)
 * @param {(item: object) => string} [config.describeItem] - used in the delete confirmation
 */
export function useCrudResource({
  api,
  emptyFormData,
  mapFormToPayload = (formData) => formData,
  validate,
  mapItemToFormData = (item) => item,
  filters = {},
  describeItem = (item) => item.name,
}) {
  const [items, setItems] = useState([]);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState(null);
  const [previous, setPrevious] = useState(null);

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [modalMode, setModalMode] = useState(null);
  const [selected, setSelected] = useState(null);
  const [formData, setFormData] = useState(emptyFormData);
  const [saving, setSaving] = useState(false);

  const filtersKey = JSON.stringify(filters);

  // Load

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const params = new URLSearchParams();

      if (search) {
        params.set("search", search);
      }

      params.set("page", String(page));

      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          params.set(key, value);
        }
      });

      const query = `?${params.toString()}`;
      const data = await api.list(query);

      if (data && Array.isArray(data.results)) {
        setItems(data.results);
        setCount(data.count ?? data.results.length);
        setNext(data.next ?? null);
        setPrevious(data.previous ?? null);
      } else {
        // Non-paginated response (plain array).
        const list = data ?? [];
        setItems(list);
        setCount(list.length);
        setNext(null);
        setPrevious(null);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, search, page, filtersKey]);

  useEffect(() => {
    const timer = setTimeout(load, search ? 300 : 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  // Reset to page 1 whenever the search term or fixed filters change.
  // (Deliberately not a useEffect: this is the React-recommended
  // "adjust state during render" pattern, using state — not a ref — to
  // remember the previous key, since refs can't be read during render.)
  const [previousFilterKey, setPreviousFilterKey] = useState(
    `${search}|${filtersKey}`
  );

  if (previousFilterKey !== `${search}|${filtersKey}`) {
    setPreviousFilterKey(`${search}|${filtersKey}`);

    if (page !== 1) {
      setPage(1);
    }
  }

  // Modal open/close

  function openCreate(overrides = {}) {
    setSelected(null);
    setFormData({ ...emptyFormData, ...overrides });
    setError("");
    setModalMode("create");
  }

  function openView(item) {
    setSelected(item);
    setError("");
    setModalMode("view");
  }

  function openEdit(item) {
    setSelected(item);
    setFormData({ ...emptyFormData, ...mapItemToFormData(item) });
    setError("");
    setModalMode("edit");
  }

  function closeModal() {
    if (saving) {
      return;
    }

    setModalMode(null);
    setSelected(null);
    setFormData(emptyFormData);
  }

  function handleFormChange(event) {
    const { name, value, type, checked } = event.target;

    setFormData((previousData) => ({
      ...previousData,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  // Submit (create/edit)

  async function handleSubmit() {
    if (validate) {
      const validationError = validate(formData);

      if (validationError) {
        setError(validationError);
        return;
      }
    }

    try {
      setSaving(true);
      setError("");

      const payload = mapFormToPayload(formData);

      if (modalMode === "create") {
        await api.create(payload);
      }

      if (modalMode === "edit") {
        await api.update(selected.id, payload);
      }

      setModalMode(null);
      setSelected(null);
      setFormData(emptyFormData);

      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  // Delete

  async function handleDelete(item) {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${describeItem(item)}?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");
      await api.delete(item.id);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return {
    items,
    count,
    hasNext: Boolean(next),
    hasPrevious: Boolean(previous),
    page,
    setPage,
    search,
    setSearch,
    loading,
    error,
    setError,
    reload: load,

    modalMode,
    selected,
    formData,
    setFormData,
    saving,

    openCreate,
    openView,
    openEdit,
    closeModal,
    handleFormChange,
    handleSubmit,
    handleDelete,
  };
}

export default useCrudResource;

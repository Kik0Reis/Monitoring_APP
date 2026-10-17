import { useCallback, useEffect, useState } from "react";

// everything a list page needs: loading, search, pagination, and the create / edit / view popup with delete and approve
// the page only describes its api and its form
//   api: { list, get, create, update, delete, approve }
//   emptyFormData: the form when it is empty
//   mapFormToPayload(formData): the object sent to the api, the form data by default
//   mapItemToFormData(item): fills the form when editing, the item by default
//   validate(formData): returns an error message or null
//   filters: fixed filters always sent to the api
//   describeItem(item): the name shown in the delete question
//   autoLoad: false when the page only needs the popup and not the list
export function useCrudResource({
  api,
  emptyFormData,
  mapFormToPayload = (formData) => formData,
  validate,
  mapItemToFormData = (item) => item,
  filters = {},
  describeItem = (item) => item.name,
  autoLoad = true,
}) {
  const [items, setItems] = useState([]);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState(null);
  const [previous, setPrevious] = useState(null);

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const [loading, setLoading] = useState(autoLoad);
  const [error, setError] = useState("");

  const [modalMode, setModalMode] = useState(null);
  const [selected, setSelected] = useState(null);
  const [formData, setFormData] = useState(emptyFormData);
  const [saving, setSaving] = useState(false);

  const filtersKey = JSON.stringify(filters);

  // loads the current page of the list with the search and the filters
  const load = useCallback(async () => {
    if (!autoLoad) return;

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

      const data = await api.list(`?${params.toString()}`);

      if (data && Array.isArray(data.results)) {
        setItems(data.results);
        setCount(data.count ?? data.results.length);
        setNext(data.next ?? null);
        setPrevious(data.previous ?? null);
      } else {
        // the api answered with a plain list, without pages
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
  }, [api, autoLoad, search, page, filtersKey]);

  // loads when something changes, typing in the search waits 300ms so it does not send a request per letter
  useEffect(() => {
    const timer = setTimeout(load, search ? 300 : 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  // goes back to page 1 when the search or a filter changes
  // done while rendering, which is the pattern React recommends instead of an effect
  const [previousFilterKey, setPreviousFilterKey] = useState(`${search}|${filtersKey}`);

  if (previousFilterKey !== `${search}|${filtersKey}`) {
    setPreviousFilterKey(`${search}|${filtersKey}`);

    if (page !== 1) {
      setPage(1);
    }
  }

  // opens the popup to create a record, overrides pre-fills some fields
  function openCreate(overrides = {}) {
    setSelected(null);
    setFormData({ ...emptyFormData, ...overrides });
    setError("");
    setModalMode("create");
  }

  // opens the popup with the details of a record
  function openView(item) {
    setSelected(item);
    setError("");
    setModalMode("view");
  }

  // opens the popup to edit a record
  function openEdit(item) {
    setSelected(item);
    setFormData({ ...emptyFormData, ...mapItemToFormData(item) });
    setError("");
    setModalMode("edit");
  }

  // closes the popup, it stays open while the record is being saved
  function closeModal() {
    if (saving) {
      return;
    }

    setModalMode(null);
    setSelected(null);
    setFormData(emptyFormData);
  }

  // copies what was typed into the form data
  function handleFormChange(event) {
    const { name, value, type, checked } = event.target;

    setFormData((previousData) => ({
      ...previousData,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  // validates and saves the form, creating or updating depending on the popup mode
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

  // asks for confirmation and deletes a record
  async function handleDelete(item) {
    if (!window.confirm(`Are you sure you want to delete ${describeItem(item)}?`)) {
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

  // confirms a record that was created automatically from mqtt
  async function handleApprove(item) {
    try {
      await api.approve(item.id);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return {
    items,
    loading,
    error,
    setError,
    reload: load,

    search,
    setSearch,
    pagination: { page, setPage, count, hasNext: Boolean(next), hasPrevious: Boolean(previous) },

    modalMode,
    selected,
    formData,
    saving,

    openCreate,
    openView,
    openEdit,
    closeModal,
    handleFormChange,
    handleSubmit,
    handleDelete,
    handleApprove,
  };
}

export default useCrudResource;

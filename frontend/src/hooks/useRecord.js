import { useCallback, useState } from "react";

import { useAutoRefresh } from "./useAutoRefresh";

// loads one record by id for a detail page and keeps it fresh, notFound is true when the record does not exist
// approve() confirms a record created from mqtt, if it fails the pending review badge just stays
export function useRecord(api, id) {
  const [record, setRecord] = useState(null);
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(async () => {
    try {
      setRecord(await api.get(id));
      setNotFound(false);
    } catch {
      setNotFound(true);
    }
  }, [api, id]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(load, { reloadKey: id });

  // confirms the record and reloads it
  async function approve() {
    try {
      await api.approve(record.id);
      await load();
    } catch {
      // nothing to do, the badge stays visible
    }
  }

  return { record, notFound, reload: load, lastUpdated, refreshing, refresh, approve };
}

export default useRecord;

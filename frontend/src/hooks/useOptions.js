import { useEffect, useState } from "react";

import { fetchAll } from "../services/api";

// loads every record of a list (all pages) to fill a dropdown, the list stays empty if the request fails
export function useOptions(listFn) {
  const [options, setOptions] = useState([]);

  useEffect(() => {
    fetchAll(listFn).then(setOptions).catch(() => {});
  }, [listFn]);

  return options;
}

export default useOptions;

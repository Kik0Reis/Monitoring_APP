import { useState } from "react";

import { SCOPE } from "../utils/scope";

// keeps the active/all choice of a page, it starts on active only
export function useScope(initialScope = SCOPE.ACTIVE) {
  return useState(initialScope);
}

export default useScope;

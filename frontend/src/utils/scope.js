// which records the dashboard and the tree show
// active: only active records, inactive ones are hidden and do not change any colour or count
// all: every record, inactive ones included
export const SCOPE = {
  ACTIVE: "active",
  ALL: "all",
};

// returns the query string part for a scope, for example "scope=active"
export function scopeQuery(scope) {
  return `scope=${scope}`;
}

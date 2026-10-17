// portuguese (pt-PT) dates and times used everywhere in the app: dd/mm/yyyy and 24 hour hh:mm:ss
// they do not depend on the language of the browser
const LOCALE = "pt-PT";

// converts a value to a Date, or null when it is empty or not a valid date
function toDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

// formats a date as dd/mm/yyyy
export function formatDate(value) {
  const date = toDate(value);
  if (!date) return "—";
  return date.toLocaleDateString(LOCALE, { day: "2-digit", month: "2-digit", year: "numeric" });
}

// formats a time as 24 hour hh:mm:ss, or hh:mm when withSeconds is false
export function formatTime(value, withSeconds = true) {
  const date = toDate(value);
  if (!date) return "—";
  return date.toLocaleTimeString(LOCALE, {
    hour: "2-digit",
    minute: "2-digit",
    ...(withSeconds ? { second: "2-digit" } : {}),
    hour12: false,
  });
}

// formats a date and time as dd/mm/yyyy hh:mm:ss
export function formatTimestamp(value) {
  if (!value) return "—";
  if (!toDate(value)) return String(value);
  return `${formatDate(value)} ${formatTime(value)}`;
}

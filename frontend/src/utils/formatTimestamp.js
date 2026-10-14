// Portuguese (pt-PT) date/time formatting used everywhere in the app:
// dd/mm/yyyy and 24-hour HH:MM:SS, regardless of the browser's language.
const LOCALE = "pt-PT";

function toDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDate(value) {
  const date = toDate(value);
  if (!date) return "—";
  return date.toLocaleDateString(LOCALE, { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function formatTime(value) {
  const date = toDate(value);
  if (!date) return "—";
  return date.toLocaleTimeString(LOCALE, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function formatTimestamp(value) {
  if (!value) return "—";
  if (!toDate(value)) return String(value);
  return `${formatDate(value)} ${formatTime(value)}`;
}

import { alertTypeLabel } from "../../utils/alertLabels";
import { formatDate, formatTime } from "../../utils/formatTimestamp";

// adds a leading zero to numbers below 10
const pad = (number) => String(number).padStart(2, "0");

// reads the detected class, action and confidence from the message of old detections
// new detections have these as fields, old ones only have them in the text:
// Camera 'X' detected 'smoke' (action=123, confidence=0.91).
function parseDetectionMessage(message) {
  const text = String(message ?? "");

  return {
    detected: text.match(/detected '([^']*)'/)?.[1] ?? null,
    action: text.match(/action=([^,)]+)/)?.[1]?.trim() ?? null,
    confidence: text.match(/confidence=([^)\s]+)/)?.[1] ?? null,
  };
}

// converts a value to a number, or null when it is empty or not a number
function toNumber(value) {
  if (value === null || value === undefined || value === "") return null;

  const number = Number(value);
  return Number.isNaN(number) ? null : number;
}

// shows a confidence as a percentage when it is between 0 and 1
export function formatConfidence(value) {
  if (value === null) return "—";
  return value <= 1 ? `${Math.round(value * 100)}%` : String(value);
}

// adds the fields the table needs to sort, filter and show an alert
// dateKey and timeKey are plain strings (yyyy-mm-dd and hh:mm:ss) so they can be compared directly
export function prepareRow(item) {
  const date = new Date(item.created_at);
  const validDate = !Number.isNaN(date.getTime());
  const parsed = parseDetectionMessage(item.message);

  return {
    ...item,
    dateKey: validDate ? `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` : "",
    timeKey: validDate ? `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}` : "",
    dateLabel: formatDate(item.created_at),
    timeLabel: formatTime(item.created_at),
    source: item.camera_name ?? item.device_name ?? "",
    deviceName: item.device_name ?? "",
    location: item.location_name ?? "",
    typeLabel: alertTypeLabel(item.alert_type ?? item.type),
    detectedValue: item.detected ?? parsed.detected ?? "",
    actionValue: String(item.action_code ?? parsed.action ?? ""),
    confidenceValue: toNumber(item.confidence ?? parsed.confidence),
    statusValue: item.active === false ? "Resolved" : "Active",
  };
}

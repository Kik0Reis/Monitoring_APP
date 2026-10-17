import { detectionsApi, problemsApi } from "../../services/api";
import { scopeQuery } from "../../utils/scope";

// rows a panel shows before the person has to open "View all"
export const PREVIEW_ROWS = 3;

// the panels of the dashboard in the order they are shown, to add a panel put it in this list
// kind: how its rows look (alert, device or location)
// preview: the key of the dashboard payload that has its rows
// loadAll: loads the full list for the popup, panels without it reuse the preview rows
export const PANELS = [
  {
    key: "offline",
    kind: "alert",
    eyebrow: "Connectivity",
    title: "Offline",
    tone: "critical",
    emptyText: "Nothing offline.",
    preview: "recent_offline_alerts",
    count: (dashboard) => dashboard.alert_counts.offline,
    loadAll: (scope) =>
      problemsApi.list(`?category=offline&active_only=true&limit=200&${scopeQuery(scope)}`),
  },
  {
    key: "error",
    kind: "alert",
    eyebrow: "Monitoring",
    title: "Errors",
    tone: "warning",
    emptyText: "No errors reported.",
    preview: "recent_error_alerts",
    count: (dashboard) => dashboard.alert_counts.error,
    loadAll: (scope) =>
      problemsApi.list(`?category=error&active_only=true&limit=200&${scopeQuery(scope)}`),
  },
  {
    key: "detections",
    kind: "alert",
    showDot: false,
    eyebrow: "Cameras",
    title: "Recent Detections",
    tone: "info",
    emptyText: "No detections yet.",
    preview: "recent_detections",
    count: (dashboard) => dashboard.alert_counts.detections,
    loadAll: (scope) => detectionsApi.list(`?limit=200&${scopeQuery(scope)}`),
  },
  {
    key: "devices",
    kind: "device",
    eyebrow: "Devices",
    title: "Devices with problems",
    tone: "critical",
    emptyText: "No devices with problems.",
    preview: "devices_with_problems",
    count: (dashboard) => dashboard.devices_with_problems.length,
  },
  {
    key: "locations",
    kind: "location",
    eyebrow: "Locations",
    title: "Locations with problems",
    tone: "critical",
    emptyText: "No locations with problems.",
    preview: "locations_with_problems",
    count: (dashboard) => dashboard.locations_with_problems.length,
  },
];

// finds a panel by its key
export function getPanel(key) {
  return PANELS.find((panel) => panel.key === key);
}

// returns the cards at the top, each one opens the devices or cameras list filtered by status
export function buildSummaryCards(summary) {
  return [
    { label: "Devices", value: summary.devices, description: "Total devices", to: "/devices" },
    { label: "Online", value: summary.online, description: "Devices online", to: "/devices?status=ONLINE" },
    { label: "Offline", value: summary.offline, description: "Devices offline", to: "/devices?status=OFFLINE" },
    { label: "Cameras", value: summary.cameras, description: "Registered cameras", to: "/cameras" },
    {
      label: "Cameras Online",
      value: summary.cameras_online,
      description: "Cameras online",
      to: "/cameras?status=ONLINE",
    },
    {
      label: "Cameras Offline",
      value: summary.cameras_offline,
      description: "Cameras offline",
      to: "/cameras?status=OFFLINE",
    },
  ].map((card) => ({ ...card, value: card.value ?? 0 }));
}

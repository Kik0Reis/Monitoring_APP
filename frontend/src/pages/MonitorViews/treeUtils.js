import { Camera, Cpu, Globe, MapPin, Users } from "lucide-react";

// where the "open" button of each node type goes, the detail page of that record
export const DETAIL_PATH = {
  country: (id) => `/countries/${id}`,
  customer: (id) => `/clients/${id}`,
  location: (id) => `/locations/${id}`,
  device: (id) => `/devices/${id}`,
  camera: (id) => `/cameras/${id}`,
};

// icon of each node type
export const TYPE_ICON = {
  country: Globe,
  customer: Users,
  location: MapPin,
  device: Cpu,
  camera: Camera,
};

// name of the children of each node type, used in the "3 customers" hint
const CHILD_LABEL = {
  country: "customer",
  customer: "location",
  location: "device",
  device: "camera",
};

// returns the key that identifies a node in the expanded set
export function nodeKey(node) {
  return `${node.type}-${node.id}`;
}

// returns the "3 customers" hint shown next to a node, or null when it has no children
export function childSummary(node) {
  const count = node.children.length;
  if (count === 0) return null;

  const label = CHILD_LABEL[node.type];
  return `${count} ${label}${count === 1 ? "" : "s"}`;
}

// returns the keys of every node of the tree
export function collectAllKeys(nodes, keys = new Set()) {
  for (const node of nodes) {
    keys.add(nodeKey(node));
    collectAllKeys(node.children, keys);
  }

  return keys;
}

// returns the keys of the nodes with a problem, so the branches with a problem start open
// system_check is already rolled up from the children, so one pass from the top is enough
function collectRedPathKeys(nodes, keys = new Set()) {
  for (const node of nodes) {
    if (node.system_check === "red") keys.add(nodeKey(node));
    collectRedPathKeys(node.children, keys);
  }

  return keys;
}

// returns the keys open on the first load: every country plus the branches with a problem
export function initialExpandedKeys(tree) {
  const keys = collectRedPathKeys(tree);
  tree.forEach((country) => keys.add(nodeKey(country)));
  return keys;
}

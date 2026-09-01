# CHANGES.md — What was updated in this pass

(Previous pass's notes are preserved further down this file, unchanged.)

## Setup after unzipping
This archive does **not** include `frontend/node_modules`, `backend/venv`,
`frontend/dist`, or `backend/db.sqlite3` (they're huge and 100%
regenerable). Before running:

    cd backend && python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py runserver

    cd frontend && npm install && npm run dev

Your `.env` files were kept, with two new variables added at the bottom
of `backend/.env` (retention settings, see below) and a new
`frontend/.env.example` (API base URL — copy it to `.env` if you want to
point the frontend at a non-default backend URL).

## 1. Heartbeat / database retention (the main ask)

`DeviceHeartbeat` rows were never deleted, so the table only ever grew.

- New settings: `HEARTBEAT_RETENTION_DAYS` (default 14) and
  `HEARTBEAT_CLEANUP_INTERVAL_HOURS` (default 24), both overridable via
  `.env`.
- New `backend/monitoring/services/retention.py` — deletes heartbeats
  older than the retention window, in small batches, so it doesn't lock
  the table on a big delete.
- New management command: `python manage.py cleanup_heartbeats
  [--days N]`, for running it by hand or from a cron job.
- The `heartbeat_worker` process (already running 24/7 per
  `docker-compose.yml`) now runs this cleanup automatically on its own
  schedule — no extra infrastructure (cron, Celery, etc.) needed.
- Tests added in `monitoring/services/tests_retention.py`.

If you want heartbeats kept longer or shorter, just change
`HEARTBEAT_RETENTION_DAYS` in `.env`.

## 2. Real bugs fixed

- **Customer/Location auto-provisioning crash.** `mqtt/provisioning.py`
  looked up existing Customers/Locations by `mqtt_key`, but the database's
  uniqueness constraint is on `name`. If a Customer or Location was ever
  created by hand (e.g. through the admin, before any MQTT traffic
  existed for it) with no `mqtt_key` set, the very next MQTT message for
  that customer would crash with an `IntegrityError` trying to create a
  duplicate. Fixed with a proper "adopt the existing record" fallback,
  plus a safety net for a race between two requests hitting this at once.
  This is the bug that was breaking the `mqtt` tests before this pass —
  unrelated to any of the refactoring below.
- **Dead code removed**: an unused `parse_message()` alias in
  `mqtt/parser.py`, and redundant local re-imports in `monitoring/tests.py`
  that were shadowing a module-level import.
- **Stale test fixed**: one MQTT test asserted behavior that no longer
  matched what the (correct) current code does for an unknown camera. Fixed
  the assertion and added a second test covering the real, known-camera
  path so both branches are actually tested.
- **Hardcoded API URL**: the frontend called `http://localhost:8000/api`
  directly, which only works for local dev. It's now
  `import.meta.env.VITE_API_BASE_URL`, configurable per environment (see
  `frontend/.env.example`), defaulting to the old value so nothing breaks
  if you don't set it.

## 3. Readability

- The whole backend was run through `black` + `isort`, which mostly
  removed the "every single argument on its own line" formatting that
  made the code hard to scan.
- Removed the repetitive `# ============` banner comments that appeared
  before almost every function. Where the banner had actually useful
  context in it, that text was kept as a normal comment; where it was
  just a restated section title, it was dropped since the function name
  already says that.
- Rewrote `mqtt/subscriber.py` and `mqtt/service.py` from scratch with
  the same behavior but far less ceremony.
- Tidied a few stray comments (a "change this when I add auth" note
  turned into an actual TODO explaining what's needed; a couple of
  string-concatenation artifacts cleaned up).

## 4. Modularity / de-spaghetti

- `mqtt/service.py` used to be one long function with a chain of
  `if/elif` branches handling six different MQTT message types. It's now
  a small router (`process_mqtt_message`) that dispatches to
  `_handle_device_message` (status/health/cameras) or
  `_handle_camera_message` (alert/event/error) — same behavior, but each
  piece is now easy to read and to extend with a new message type
  without touching the others.
- `mqtt/provisioning.py`'s duplicated "look up by key, fall back to
  looking up by name, then create" logic for Customer and Location was
  pulled into one shared `_resolve_by_mqtt_key()` helper instead of two
  near-identical copies.
- `monitoring/services/device_health.py` checked a device/component
  status against the same `{"up", "online", "healthy"}` set in three
  separate places. That's now a single `_is_component_healthy()` helper.

## 5. Scalability

- Heartbeat/camera timeout sweeps (`heartbeat_monitor.py`) now use
  `.only(...)` to fetch just the columns they need, instead of pulling
  every device/camera's full row (including potentially large JSON health
  blobs) on every timeout check.
- The retention cleanup above deletes in batches rather than one giant
  query, so it stays cheap even if the table has gotten large before this
  update is deployed.
- The frontend's API base URL is now environment-configurable (see
  above), which is a prerequisite for actually deploying this anywhere
  beyond one dev's laptop.

## 6. Frontend

The frontend was already in decent shape — a clean `eslint` pass, no
dead code, and a shared `useCrudResource` hook already doing the heavy
lifting for the list pages instead of duplicating CRUD logic across
Countries/Clients/Locations/Devices/Cameras. Changes here were lighter:

- Removed the one AI-style banner-comment block, in `useCrudResource.js`.
- Made the API base URL configurable (see "Real bugs fixed" above).

## What's not included

This zip does **not** include `node_modules/`, the Python `venv/`,
`frontend/dist/`, or `db.sqlite3` — those are regenerated with
`npm install`, `pip install -r requirements.txt`, `npm run build`, and
`python manage.py migrate` respectively, and shipping them would just
bloat the download.

## Suggestions for next time (not done here, out of scope for this pass)

- No authentication/permissions are configured yet — every API endpoint
  is open. Worth locking down before this goes anywhere public.
- Consider the same retention treatment for `DeviceStatusHistory` and
  resolved `DeviceAlert`/`CameraAlert` rows if those start growing large
  too — the `retention.py` pattern here would extend cleanly to them.
- If MQTT volume grows a lot, the subscriber currently processes messages
  synchronously one at a time; a queue (e.g. Celery) between the
  subscriber and the monitoring services would let you scale processing
  independently of the MQTT connection.

---

# Previous pass's notes (kept for history)

# CHANGES.md — What was updated in this pass

## Setup after unzipping
This archive does **not** include `frontend/node_modules` or `backend/venv`
(they're huge and 100% regenerable). Before running:

    cd backend && python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    python manage.py runserver

    cd frontend && npm install && npm run dev

Your existing `.env` and `db.sqlite3` were kept as-is.

## Backend (Django)

- **Devices now expose full status data.** `component_statuses`, `health_data`,
  and a new `latest_heartbeat` (cpu/memory/storage/temperature) are now part
  of the Device API response — previously stored in the DB but never sent
  to the frontend.
- **Breadcrumbs.** Customer/Location/Device/Camera serializers now return a
  `breadcrumb` field (the full Country → ... → this-item chain), so the
  frontend can render drilldown navigation without extra round trips, even
  on a hard page refresh.
- **Child counts.** Country/Customer/Location/Device now return
  `customers_count` / `locations_count` / `devices_count` / `cameras_count`,
  computed via query annotations (no N+1).
- **Fixed a real bug: duplicated dashboard logic.** There were two different
  implementations of the dashboard aggregation (`monitoring/views.py` had
  one inline, `monitoring/services/dashboard.py` had another, unused, one).
  They had drifted apart. Consolidated into a single service module
  (`monitoring/services/dashboard.py`) that the view now just calls.
- **New:** `devices_with_problems` in the dashboard payload — individual
  problem devices (not just locations), so the dashboard can link straight
  to a broken device's page.
- **New:** `GET /api/alerts/?limit=N` — full alerts feed, used by the new
  Alerts page (previously a placeholder).

## Frontend (React)

- **Shared CRUD infrastructure.** New `useCrudResource` hook centralizes the
  search/pagination/create/edit/delete logic that was copy-pasted (with
  small drifting bugs) across Countries/Clients/Locations/Devices/Cameras.
  Each list page went from ~450-600 lines to ~200.
- **Fixed a pagination bug.** The old pages fetched one page from the API
  (10 items) and then paginated *that* again client-side — meaning anything
  past the first 10 records was unreachable. Now uses the API's real
  page/count/next/previous.
- **Drilldown navigation.** New routes: `/countries/:id`, `/clients/:id`,
  `/locations/:id`, `/devices/:id`, `/cameras/:id`. Clicking a country shows
  its clients, clicking a client shows its locations, and so on down to
  cameras — each page has breadcrumbs and an inline "add child" form.
- **Device detail page** shows the full component breakdown
  (detectorapi/detector/idmr/etc., rendered generically from whatever keys
  your MQTT payload contains) and the latest heartbeat metrics.
- **Dashboard** now links both problem devices and problem locations
  straight to their pages, and auto-refreshes.
- **Unified CSS.** New `src/styles/tokens.css` (colors/type/spacing as CSS
  variables) and `src/styles/common.css` (one definition per shared class:
  buttons, tables, badges, forms, panels...). Previously every page
  redefined `.page-header h1`, `.primary-button`, `.status-dot`, etc.
  slightly differently, which is why fonts/sizes/weights felt inconsistent.
  Per-page CSS files now only contain page-specific rules (mostly empty).
- **Auto-refresh / "polling."** New `useAutoRefresh` hook, used on every
  page: loads immediately, then again every 60 seconds, with a manual
  refresh button and a "last updated Xs ago" indicator.

  Note: this is HTTP polling, not websockets. True websockets would need
  Django Channels + a channel layer (Redis) + an ASGI server — new
  infrastructure that wasn't already part of this project. Polling every
  60s meets "refresh automatically" without adding that, but if you want
  push-based websockets later, that's a good follow-up.
- **Fixed file naming.** Page files were imported with capitalized names
  (e.g. `Countries`) but saved lowercase (`countries.jsx`) — works on
  Windows/Mac, breaks on Linux. Renamed to match.

## Nothing was removed
All existing CRUD functionality (create/edit/delete/search/filter) for
every entity is intact — it was reorganized, not cut. The old "view" (👁)
modal on list pages still works; drilldown is additive (click a row's name
or the row itself to open the full detail page).

## Follow-up pass: split Alerts into Problems vs Detections

The old single "alerts" feed mixed two very different things together:
system-inferred connectivity problems (device offline, unhealthy
component, MQTT/system errors) and real camera detections reported over
MQTT (smoke, person, etc.). A device that flapped online/offline
repeatedly would also flood the feed with many resolved, historical rows
for the same device.

- **Backend:** `monitoring/services/dashboard.py` now has
  `get_problem_alerts(limit, active_only=True)` and
  `get_camera_detections(limit)` instead of one `get_recent_alerts()`.
  New endpoints: `GET /api/problems/?active_only=true|false` and
  `GET /api/detections/`. The old `/api/alerts/` endpoint is gone —
  everything that used it now uses one of the two new ones.
- **`active_only=True` is the default** and is what fixes the repeat
  issue: the backend already reuses a single alert row while something
  stays broken, so filtering to active naturally gives one row per
  currently-broken device/camera. `active_only=false` still exposes full
  history (useful for diagnosing a flapping device).
- **Frontend:** the Alerts page now has two tabs — "Problems" (with a
  "Show history" toggle) and "Detections" (a plain chronological log,
  no active/resolved concept — every detection is a distinct event that
  never resolves). The Dashboard's alert panel was renamed "Recent
  Problems" and now uses the deduped, active-only feed.

## Follow-up pass: tree-based MQTT auto-provisioning

Previously, an MQTT message for a device that didn't already exist in the
database was silently dropped ("Received MQTT message for unknown Edge
device"). Worse: `Device.mqtt_identifier` was globally unique across the
*entire* database, not scoped per location — so two different customers
whose installers both happened to name a device "01" (very plausible,
since bare device IDs like "01" are common) would hit a hard database
error the moment the second one was created.

- **`mqtt_identifier` is now unique per-location**, not globally
  (migration applied and tested against the real database). Two
  different customers can now both have a device called "01" —
  tested directly and confirmed working.
- **New `mqtt/provisioning.py`** resolves the full `Country -> Customer
  -> Location -> Device` tree from the MQTT topic
  (`aiaction/{country}/{client}/{installation}/{device_id}/...`),
  auto-creating whichever pieces don't exist yet, instead of routing on
  a bare device_id.
- **Stable matching keys.** `Customer.mqtt_key` and `Location.mqtt_key`
  are set once when a record is auto-created from MQTT and never
  change, even if a human renames the customer/location's display
  `name` afterward in the UI. Matching against the editable `name`
  field would have caused a duplicate to be created the next time a
  renamed customer's device reported in — tested and confirmed this
  does not happen.
- **`pending_review` flag** added to Country/Customer/Location/Device.
  Anything auto-created from MQTT (untrusted network input) starts
  flagged rather than treated as fully trusted immediately. Devices
  also get a placeholder serial number (`AUTO-{location_id}-{identifier}`)
  since MQTT provides no real serial number.
  - Filterable via `?pending_review=true` on every list endpoint.
  - New `POST /api/<resource>/<id>/approve/` action clears the flag.
  - Frontend: a "Pending Review" badge appears next to the name
    everywhere the record shows up (list pages, detail pages, and
    nested child tables), with an "Approve" button/icon next to it.
  - Registered in Django admin too, with a filter for it.
- Registered `DeviceAlert`/`CameraAlert`/`DeviceHeartbeat` in Django
  admin (previously not registered at all, despite being exactly the
  models you'd want to inspect while debugging).

### A note on MQTT topic naming
The topic *structure* your devices already use
(`aiaction/{country}/{client}/{installation}/{device_id}/...`) is fine
and is what the auto-provisioning above relies on. What isn't governed
by any convention is the *values* installers put in each segment —
inconsistent casing (`aitecserv` vs `Onda`) and bare, non-unique device
IDs (`"01"`). Worth raising with your team: (1) country segment should
always be a fixed-case ISO country code, (2) client/installation
segments should follow one agreed slug format, (3) device IDs should be
meaningful on their own (e.g. the device's real serial number), not a
bare number that only makes sense within one installation.

## Follow-up pass: auto-create cameras from MQTT too

Extended the same auto-provisioning approach to cameras. The
`.../cameras` topic (device's camera status list — the one with
`camera_id`, `name`, and an explicit `status`) is the one that drives
real Camera rows; the per-component `status/detectorapi`,
`status/idmr`, `status/detector` payloads use a different identifier
format (`camera_id_ch1`) and remain purely informational, stored in the
device's component health board as before — they don't create/update
individual Camera rows.

- `Camera` gained the same `pending_review` flag as the other four
  entities, plus a `POST /api/cameras/<id>/approve/` action and
  `?pending_review=true` filtering.
- `monitoring/services/camera_monitor.py::process_camera_status_list`
  now auto-creates a camera (via the new `resolve_camera()` in
  `mqtt/provisioning.py`) instead of silently skipping when a device
  reports a camera_id it hasn't seen before. New cameras default to
  channel 1 (this payload doesn't carry channel info) and take their
  name straight from the payload's `name` field.
- No uniqueness-scoping fix was needed here the way there was for
  devices — `Camera.camera_identifier` was already scoped per-device,
  not global, so two different devices reporting the same camera_id
  never collided in the first place.
- Tested end-to-end with the exact real payload provided: one
  `.../cameras` message auto-created the customer, location, device,
  *and* both cameras in a single pass, all correctly flagged
  `pending_review` and linked to the right parent at every level.
- Frontend: the same "Pending Review" badge + Approve action now also
  appears on the Cameras list page, the camera table inside a device's
  detail page, and the camera detail page itself.


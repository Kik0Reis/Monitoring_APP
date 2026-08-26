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


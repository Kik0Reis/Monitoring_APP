# AiTecServ Monitor

Web app to monitor edge devices and their cameras. The devices report over MQTT, the backend keeps their status, alerts and detections, and the frontend shows them.

## Structure

```
backend/                 Django + Django REST Framework
  core/                  shared code: base model, alert rules, breadcrumbs, serializer helpers, base viewset, .env settings
  countries/ customers/  the hierarchy: country > customer > location > device > camera
  locations/ devices/
  cameras/
  monitoring/            heartbeats, alerts, detections, dashboard and tree
    services/            alert_queries (what counts as a problem), alert_lists (what the api returns),
                         dashboard, tree, scope (active/all filter), device_health, camera_monitor,
                         heartbeat_monitor, mqtt_reconciliation, retention
  mqtt/                  subscriber, topic parser, service and automatic creation of records
  config/                settings and api routes

frontend/                React + Vite
  src/pages/             one folder per page, the page file is called XxxPage.jsx
  src/components/        common (small pieces), crud (list and popup), detail (detail pages), layout
  src/hooks/             data loading (useAutoRefresh, useCrudResource, useRecord, useScope, ...)
  src/services/          http client and api endpoints
  src/styles/            global css split by topic, loaded in order by styles/index.css
  src/utils/             formatting and small helpers
```

## Running

Backend (needs a `backend/.env`):

```
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
python manage.py mqtt_subscriber     # listens to the broker
python manage.py heartbeat_worker    # marks devices offline and cleans old data
```

Frontend:

```
cd frontend
npm install
npm run dev
```

In development set `VITE_API_BASE_URL` (for example `http://localhost:8000/api`), in production nginx serves the build and proxies `/api`.

Production: `docker compose -f docker-compose.prod.yml up -d --build`.

## Tests and checks

```
cd backend && python manage.py test
cd frontend && npm run lint && npm run build
```

## Active and all

Devices, cameras, locations and customers have an `active` flag. The dashboard and the monitor tree can show only active records or all of them:

- `?scope=active` hides inactive records and everything under them, they do not change any colour or count
- `?scope=all` (default of the api) shows everything

The frontend starts on active only and has an Active only / All button on both pages.

## Where to add things

- a page: create `pages/Name/NamePage.jsx` and add it to the list in `App.jsx`
- a menu item: add it to `NAV_ITEMS` in `components/layout/Sidebar.jsx`
- a dashboard panel: add it to `PANELS` in `pages/Dashboard/dashboardConfig.js`
- an alerts tab or column: `pages/Alerts/alertColumns.jsx`
- a setting: add the field in `pages/Settings/settingsFields.js` and in `core/serializers.py`
- a list page: use `useCrudResource`, `DataTable`, `RowActions` and `ResourceModal` like `pages/Devices/DevicesPage.jsx`

## Code style

Every class, function and component has a short `//` (or `#` in python) comment above it that says what it does. Keep new code the same way.

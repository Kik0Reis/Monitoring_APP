# frontend path of each record type
CRUMB_PATHS = {
    "country": "countries",
    "customer": "clients",
    "location": "locations",
    "device": "devices",
    "camera": "cameras",
}


# builds one breadcrumb entry for the frontend navigation
def _crumb(kind, record):
    return {
        "type": kind,
        "id": record.id,
        "name": record.name,
        "path": f"/{CRUMB_PATHS[kind]}/{record.id}",
    }


# returns the breadcrumb of a customer: country > customer
def customer_breadcrumb(customer):
    return [_crumb("country", customer.country), _crumb("customer", customer)]


# returns the breadcrumb of a location: country > customer > location
def location_breadcrumb(location):
    return customer_breadcrumb(location.customer) + [_crumb("location", location)]


# returns the breadcrumb of a device: country > customer > location > device
def device_breadcrumb(device):
    return location_breadcrumb(device.location) + [_crumb("device", device)]


# returns the breadcrumb of a camera: country > customer > location > device > camera
def camera_breadcrumb(camera):
    return device_breadcrumb(camera.device) + [_crumb("camera", camera)]

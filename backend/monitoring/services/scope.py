from django.db.models import Q

SCOPE_ACTIVE = "active"
SCOPE_ALL = "all"


# reads ?scope=active|all from a request, returns True when inactive records must be hidden
def hide_inactive_from_request(request):
    return request.query_params.get("scope", SCOPE_ALL).lower() == SCOPE_ACTIVE


# matches a location that is active and belongs to an active customer
def active_location_q(prefix=""):
    return Q(**{
        f"{prefix}active": True,
        f"{prefix}customer__active": True,
    })


# matches a device that is active and sits in an active location
def active_device_q(prefix=""):
    return Q(**{f"{prefix}active": True}) & active_location_q(f"{prefix}location__")


# matches a camera that is active and belongs to an active device
def active_camera_q(prefix=""):
    return Q(**{f"{prefix}active": True}) & active_device_q(f"{prefix}device__")

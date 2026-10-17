from rest_framework import serializers


# trims a text value and makes sure it has at least min_length characters
def clean_name(value, label, min_length=2):
    value = value.strip()

    if len(value) < min_length:
        raise serializers.ValidationError(f"{label} must contain at least {min_length} characters.")

    return value


# returns the count the viewset annotated on the object, or counts with a query when it is missing
def annotated_count(obj, annotation, related_name):
    annotated = getattr(obj, annotation, None)

    if annotated is not None:
        return annotated

    return getattr(obj, related_name).count()

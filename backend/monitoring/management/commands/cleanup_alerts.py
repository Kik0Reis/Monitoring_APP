from django.conf import settings
from django.core.management.base import BaseCommand

from monitoring.services.retention import delete_old_resolved_alerts


class Command(BaseCommand):
    help = (
        "Delete resolved DeviceAlert/CameraAlert rows (active=False) older "
        "than the configured retention window. Active alerts are never "
        "touched. Runs automatically inside heartbeat_worker, but can also "
        "be run on demand or from a cron job / scheduled task."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help=(
                "Delete resolved alerts older than this many days. "
                "Defaults to ALERT_RETENTION_DAYS from settings/.env."
            ),
        )

    def handle(self, *args, **options):
        retention_days = options["days"] or settings.ALERT_RETENTION_DAYS

        deleted_count = delete_old_resolved_alerts(retention_days=retention_days)

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} resolved alert(s) older than "
                f"{retention_days} day(s)."
            )
        )

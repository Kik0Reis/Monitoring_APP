from django.conf import settings
from django.core.management.base import BaseCommand

from monitoring.services.retention import delete_old_heartbeats


# management command that deletes old heartbeats
class Command(BaseCommand):
    help = "Deletes heartbeats older than the retention days."

    # defines the --days option
    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help=(
                "Delete heartbeats older than this many days. Defaults to "
                "HEARTBEAT_RETENTION_DAYS from settings/.env."
            ),
        )

    # deletes the old heartbeats and prints how many were deleted
    def handle(self, *args, **options):
        retention_days = options["days"] or settings.HEARTBEAT_RETENTION_DAYS

        deleted_count = delete_old_heartbeats(retention_days=retention_days)

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} heartbeat(s) older than "
                f"{retention_days} day(s)."
            )
        )

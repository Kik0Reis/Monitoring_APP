import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from monitoring.services.heartbeat_monitor import (
    DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    check_all_heartbeats,
)
from monitoring.services.retention import delete_old_heartbeats


class Command(BaseCommand):
    help = (
        "Long-running worker that continuously monitors Edge devices and "
        "cameras for missed heartbeats, and periodically prunes old "
        "heartbeat history from the database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
            help="Heartbeat timeout in seconds.",
        )
        parser.add_argument(
            "--interval", type=int, default=10, help="Seconds between heartbeat checks."
        )
        parser.add_argument(
            "--cleanup-interval-hours",
            type=int,
            default=settings.HEARTBEAT_CLEANUP_INTERVAL_HOURS,
            help="Hours between old-heartbeat cleanup runs.",
        )

    def handle(self, *args, **options):
        timeout_seconds = options["timeout"]
        interval_seconds = options["interval"]
        cleanup_interval_seconds = options["cleanup_interval_hours"] * 3600

        self.stdout.write(
            self.style.SUCCESS(
                f"Heartbeat worker started: timeout={timeout_seconds}s, "
                f"interval={interval_seconds}s, "
                f"cleanup every {options['cleanup_interval_hours']}h "
                f"(keeping {settings.HEARTBEAT_RETENTION_DAYS} days of history)"
            )
        )

        # Run an initial cleanup on startup, then track when the next one
        # is due. A single restart-loop process is enough here because
        # this command already runs as a permanent, always-on service
        # (see docker-compose.yml) — no separate cron/scheduler needed.
        next_cleanup_at = timezone.now()

        while True:
            result = check_all_heartbeats(timeout_seconds=timeout_seconds)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Heartbeat check: {result['devices_offline']} devices "
                    f"offline, {result['cameras_offline']} cameras offline."
                )
            )

            if timezone.now() >= next_cleanup_at:
                deleted_count = delete_old_heartbeats()

                if deleted_count:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Heartbeat cleanup: removed {deleted_count} "
                            "old heartbeat(s)."
                        )
                    )

                next_cleanup_at = timezone.now() + timezone.timedelta(
                    seconds=cleanup_interval_seconds
                )

            time.sleep(interval_seconds)

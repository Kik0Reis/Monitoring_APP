import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from monitoring.services.heartbeat_monitor import (
    DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    check_all_heartbeats,
)
from monitoring.services.retention import (
    delete_old_detections,
    delete_old_heartbeats,
    delete_old_resolved_alerts,
    resolve_stale_alerts,
)


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
                f"(keeping {settings.HEARTBEAT_RETENTION_DAYS} days of heartbeats, "
                f"{settings.ALERT_RETENTION_DAYS} days of resolved alerts, "
                f"{settings.DETECTION_RETENTION_DAYS} days of detections; "
                f"auto-resolving stale error alerts after "
                f"{settings.ALERT_STALE_HOURS}h of MQTT silence)"
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
                deleted_heartbeats = delete_old_heartbeats()

                if deleted_heartbeats:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Heartbeat cleanup: removed {deleted_heartbeats} "
                            "old heartbeat(s)."
                        )
                    )

                deleted_alerts = delete_old_resolved_alerts()

                if deleted_alerts:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Alert cleanup: removed {deleted_alerts} "
                            "old resolved alert(s)."
                        )
                    )

                resolved_stale = resolve_stale_alerts()

                if resolved_stale:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Stale alert cleanup: auto-resolved {resolved_stale} "
                            "alert(s) no longer reported on MQTT."
                        )
                    )

                deleted_detections = delete_old_detections()

                if deleted_detections:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Detection cleanup: removed {deleted_detections} "
                            "old detection(s)."
                        )
                    )

                next_cleanup_at = timezone.now() + timezone.timedelta(
                    seconds=cleanup_interval_seconds
                )

            time.sleep(interval_seconds)

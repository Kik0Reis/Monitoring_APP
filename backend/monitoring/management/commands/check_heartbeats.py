from django.core.management.base import BaseCommand

from monitoring.services.heartbeat_monitor import (
    check_all_heartbeats,
    DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
)


class Command(BaseCommand):
    help = "Check Edge devices and cameras for heartbeat timeouts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
            help="Heartbeat timeout in seconds.",
        )

    def handle(self, *args, **options):
        timeout_seconds = options["timeout"]

        result = check_all_heartbeats(
            timeout_seconds=timeout_seconds,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Heartbeat check completed: "
                f"{result['devices_offline']} devices offline, "
                f"{result['cameras_offline']} cameras offline."
            )
        )
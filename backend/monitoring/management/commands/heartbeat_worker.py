import time

from django.core.management.base import BaseCommand

from monitoring.services.heartbeat_monitor import (
    check_all_heartbeats,
    DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
)


class Command(BaseCommand):
    help = "Continuously monitor Edge devices and cameras."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
            help="Heartbeat timeout in seconds.",
        )

        parser.add_argument(
            "--interval",
            type=int,
            default=10,
            help="Seconds between heartbeat checks.",
        )

    def handle(self, *args, **options):
        timeout_seconds = options["timeout"]
        interval_seconds = options["interval"]

        self.stdout.write(
            self.style.SUCCESS(
                "Heartbeat worker started: "
                f"timeout={timeout_seconds}s, "
                f"interval={interval_seconds}s"
            )
        )

        while True:
            result = check_all_heartbeats(
                timeout_seconds=timeout_seconds,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Heartbeat check: "
                    f"{result['devices_offline']} devices offline, "
                    f"{result['cameras_offline']} cameras offline."
                )
            )

            time.sleep(interval_seconds)
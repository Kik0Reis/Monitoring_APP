"""
Django management command for the MQTT subscriber.
"""

from django.core.management.base import BaseCommand

from mqtt.subscriber import MQTTSubscriber


class Command(BaseCommand):
    """
    Start the MQTT subscriber.
    """

    help = "Start the EMQX Cloud MQTT subscriber."

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.SUCCESS(
                "Starting MQTT subscriber..."
            )
        )

        subscriber = MQTTSubscriber()

        try:
            subscriber.start()

        except KeyboardInterrupt:

            self.stdout.write(
                self.style.WARNING(
                    "Stopping MQTT subscriber..."
                )
            )

            subscriber.stop()
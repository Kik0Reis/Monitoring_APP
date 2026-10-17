# management command that starts the mqtt subscriber

from django.core.management.base import BaseCommand

from mqtt.subscriber import MQTTSubscriber


# starts the mqtt subscriber and stops it on ctrl+c
class Command(BaseCommand):
    help = "Start the EMQX Cloud MQTT subscriber."

    # runs the subscriber until it is interrupted
    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS("Starting MQTT subscriber..."))

        subscriber = MQTTSubscriber()

        try:
            subscriber.start()

        except KeyboardInterrupt:

            self.stdout.write(self.style.WARNING("Stopping MQTT subscriber..."))

            subscriber.stop()

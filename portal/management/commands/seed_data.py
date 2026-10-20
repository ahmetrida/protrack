from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'ProTrack Cloud v1.05 operates dynamically while preserving existing records.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(
            "ProTrack Cloud v1.05 is active! Existing database records are preserved."
        ))

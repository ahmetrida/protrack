from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'ProTrack v4.0 runs 100% dynamically via self-service registration.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(
            "ProTrack v4.0 is configured for 100% fresh self-service registration! Visit /signup/ in your browser to create your University, College, Department, and Role accounts dynamically."
        ))

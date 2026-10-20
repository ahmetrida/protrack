from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'ProTrack v5.0 operates 100% dynamically via role-verified self-service registration.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(
            "ProTrack v5.0 is ready! Visit /signup/ to register your Institution Admin (with Front & Back ID proof), add Universities/Colleges/Departments, and onboard Faculty Guides & Students."
        ))

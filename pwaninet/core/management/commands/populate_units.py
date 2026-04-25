from django.core.management.base import BaseCommand
from courses.models import Course, Unit

class Command(BaseCommand):
    help = 'Populates the database with Pwani University units'

    def handle(self, *args, **kwargs):
        # Gets or create the course 
        cs_course, created = Course.objects.get_or_create(name="Computer Science")
        
        #Defining the units (code,name,year)
        units_to_add = [
            ("SMA 121", "Discrete Mathematics", 1),
            ("BIT 111", "Introduction to Programming", 1),
            ("PHY 111", "Electronics", 1),
            ("SMA 122", "Calculus I", 1),
            ("CSC 121", "Computer Organization", 1),
        ]

        #feeds the units into the db
        for code, name, year in units_to_add:
            unit, created = Unit.objects.get_or_create(
                code=code,
                defaults={'name': name, 'course': cs_course, 'year': year}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Deployed: {name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Skipped (Exists): {name}"))
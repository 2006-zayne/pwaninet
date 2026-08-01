"""Management command to seed enhanced academic data with realistic university structure."""

from django.core.management.base import BaseCommand
from django.db import transaction
from documents.academic.models import (
    AcademicYear, Semester, AcademicLevel,
    Faculty, School, Department, Programme,
    AcademicUnit, ProgrammeUnit
)
from documents.documents.models import Category


class Command(BaseCommand):
    help = 'Seed enhanced academic data with realistic university structure'

    def handle(self, *args, **options):
        self.stdout.write('Seeding enhanced academic data...')
        
        with transaction.atomic():
            self.seed_academic_levels()
            self.seed_academic_years()
            self.seed_semesters()
            self.seed_faculties()
            self.seed_schools()
            self.seed_departments()
            self.seed_programmes()
            self.seed_academic_units()
            self.seed_programme_units()
            self.seed_categories()
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded enhanced academic data'))

    def seed_academic_levels(self):
        """Seed academic levels (Year 1-6, Masters, PhD)."""
        levels = [
            (1, 'Year 1', 'First year of undergraduate study'),
            (2, 'Year 2', 'Second year of undergraduate study'),
            (3, 'Year 3', 'Third year of undergraduate study'),
            (4, 'Year 4', 'Fourth year of undergraduate study'),
            (5, 'Year 5', 'Fifth year of undergraduate study'),
            (6, 'Year 6', 'Sixth year of undergraduate study'),
            (7, 'Masters', 'Postgraduate masters level'),
            (8, 'PhD', 'Doctoral level'),
        ]
        
        for level, name, description in levels:
            obj, created = AcademicLevel.objects.get_or_create(
                level=level,
                defaults={
                    'name': name,
                    'description': description,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'  Created AcademicLevel: {name}')
    
    def seed_academic_years(self):
        """Seed academic years (2023/2024, 2024/2025, 2025/2026)."""
        from datetime import date
        
        years = [
            ('2023/2024', '2023/2024', date(2023, 9, 1), date(2024, 8, 31), False),
            ('2024/2025', '2024/2025', date(2024, 9, 1), date(2025, 8, 31), True),
            ('2025/2026', '2025/2026', date(2025, 9, 1), date(2026, 8, 31), False),
        ]
        
        for code, name, start_date, end_date, is_current in years:
            obj, created = AcademicYear.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_current': is_current
                }
            )
            if created:
                self.stdout.write(f'  Created AcademicYear: {name}')
    
    def seed_semesters(self):
        """Seed semesters for each academic year."""
        from datetime import date
        
        for year in AcademicYear.objects.all():
            semesters = [
                (1, date(year.start_date.year, 9, 1), date(year.start_date.year, 12, 31), False),
                (2, date(year.start_date.year + 1, 1, 1), date(year.start_date.year + 1, 5, 31), True if year.is_current else False),
                (3, date(year.start_date.year + 1, 6, 1), date(year.start_date.year + 1, 8, 15), False),
            ]
            
            for number, start_date, end_date, is_current in semesters:
                obj, created = Semester.objects.get_or_create(
                    number=number,
                    academic_year=year,
                    defaults={
                        'start_date': start_date,
                        'end_date': end_date,
                        'is_current': is_current
                    }
                )
                if created:
                    self.stdout.write(f'  Created Semester: {number} - {year.code}')
    
    def seed_faculties(self):
        """Seed faculties."""
        faculties = [
            ('SCI', 'Faculty of Science and Technology', 'Computing, Engineering, and Pure Sciences'),
            ('BUS', 'Faculty of Business and Economics', 'Business, Economics, and Management'),
            ('ART', 'Faculty of Arts and Social Sciences', 'Humanities, Social Sciences, and Arts'),
            ('MED', 'Faculty of Health Sciences', 'Medicine, Nursing, and Pharmacy'),
            ('LAW', 'Faculty of Law', 'Legal studies and jurisprudence'),
        ]
        
        for code, name, description in faculties:
            obj, created = Faculty.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'description': description,
                    'slug': name.lower().replace(' ', '-')
                }
            )
            if created:
                self.stdout.write(f'  Created Faculty: {name}')
    
    def seed_schools(self):
        """Seed schools within faculties."""
        schools = [
            # Science and Technology
            ('CS', 'School of Computing', 'SCI', 'Computer Science and IT'),
            ('ENG', 'School of Engineering', 'SCI', 'Engineering disciplines'),
            ('SCI', 'School of Pure Sciences', 'SCI', 'Mathematics, Physics, Chemistry'),
            
            # Business and Economics
            ('BIZ', 'School of Business', 'BUS', 'Business Administration'),
            ('ECO', 'School of Economics', 'BUS', 'Economics and Finance'),
            
            # Arts and Social Sciences
            ('HUM', 'School of Humanities', 'ART', 'Languages, Literature, History'),
            ('SOC', 'School of Social Sciences', 'ART', 'Sociology, Psychology, Political Science'),
            
            # Health Sciences
            ('MED', 'School of Medicine', 'MED', 'Medical studies'),
            ('NUR', 'School of Nursing', 'MED', 'Nursing and Healthcare'),
            
            # Law
            ('LAW', 'School of Law', 'LAW', 'Legal studies'),
        ]
        
        for code, name, faculty_code, description in schools:
            faculty = Faculty.objects.get(code=faculty_code)
            obj, created = School.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'faculty': faculty,
                    'description': description,
                    'slug': name.lower().replace(' ', '-')
                }
            )
            if created:
                self.stdout.write(f'  Created School: {name}')
    
    def seed_departments(self):
        """Seed departments within schools."""
        departments = [
            # Computing
            ('CS', 'Computer Science', 'CS', 'Core CS curriculum'),
            ('IT', 'Information Technology', 'CS', 'IT and Systems'),
            ('SE', 'Software Engineering', 'CS', 'Software development'),
            
            # Engineering
            ('CE', 'Civil Engineering', 'ENG', 'Civil and Structural'),
            ('EE', 'Electrical Engineering', 'ENG', 'Electrical and Electronics'),
            ('ME', 'Mechanical Engineering', 'ENG', 'Mechanical systems'),
            
            # Business
            ('MGT', 'Management', 'BIZ', 'Business Management'),
            ('MKT', 'Marketing', 'BIZ', 'Marketing and Sales'),
            ('ACC', 'Accounting', 'BIZ', 'Accounting and Finance'),
            
            # Humanities
            ('ENG', 'English', 'HUM', 'English Language and Literature'),
            ('HIS', 'History', 'HUM', 'Historical studies'),
            
            # Social Sciences
            ('PSY', 'Psychology', 'SOC', 'Psychological sciences'),
            ('SOC', 'Sociology', 'SOC', 'Sociological studies'),
            
            # Medicine
            ('MED', 'Medicine', 'MED', 'General Medicine'),
            ('SUR', 'Surgery', 'MED', 'Surgical disciplines'),
            ('NUR', 'Nursing', 'MED', 'Nursing and Healthcare'),
            
            # Law
            ('LAW', 'Law', 'LAW', 'General Law'),
            ('CRIM', 'Criminal Law', 'LAW', 'Criminal Justice'),
        ]
        
        for code, name, school_code, description in departments:
            school = School.objects.get(code=school_code)
            obj, created = Department.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'school': school,
                    'description': description,
                    'slug': name.lower().replace(' ', '-')
                }
            )
            if created:
                self.stdout.write(f'  Created Department: {name}')
    
    def seed_programmes(self):
        """Seed academic programmes."""
        programmes = [
            # Computing
            ('BSC-CS', 'BSc Computer Science', 'CS', 4, 'Undergraduate CS programme'),
            ('BSC-IT', 'BSc Information Technology', 'IT', 4, 'Undergraduate IT programme'),
            ('BSC-SE', 'BSc Software Engineering', 'SE', 4, 'Undergraduate SE programme'),
            ('MSC-CS', 'MSc Computer Science', 'CS', 2, 'Postgraduate CS programme'),
            
            # Engineering
            ('BSC-CE', 'BSc Civil Engineering', 'CE', 5, 'Undergraduate Civil Engineering'),
            ('BSC-EE', 'BSc Electrical Engineering', 'EE', 5, 'Undergraduate Electrical Engineering'),
            ('BSC-ME', 'BSc Mechanical Engineering', 'ME', 5, 'Undergraduate Mechanical Engineering'),
            
            # Business
            ('BBA', 'BBA Business Administration', 'MGT', 4, 'Undergraduate Business'),
            ('BSC-ACC', 'BSc Accounting', 'ACC', 4, 'Undergraduate Accounting'),
            ('MBA', 'MBA', 'MGT', 2, 'Master of Business Administration'),
            
            # Humanities
            ('BA-ENG', 'BA English', 'ENG', 3, 'Undergraduate English'),
            ('BA-HIS', 'BA History', 'HIS', 3, 'Undergraduate History'),
            
            # Social Sciences
            ('BSC-PSY', 'BSc Psychology', 'PSY', 4, 'Undergraduate Psychology'),
            ('BA-SOC', 'BA Sociology', 'SOC', 3, 'Undergraduate Sociology'),
            
            # Medicine
            ('MBBS', 'MBBS', 'MED', 6, 'Bachelor of Medicine, Bachelor of Surgery'),
            ('BSC-NUR', 'BSc Nursing', 'MED', 4, 'Bachelor of Nursing'),
            
            # Law
            ('LLB', 'LLB', 'LAW', 4, 'Bachelor of Laws'),
            ('LLM', 'LLM', 'LAW', 2, 'Master of Laws'),
        ]
        
        for code, name, dept_code, duration, description in programmes:
            department = Department.objects.get(code=dept_code)
            obj, created = Programme.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'department': department,
                    'duration_years': duration,
                    'description': description,
                    'is_active': True,
                    'slug': name.lower().replace(' ', '-')
                }
            )
            if created:
                self.stdout.write(f'  Created Programme: {name}')
    
    def seed_academic_units(self):
        """Seed academic units."""
        units = [
            # Computer Science
            ('CSC101', 'Introduction to Programming', 'CS', 3, 'Basic programming concepts'),
            ('CSC102', 'Data Structures', 'CS', 3, 'Fundamental data structures'),
            ('CSC201', 'Algorithms', 'CS', 3, 'Algorithm design and analysis'),
            ('CSC202', 'Database Systems', 'CS', 3, 'Database design and SQL'),
            ('CSC301', 'Software Engineering', 'CS', 3, 'Software development practices'),
            ('CSC302', 'Operating Systems', 'CS', 3, 'OS concepts and internals'),
            ('CSC401', 'Artificial Intelligence', 'CS', 3, 'AI fundamentals'),
            ('CSC402', 'Machine Learning', 'CS', 3, 'ML algorithms and applications'),
            
            # Information Technology
            ('IT101', 'Computer Fundamentals', 'IT', 3, 'Basic computer concepts'),
            ('IT201', 'Network Administration', 'IT', 3, 'Network management'),
            ('IT202', 'Web Technologies', 'IT', 3, 'Web development'),
            ('IT301', 'Information Security', 'IT', 3, 'Cybersecurity basics'),
            
            # Software Engineering
            ('SE201', 'Requirements Engineering', 'SE', 3, 'Software requirements'),
            ('SE301', 'Software Testing', 'SE', 3, 'Testing methodologies'),
            ('SE401', 'Software Architecture', 'SE', 3, 'Architectural patterns'),
            
            # Business
            ('BIZ101', 'Introduction to Business', 'MGT', 3, 'Business fundamentals'),
            ('BIZ201', 'Business Communication', 'MGT', 3, 'Communication skills'),
            ('BIZ301', 'Strategic Management', 'MGT', 3, 'Business strategy'),
            ('ACC101', 'Financial Accounting', 'ACC', 3, 'Accounting principles'),
            ('ACC201', 'Cost Accounting', 'ACC', 3, 'Cost management'),
            ('MKT101', 'Principles of Marketing', 'MKT', 3, 'Marketing fundamentals'),
            
            # Psychology
            ('PSY101', 'Introduction to Psychology', 'PSY', 3, 'Psychology basics'),
            ('PSY201', 'Developmental Psychology', 'PSY', 3, 'Human development'),
            ('PSY301', 'Cognitive Psychology', 'PSY', 3, 'Cognitive processes'),
            
            # Law
            ('LAW101', 'Introduction to Law', 'LAW', 3, 'Legal system overview'),
            ('LAW201', 'Contract Law', 'LAW', 3, 'Contract principles'),
            ('LAW301', 'Criminal Law', 'LAW', 3, 'Criminal justice'),
            ('LAW401', 'Constitutional Law', 'LAW', 3, 'Constitutional principles'),
        ]
        
        for code, name, dept_code, credits, description in units:
            department = Department.objects.get(code=dept_code)
            obj, created = AcademicUnit.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'description': description,
                    'credit_hours': credits,
                    'is_active': True,
                    'slug': name.lower().replace(' ', '-')
                }
            )
            if created:
                self.stdout.write(f'  Created AcademicUnit: {code} - {name}')
    
    def seed_programme_units(self):
        """Seed programme-unit curriculum mappings."""
        # Get academic entities
        bsc_cs = Programme.objects.get(code='BSC-CS')
        bsc_it = Programme.objects.get(code='BSC-IT')
        bba = Programme.objects.get(code='BBA')
        current_year = AcademicYear.objects.get(is_current=True)
        semesters = Semester.objects.filter(academic_year=current_year)
        
        # BSc Computer Science curriculum
        cs_units = [
            ('CSC101', 1, 1),
            ('CSC102', 1, 2),
            ('CSC201', 2, 1),
            ('CSC202', 2, 2),
            ('CSC301', 3, 1),
            ('CSC302', 3, 2),
            ('CSC401', 4, 1),
            ('CSC402', 4, 2),
        ]
        
        for unit_code, level_num, sem_num in cs_units:
            unit = AcademicUnit.objects.get(code=unit_code)
            level = AcademicLevel.objects.get(level=level_num)
            semester = semesters.filter(number=sem_num).first()
            
            obj, created = ProgrammeUnit.objects.get_or_create(
                programme=bsc_cs,
                academic_unit=unit,
                academic_level=level,
                academic_year=current_year,
                semester=semester,
                defaults={'is_core': True, 'is_elective': False}
            )
            if created:
                self.stdout.write(f'  Created ProgrammeUnit: {bsc_cs.code} - {unit.code} (Level {level_num})')
        
        # BSc IT curriculum
        it_units = [
            ('IT101', 1, 1),
            ('CSC101', 1, 1),  # Shared unit
            ('IT201', 2, 1),
            ('IT202', 2, 2),
            ('IT301', 3, 1),
        ]
        
        for unit_code, level_num, sem_num in it_units:
            unit = AcademicUnit.objects.get(code=unit_code)
            level = AcademicLevel.objects.get(level=level_num)
            semester = semesters.filter(number=sem_num).first()
            
            obj, created = ProgrammeUnit.objects.get_or_create(
                programme=bsc_it,
                academic_unit=unit,
                academic_level=level,
                academic_year=current_year,
                semester=semester,
                defaults={'is_core': True, 'is_elective': False}
            )
            if created:
                self.stdout.write(f'  Created ProgrammeUnit: {bsc_it.code} - {unit.code} (Level {level_num})')
        
        # BBA curriculum
        bba_units = [
            ('BIZ101', 1, 1),
            ('BIZ201', 2, 1),
            ('BIZ301', 3, 1),
            ('ACC101', 1, 2),
            ('MKT101', 2, 2),
        ]
        
        for unit_code, level_num, sem_num in bba_units:
            unit = AcademicUnit.objects.get(code=unit_code)
            level = AcademicLevel.objects.get(level=level_num)
            semester = semesters.filter(number=sem_num).first()
            
            obj, created = ProgrammeUnit.objects.get_or_create(
                programme=bba,
                academic_unit=unit,
                academic_level=level,
                academic_year=current_year,
                semester=semester,
                defaults={'is_core': True, 'is_elective': False}
            )
            if created:
                self.stdout.write(f'  Created ProgrammeUnit: {bba.code} - {unit.code} (Level {level_num})')
    
    def seed_categories(self):
        """Seed document categories."""
        categories = [
            ('past_paper', 'Past Paper', 'Previous examination papers'),
            ('lecture_notes', 'Lecture Notes', 'Class lecture materials'),
            ('cat', 'CAT', 'Continuous Assessment Tests'),
            ('assignment', 'Assignment', 'Course assignments'),
            ('slides', 'Slides', 'Presentation slides'),
            ('research', 'Research', 'Research papers and projects'),
            ('book', 'Book', 'Textbooks and reference materials'),
            ('project', 'Project', 'Course and final year projects'),
            ('laboratory', 'Laboratory', 'Lab manuals and reports'),
            ('tutorial', 'Tutorial', 'Tutorial materials'),
            ('exam', 'Exam', 'Examination materials'),
            ('syllabus', 'Syllabus', 'Course syllabi'),
            ('other', 'Other', 'Other document types'),
        ]
        
        for code, name, description in categories:
            obj, created = Category.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'description': description,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'  Created Category: {name}')

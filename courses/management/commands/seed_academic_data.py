from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta
from courses.models import Faculty, Department, Course, Year, CourseAcademicUnit
from documents.academic.models import AcademicYear, Semester, AcademicUnit
from documents.documents.models import Category


class Command(BaseCommand):
    help = 'Seed academic data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Starting to seed academic data...')
        
        with transaction.atomic():
            self.seed_faculties()
            self.seed_departments()
            self.seed_courses()
            self.seed_years()
            self.seed_academic_years()
            self.seed_semesters()
            self.seed_academic_units()
            self.seed_categories()
            self.seed_course_academic_units()
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded academic data'))

    def seed_faculties(self):
        self.stdout.write('Seeding faculties...')
        faculties_data = [
            {'code': 'SCI', 'name': 'Faculty of Science', 'description': 'Faculty of Science and Technology'},
            {'code': 'ENG', 'name': 'Faculty of Engineering', 'description': 'Faculty of Engineering and Technology'},
            {'code': 'BUS', 'name': 'Faculty of Business', 'description': 'Faculty of Business and Economics'},
            {'code': 'ART', 'name': 'Faculty of Arts', 'description': 'Faculty of Arts and Social Sciences'},
        ]
        
        for data in faculties_data:
            Faculty.objects.get_or_create(code=data['code'], defaults=data)
        
        self.stdout.write(f'Created {len(faculties_data)} faculties')

    def seed_departments(self):
        self.stdout.write('Seeding departments...')
        departments_data = [
            {'code': 'CS', 'name': 'Computer Science', 'faculty_code': 'SCI', 'description': 'Department of Computer Science'},
            {'code': 'MATH', 'name': 'Mathematics', 'faculty_code': 'SCI', 'description': 'Department of Mathematics'},
            {'code': 'PHY', 'name': 'Physics', 'faculty_code': 'SCI', 'description': 'Department of Physics'},
            {'code': 'CHEM', 'name': 'Chemistry', 'faculty_code': 'SCI', 'description': 'Department of Chemistry'},
            {'code': 'CIV', 'name': 'Civil Engineering', 'faculty_code': 'ENG', 'description': 'Department of Civil Engineering'},
            {'code': 'MECH', 'name': 'Mechanical Engineering', 'faculty_code': 'ENG', 'description': 'Department of Mechanical Engineering'},
            {'code': 'ELEC', 'name': 'Electrical Engineering', 'faculty_code': 'ENG', 'description': 'Department of Electrical Engineering'},
            {'code': 'ACC', 'name': 'Accounting', 'faculty_code': 'BUS', 'description': 'Department of Accounting'},
            {'code': 'ECON', 'name': 'Economics', 'faculty_code': 'BUS', 'description': 'Department of Economics'},
        ]
        
        for data in departments_data:
            faculty = Faculty.objects.get(code=data.pop('faculty_code'))
            Department.objects.get_or_create(code=data['code'], defaults={**data, 'faculty': faculty})
        
        self.stdout.write(f'Created {len(departments_data)} departments')

    def seed_courses(self):
        self.stdout.write('Seeding courses...')
        courses_data = [
            {'code': 'BSC-CS', 'name': 'BSc Computer Science', 'department_code': 'CS', 'degree_type': 'Bachelor', 'duration_years': 4},
            {'code': 'BSC-MATH', 'name': 'BSc Mathematics', 'department_code': 'MATH', 'degree_type': 'Bachelor', 'duration_years': 4},
            {'code': 'BSC-PHY', 'name': 'BSc Physics', 'department_code': 'PHY', 'degree_type': 'Bachelor', 'duration_years': 4},
            {'code': 'BSC-CHEM', 'name': 'BSc Chemistry', 'department_code': 'CHEM', 'degree_type': 'Bachelor', 'duration_years': 4},
            {'code': 'BSC-CIV', 'name': 'BSc Civil Engineering', 'department_code': 'CIV', 'degree_type': 'Bachelor', 'duration_years': 5},
            {'code': 'BSC-MECH', 'name': 'BSc Mechanical Engineering', 'department_code': 'MECH', 'degree_type': 'Bachelor', 'duration_years': 5},
            {'code': 'BSC-ELEC', 'name': 'BSc Electrical Engineering', 'department_code': 'ELEC', 'degree_type': 'Bachelor', 'duration_years': 5},
            {'code': 'BSC-ACC', 'name': 'BSc Accounting', 'department_code': 'ACC', 'degree_type': 'Bachelor', 'duration_years': 4},
            {'code': 'BSC-ECON', 'name': 'BSc Economics', 'department_code': 'ECON', 'degree_type': 'Bachelor', 'duration_years': 4},
            {'code': 'BSC-IT', 'name': 'BSc Information Technology', 'department_code': 'CS', 'degree_type': 'Bachelor', 'duration_years': 4},
            {'code': 'BSC-COMP', 'name': 'BSc Computer Education', 'department_code': 'CS', 'degree_type': 'Bachelor', 'duration_years': 4},
        ]
        
        for data in courses_data:
            department = Department.objects.get(code=data.pop('department_code'))
            Course.objects.get_or_create(code=data['code'], defaults={**data, 'department': department})
        
        self.stdout.write(f'Created {len(courses_data)} courses')

    def seed_years(self):
        self.stdout.write('Seeding student years...')
        courses = Course.objects.all()
        
        for course in courses:
            for level in range(1, course.duration_years + 1):
                Year.objects.get_or_create(course=course, level=level)
        
        self.stdout.write(f'Created student years for {courses.count()} courses')

    def seed_academic_years(self):
        self.stdout.write('Seeding academic years...')
        current_year = date.today().year
        
        academic_years_data = [
            {'code': f'{current_year}/{current_year+1}', 'name': f'{current_year}/{current_year+1}', 'start_date': date(current_year, 9, 1), 'end_date': date(current_year+1, 8, 31), 'is_current': True},
            {'code': f'{current_year-1}/{current_year}', 'name': f'{current_year-1}/{current_year}', 'start_date': date(current_year-1, 9, 1), 'end_date': date(current_year, 8, 31), 'is_current': False},
            {'code': f'{current_year-2}/{current_year-1}', 'name': f'{current_year-2}/{current_year-1}', 'start_date': date(current_year-2, 9, 1), 'end_date': date(current_year-1, 8, 31), 'is_current': False},
        ]
        
        for data in academic_years_data:
            AcademicYear.objects.get_or_create(code=data['code'], defaults=data)
        
        self.stdout.write(f'Created {len(academic_years_data)} academic years')

    def seed_semesters(self):
        self.stdout.write('Seeding semesters...')
        current_academic_year = AcademicYear.objects.filter(is_current=True).first()
        
        if not current_academic_year:
            current_academic_year = AcademicYear.objects.first()
        
        if current_academic_year:
            semesters_data = [
                {'number': 1, 'academic_year': current_academic_year, 'start_date': current_academic_year.start_date, 'end_date': current_academic_year.start_date + timedelta(days=120), 'is_current': True},
                {'number': 2, 'academic_year': current_academic_year, 'start_date': current_academic_year.start_date + timedelta(days=150), 'end_date': current_academic_year.start_date + timedelta(days=270), 'is_current': False},
                {'number': 3, 'academic_year': current_academic_year, 'start_date': current_academic_year.start_date + timedelta(days=300), 'end_date': current_academic_year.end_date, 'is_current': False},
            ]
            
            for data in semesters_data:
                Semester.objects.get_or_create(number=data['number'], academic_year=data['academic_year'], defaults=data)
        
        self.stdout.write('Created semesters')

    def seed_academic_units(self):
        self.stdout.write('Seeding academic units...')
        academic_units_data = [
            {'code': 'CSC101', 'name': 'Introduction to Computing', 'credit_hours': 3},
            {'code': 'CSC102', 'name': 'Programming Fundamentals', 'credit_hours': 4},
            {'code': 'CSC221', 'name': 'Database Systems', 'credit_hours': 3},
            {'code': 'CSC222', 'name': 'Data Structures and Algorithms', 'credit_hours': 4},
            {'code': 'CSC311', 'name': 'Operating Systems', 'credit_hours': 3},
            {'code': 'CSC312', 'name': 'Computer Networks', 'credit_hours': 3},
            {'code': 'CSC421', 'name': 'Software Engineering', 'credit_hours': 3},
            {'code': 'CSC422', 'name': 'Artificial Intelligence', 'credit_hours': 3},
            {'code': 'MATH101', 'name': 'Calculus I', 'credit_hours': 4},
            {'code': 'MATH102', 'name': 'Linear Algebra', 'credit_hours': 3},
            {'code': 'MATH201', 'name': 'Calculus II', 'credit_hours': 4},
            {'code': 'MATH202', 'name': 'Differential Equations', 'credit_hours': 3},
            {'code': 'PHY101', 'name': 'Mechanics', 'credit_hours': 3},
            {'code': 'PHY102', 'name': 'Electricity and Magnetism', 'credit_hours': 3},
            {'code': 'CHEM101', 'name': 'General Chemistry', 'credit_hours': 3},
            {'code': 'CHEM102', 'name': 'Organic Chemistry', 'credit_hours': 3},
            {'code': 'IT101', 'name': 'Introduction to IT', 'credit_hours': 3},
            {'code': 'IT201', 'name': 'Web Development', 'credit_hours': 3},
            {'code': 'IT301', 'name': 'Network Security', 'credit_hours': 3},
            {'code': 'COMP101', 'name': 'Educational Technology', 'credit_hours': 3},
            {'code': 'COMP201', 'name': 'Computer Literacy', 'credit_hours': 3},
            {'code': 'COMP301', 'name': 'ICT in Education', 'credit_hours': 3},
        ]
        
        for data in academic_units_data:
            AcademicUnit.objects.get_or_create(code=data['code'], defaults=data)
        
        self.stdout.write(f'Created {len(academic_units_data)} academic units')

    def seed_categories(self):
        self.stdout.write('Seeding document categories...')
        categories_data = [
            {'code': 'past_paper', 'name': 'Past Paper', 'description': 'Previous exam papers', 'icon': 'bi-file-earmark-text'},
            {'code': 'lecture_notes', 'name': 'Lecture Notes', 'description': 'Class lecture materials', 'icon': 'bi-journal-text'},
            {'code': 'cat', 'name': 'CAT', 'description': 'Continuous Assessment Tests', 'icon': 'bi-clipboard-check'},
            {'code': 'assignment', 'name': 'Assignment', 'description': 'Course assignments', 'icon': 'bi-pencil-square'},
            {'code': 'slides', 'name': 'Slides', 'description': 'Presentation slides', 'icon': 'bi-easel'},
            {'code': 'research', 'name': 'Research', 'description': 'Research papers and projects', 'icon': 'bi-search'},
            {'code': 'book', 'name': 'Book', 'description': 'Textbooks and reference materials', 'icon': 'bi-book'},
            {'code': 'project', 'name': 'Project', 'description': 'Course projects', 'icon': 'bi-diagram-3'},
            {'code': 'laboratory', 'name': 'Laboratory', 'description': 'Lab manuals and reports', 'icon': 'bi-flask'},
            {'code': 'tutorial', 'name': 'Tutorial', 'description': 'Tutorial materials', 'icon': 'bi-lightbulb'},
            {'code': 'exam', 'name': 'Exam', 'description': 'Exam materials', 'icon': 'bi-file-earmark-check'},
            {'code': 'syllabus', 'name': 'Syllabus', 'description': 'Course syllabi', 'icon': 'bi-list-check'},
            {'code': 'other', 'name': 'Other', 'description': 'Other documents', 'icon': 'bi-file-earmark'},
        ]
        
        for data in categories_data:
            Category.objects.get_or_create(code=data['code'], defaults=data)
        
        self.stdout.write(f'Created {len(categories_data)} categories')

    def seed_course_academic_units(self):
        self.stdout.write('Seeding course-academic unit relationships...')
        
        # Get current semester
        current_semester = Semester.objects.filter(is_current=True).first()
        if not current_semester:
            current_semester = Semester.objects.first()
        
        if not current_semester:
            self.stdout.write(self.style.WARNING('No semesters found. Skipping course-academic unit relationships.'))
            return
        
        # Define which units are offered in which courses at which year level
        course_unit_mappings = [
            # BSc Computer Science
            {'course_code': 'BSC-CS', 'unit_code': 'CSC101', 'year_level': 1, 'is_core': True},
            {'course_code': 'BSC-CS', 'unit_code': 'CSC102', 'year_level': 1, 'is_core': True},
            {'course_code': 'BSC-CS', 'unit_code': 'MATH101', 'year_level': 1, 'is_core': True},
            {'course_code': 'BSC-CS', 'unit_code': 'MATH102', 'year_level': 1, 'is_core': True},
            {'course_code': 'BSC-CS', 'unit_code': 'CSC221', 'year_level': 2, 'is_core': True},
            {'course_code': 'BSC-CS', 'unit_code': 'CSC222', 'year_level': 2, 'is_core': True},
            {'course_code': 'BSC-CS', 'unit_code': 'MATH201', 'year_level': 2, 'is_core': True},
            {'course_code': 'BSC-CS', 'unit_code': 'CSC311', 'year_level': 3, 'is_core': True},
            {'course_code': 'BSC-CS', 'unit_code': 'CSC312', 'year_level': 3, 'is_core': True},
            {'course_code': 'BSC-CS', 'unit_code': 'CSC421', 'year_level': 4, 'is_core': True},
            {'course_code': 'BSC-CS', 'unit_code': 'CSC422', 'year_level': 4, 'is_core': True},
            
            # BSc Information Technology (shares some units with CS)
            {'course_code': 'BSC-IT', 'unit_code': 'CSC101', 'year_level': 1, 'is_core': True},
            {'course_code': 'BSC-IT', 'unit_code': 'IT101', 'year_level': 1, 'is_core': True},
            {'course_code': 'BSC-IT', 'unit_code': 'MATH101', 'year_level': 1, 'is_core': True},
            {'course_code': 'BSC-IT', 'unit_code': 'CSC221', 'year_level': 2, 'is_core': True},
            {'course_code': 'BSC-IT', 'unit_code': 'IT201', 'year_level': 2, 'is_core': True},
            {'course_code': 'BSC-IT', 'unit_code': 'CSC311', 'year_level': 3, 'is_core': True},
            {'course_code': 'BSC-IT', 'unit_code': 'IT301', 'year_level': 3, 'is_core': True},
            
            # BSc Computer Education (shares some units with CS)
            {'course_code': 'BSC-COMP', 'unit_code': 'CSC101', 'year_level': 1, 'is_core': True},
            {'course_code': 'BSC-COMP', 'unit_code': 'COMP101', 'year_level': 1, 'is_core': True},
            {'course_code': 'BSC-COMP', 'unit_code': 'MATH101', 'year_level': 1, 'is_core': True},
            {'course_code': 'BSC-COMP', 'unit_code': 'CSC221', 'year_level': 2, 'is_core': True},
            {'course_code': 'BSC-COMP', 'unit_code': 'COMP201', 'year_level': 2, 'is_core': True},
            {'course_code': 'BSC-COMP', 'unit_code': 'CSC311', 'year_level': 3, 'is_core': True},
            {'course_code': 'BSC-COMP', 'unit_code': 'COMP301', 'year_level': 3, 'is_core': True},
        ]
        
        created_count = 0
        for mapping in course_unit_mappings:
            try:
                course = Course.objects.get(code=mapping['course_code'])
                academic_unit = AcademicUnit.objects.get(code=mapping['unit_code'])
                year_level = Year.objects.get(course=course, level=mapping['year_level'])
                
                CourseAcademicUnit.objects.get_or_create(
                    course=course,
                    academic_unit=academic_unit,
                    year_level=year_level,
                    semester=current_semester,
                    defaults={'is_core': mapping.get('is_core', True), 'is_elective': mapping.get('is_elective', False)}
                )
                created_count += 1
            except (Course.DoesNotExist, AcademicUnit.DoesNotExist, Year.DoesNotExist) as e:
                self.stdout.write(self.style.WARNING(f'Skipping mapping {mapping}: {e}'))
        
        self.stdout.write(f'Created {created_count} course-academic unit relationships')

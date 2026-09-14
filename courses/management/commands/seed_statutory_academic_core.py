from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from courses.models import (
    School,
    Department,
    Programme,
    OfficialSchoolCode,
    AcademicLevelType,
)


class Command(BaseCommand):
    help = "Seeds Pwani University Schools, Departments, and Programmes in strict compliance with the Academic Audit."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initiating statutory Pwani University academic core seed..."))

        # -------------------------------------------------------------
        # 1. SEED STATUTORY SCHOOLS
        # -------------------------------------------------------------
        schools_data = [
            {"code": OfficialSchoolCode.SEDU, "name": "School of Education"},
            {"code": OfficialSchoolCode.SHSS, "name": "School of Humanities and Social Sciences"},
            {"code": OfficialSchoolCode.SPAS, "name": "School of Pure and Applied Sciences"},
            {"code": OfficialSchoolCode.SAAB, "name": "School of Agricultural Sciences and Agribusiness"},
            {"code": OfficialSchoolCode.SEES, "name": "School of Environmental and Earth Sciences"},
            {"code": OfficialSchoolCode.SHHS, "name": "School of Health and Human Sciences"},
            {"code": OfficialSchoolCode.SBE,  "name": "School of Business and Economics"},
        ]

        school_map = {}
        for s in schools_data:
            obj, created = School.objects.update_or_create(
                code=s["code"],
                defaults={
                    "name": s["name"],
                    "slug": slugify(s["name"]),
                    "is_active": True,
                }
            )
            school_map[s["code"]] = obj

        self.stdout.write(self.style.SUCCESS(f"Validated {len(school_map)} Statutory Schools."))

        # -------------------------------------------------------------
        # 2. SEED OFFICIAL DEPARTMENTS
        # -------------------------------------------------------------
        departments_data = [
            # School of Education (SEDU)
            {"code": "EDCI", "name": "Department of Curriculum Studies and Education Technology", "school": OfficialSchoolCode.SEDU},
            {"code": "EDFE", "name": "Department of Educational Foundations and Policy Studies", "school": OfficialSchoolCode.SEDU},
            {"code": "EDPS", "name": "Department of Educational Psychology and Special Needs", "school": OfficialSchoolCode.SEDU},

            # School of Humanities and Social Sciences (SHSS)
            {"code": "LANG", "name": "Department of Languages, Linguistics and Literature", "school": OfficialSchoolCode.SHSS},
            {"code": "SOCS", "name": "Department of Social Sciences", "school": OfficialSchoolCode.SHSS},
            {"code": "PHIL", "name": "Department of Philosophy and Religious Studies", "school": OfficialSchoolCode.SHSS},

            # School of Pure and Applied Sciences (SPAS)
            {"code": "COMP", "name": "Department of Computing", "school": OfficialSchoolCode.SPAS},
            {"code": "MATH", "name": "Department of Mathematics and Statistics", "school": OfficialSchoolCode.SPAS},
            {"code": "PHYS", "name": "Department of Physics", "school": OfficialSchoolCode.SPAS},
            {"code": "CHEM", "name": "Department of Chemistry", "school": OfficialSchoolCode.SPAS},
            {"code": "BIOS", "name": "Department of Biological Sciences", "school": OfficialSchoolCode.SPAS},
            {"code": "TECH", "name": "Department of Technical and Vocational Trades", "school": OfficialSchoolCode.SPAS},
            {"code": "SPAS-ID", "name": "Department of Multidisciplinary Science Studies", "school": OfficialSchoolCode.SPAS},

            # School of Agricultural Sciences and Agribusiness (SAAB)
            {"code": "AGBM", "name": "Department of Agribusiness and Agricultural Economics", "school": OfficialSchoolCode.SAAB},
            {"code": "CRPS", "name": "Department of Crop Sciences", "school": OfficialSchoolCode.SAAB},
            {"code": "ANIS", "name": "Department of Animal Sciences", "school": OfficialSchoolCode.SAAB},

            # School of Environmental and Earth Sciences (SEES)
            {"code": "ENVS", "name": "Department of Environmental Sciences", "school": OfficialSchoolCode.SEES},
            {"code": "ENVB", "name": "Department of Environmental Studies and Community Development", "school": OfficialSchoolCode.SEES},
            {"code": "MRFS", "name": "Department of Marine and Fisheries Sciences", "school": OfficialSchoolCode.SEES},

            # School of Health and Human Sciences (SHHS)
            {"code": "NURS", "name": "Department of Nursing Sciences", "school": OfficialSchoolCode.SHHS},
            {"code": "PUBH", "name": "Department of Public Health", "school": OfficialSchoolCode.SHHS},
            {"code": "CLNS", "name": "Department of Clinical and Medical Sciences", "school": OfficialSchoolCode.SHHS},
            {"code": "FOOD", "name": "Department of Foods, Nutrition and Dietetics", "school": OfficialSchoolCode.SHHS},

            # School of Business and Economics (SBE)
            {"code": "BUSM", "name": "Department of Business Administration", "school": OfficialSchoolCode.SBE},
            {"code": "FINA", "name": "Department of Finance and Accounting", "school": OfficialSchoolCode.SBE},
            {"code": "ECON", "name": "Department of Economics", "school": OfficialSchoolCode.SBE},
            {"code": "HOSP", "name": "Department of Hospitality and Tourism Management", "school": OfficialSchoolCode.SBE},
        ]

        dept_map = {}
        for d in departments_data:
            school_obj = school_map[d["school"]]
            obj, _ = Department.objects.update_or_create(
                code=d["code"],
                defaults={
                    "name": d["name"],
                    "school": school_obj,
                    "slug": slugify(f"{school_obj.code}-{d['name']}"),
                    "is_active": True,
                }
            )
            dept_map[d["code"]] = obj

        self.stdout.write(self.style.SUCCESS(f"Validated {len(dept_map)} Academic Departments."))

        # -------------------------------------------------------------
        # 3. SEED AUDITED PROGRAMMES
        # Format: (Code, Title, Level, DeptCode, DurationYears)
        # -------------------------------------------------------------
        programmes_dataset = [
            # --- UNDERGRADUATE DEGREES ---
            ("BA-GEN", "Bachelor of Arts", AcademicLevelType.BACHELOR, "SOCS", 4),
            ("BA-GER", "Bachelor of Arts (German)", AcademicLevelType.BACHELOR, "LANG", 4),
            ("BA-ANTH", "Bachelor of Arts in Anthropology", AcademicLevelType.BACHELOR, "SOCS", 4),
            ("BA-CCP", "Bachelor of Arts in Child Care and Protection", AcademicLevelType.BACHELOR, "SOCS", 4),
            ("BA-ECON", "Bachelor of Arts in Economics", AcademicLevelType.BACHELOR, "ECON", 4),
            ("BA-ENG", "Bachelor of Arts in English and Linguistics", AcademicLevelType.BACHELOR, "LANG", 4),
            ("BA-FRN", "Bachelor of Arts in French", AcademicLevelType.BACHELOR, "LANG", 4),
            ("BA-HIST", "Bachelor of Arts in History", AcademicLevelType.BACHELOR, "SOCS", 4),
            ("BA-HISA", "Bachelor of Arts in History and Archaeology", AcademicLevelType.BACHELOR, "SOCS", 4),
            ("BA-ISLM", "Bachelor of Arts in Islamic Studies", AcademicLevelType.BACHELOR, "PHIL", 4),
            ("BA-KISW", "Bachelor of Arts in Kiswahili", AcademicLevelType.BACHELOR, "LANG", 4),
            ("BA-LIT", "Bachelor of Arts in Literature", AcademicLevelType.BACHELOR, "LANG", 4),
            ("BA-PHIL", "Bachelor of Arts in Philosophy", AcademicLevelType.BACHELOR, "PHIL", 4),
            ("BA-POLS", "Bachelor of Arts in Political Science", AcademicLevelType.BACHELOR, "SOCS", 4),
            ("BA-PSYC", "Bachelor of Arts in Psychology", AcademicLevelType.BACHELOR, "SOCS", 4),
            ("BA-RELS", "Bachelor of Arts in Religious Studies", AcademicLevelType.BACHELOR, "PHIL", 4),
            ("BA-SOCI", "Bachelor of Arts in Sociology", AcademicLevelType.BACHELOR, "SOCS", 4),
            ("BA-THEO", "Bachelor of Arts in Theology", AcademicLevelType.BACHELOR, "PHIL", 4),
            ("BA-PLEAD", "Bachelor of Arts Philosophy and Leadership", AcademicLevelType.BACHELOR, "PHIL", 4),
            ("B-COM", "Bachelor of Commerce", AcademicLevelType.BACHELOR, "BUSM", 4),
            ("BED-ARTS", "Bachelor of Education (Arts)", AcademicLevelType.BACHELOR, "EDCI", 4),
            ("BED-COMP", "Bachelor of Education (Computer)", AcademicLevelType.BACHELOR, "EDCI", 4),
            ("BED-SCI", "Bachelor of Education (Science)", AcademicLevelType.BACHELOR, "EDCI", 4),
            ("BED-FRN", "Bachelor of Education Arts (French)", AcademicLevelType.BACHELOR, "EDCI", 4),
            ("BED-ECDE", "Bachelor of Education in Early Childhood Education", AcademicLevelType.BACHELOR, "EDPS", 4),
            ("BED-SNE", "Bachelor of Education in Special Needs Education", AcademicLevelType.BACHELOR, "EDPS", 4),
            ("B-EPM", "Bachelor of Environmental Planning & Management", AcademicLevelType.BACHELOR, "ENVS", 4),
            ("BSC-ENV", "Bachelor of Environmental Science", AcademicLevelType.BACHELOR, "ENVS", 4),
            ("BES-COMD", "Bachelor of Environmental Studies (Community Development)", AcademicLevelType.BACHELOR, "ENVB", 4),
            ("BES-COMM", "Bachelor of Environmental Studies (Community Resource Conservation)", AcademicLevelType.BACHELOR, "ENVB", 4),
            ("BSC-MART", "Bachelor of Maritime Studies", AcademicLevelType.BACHELOR, "MRFS", 4),
            ("MBCHB", "Bachelor of Medicine & Bachelor of Surgery (MB,ChB)", AcademicLevelType.BACHELOR, "CLNS", 6),
            ("BSC-AGED", "Bachelor of Science (Agricultural Education and Extension)", AcademicLevelType.BACHELOR, "CRPS", 4),
            ("BSC-BIOL", "Bachelor of Science (Biology)", AcademicLevelType.BACHELOR, "BIOS", 4),
            ("BSC-GEN", "Bachelor of Science (General)", AcademicLevelType.BACHELOR, "SPAS-ID", 4),
            ("BSC-HTM", "Bachelor of Science (Hospitality & Tourism Management)", AcademicLevelType.BACHELOR, "HOSP", 4),
            ("BSC-AGBM", "Bachelor of Science in Agribusiness Management and Trade", AcademicLevelType.BACHELOR, "AGBM", 4),
            ("BSC-AGRM", "Bachelor of Science in Agricultural Resource Management", AcademicLevelType.BACHELOR, "CRPS", 4),
            ("BSC-AGR", "Bachelor of Science in Agriculture", AcademicLevelType.BACHELOR, "CRPS", 4),
            ("BSC-AGEX", "Bachelor of Science in Agriculture and Extension", AcademicLevelType.BACHELOR, "CRPS", 4),
            ("BSC-ANHP", "Bachelor of Science in Animal Health And Production", AcademicLevelType.BACHELOR, "ANIS", 4),
            ("BSC-ANIS", "Bachelor of Science in Animal Science", AcademicLevelType.BACHELOR, "ANIS", 4),
            ("BSC-BIOC", "Bachelor of Science in Biochemistry", AcademicLevelType.BACHELOR, "BIOS", 4),
            ("BSC-BIOT", "Bachelor of Science in Biotechnology", AcademicLevelType.BACHELOR, "BIOS", 4),
            ("BSC-CHEM", "Bachelor of Science in Chemistry", AcademicLevelType.BACHELOR, "CHEM", 4),
            ("BSC-CS", "Bachelor of Science in Computer Science", AcademicLevelType.BACHELOR, "COMP", 4),
            ("BSC-DAGR", "Bachelor of Science in Dryland Agriculture", AcademicLevelType.BACHELOR, "CRPS", 4),
            ("BSC-ENVH", "Bachelor of Science in Environmental Health", AcademicLevelType.BACHELOR, "PUBH", 4),
            ("BSC-FND", "Bachelor of Science in Foods, Nutrition and Dietetics", AcademicLevelType.BACHELOR, "FOOD", 4),
            ("BSC-GEOG", "Bachelor of Science in Geography", AcademicLevelType.BACHELOR, "ENVS", 4),
            ("BSC-ICHEM", "Bachelor of Science in Industrial Chemistry", AcademicLevelType.BACHELOR, "CHEM", 4),
            ("BSC-MBIO", "Bachelor of Science in Marine Biology & Fisheries", AcademicLevelType.BACHELOR, "MRFS", 4),
            ("BSC-MATH", "Bachelor of Science in Mathematics", AcademicLevelType.BACHELOR, "MATH", 4),
            ("BSC-MICR", "Bachelor of Science in Microbiology", AcademicLevelType.BACHELOR, "BIOS", 4),
            ("BSC-NURS", "Bachelor of Science in Nursing and Public Health", AcademicLevelType.BACHELOR, "NURS", 4),
            ("BSC-PHYS", "Bachelor of Science in Physics", AcademicLevelType.BACHELOR, "PHYS", 4),
            ("BSC-TECT", "Bachelor of Science in Telecommunication and Information Technology", AcademicLevelType.BACHELOR, "COMP", 4),
            ("BSC-ZOOL", "Bachelor of Science in Zoology", AcademicLevelType.BACHELOR, "BIOS", 4),

            # --- POSTGRADUATE DIPLOMA ---
            ("PGDE", "Postgraduate Diploma in Education", AcademicLevelType.POSTGRAD_DIPLOMA, "EDCI", 1),

            # --- DIPLOMAS (TVET & SUB-DEGREE) ---
            ("DIP-PLTM", "Diploma in Poultry Management", AcademicLevelType.DIPLOMA, "ANIS", 2),
            ("DIP-TECH", "Diploma in Technical Training", AcademicLevelType.DIPLOMA, "EDCI", 2),
            ("DIP-AGEX", "Diploma in Agricultural Extension", AcademicLevelType.DIPLOMA, "CRPS", 2),
            ("DIP-AGBM", "Diploma in Agribusiness Management", AcademicLevelType.DIPLOMA, "AGBM", 2),
            ("DIP-ANHL", "Diploma in Animal Health", AcademicLevelType.DIPLOMA, "ANIS", 2),
            ("DIP-ANPR", "Diploma in Animal Production", AcademicLevelType.DIPLOMA, "ANIS", 2),
            ("DIP-AQUA", "Diploma in Aquaculture", AcademicLevelType.DIPLOMA, "MRFS", 2),
            ("DIP-CDSW", "Diploma in Community Development & Social Work", AcademicLevelType.DIPLOMA, "SOCS", 2),
            ("DIP-COMH", "Diploma in Community Health", AcademicLevelType.DIPLOMA, "PUBH", 2),
            ("DIP-CS", "Diploma in Computer Science", AcademicLevelType.DIPLOMA, "COMP", 2),
            ("DIP-COSM", "Diploma in Cosmetology", AcademicLevelType.DIPLOMA, "TECH", 2),
            ("DIP-CPSYC", "Diploma in Counselling Psychology", AcademicLevelType.DIPLOMA, "SOCS", 2),
            ("DIP-ECDE", "Diploma in Early Childhood Development Education", AcademicLevelType.DIPLOMA, "EDPS", 2),
            ("DIP-ELEC", "Diploma in Electrical Installation", AcademicLevelType.DIPLOMA, "TECH", 2),
            ("DIP-ENVT", "Diploma in Environmental Technology", AcademicLevelType.DIPLOMA, "ENVS", 2),
            ("DIP-FDGM", "Diploma in Fashion Design & Garment Making", AcademicLevelType.DIPLOMA, "TECH", 2),
            ("DIP-FIST", "Diploma in Fisheries Technology", AcademicLevelType.DIPLOMA, "MRFS", 2),
            ("DIP-FBP", "Diploma in Food & Beverage Production", AcademicLevelType.DIPLOMA, "HOSP", 2),
            ("DIP-FPT", "Diploma in Food Processing Technology", AcademicLevelType.DIPLOMA, "FOOD", 2),
            ("DIP-HOSM", "Diploma in Hospitality Management", AcademicLevelType.DIPLOMA, "HOSP", 2),
            ("DIP-HRM", "Diploma in Human Resource Management", AcademicLevelType.DIPLOMA, "BUSM", 2),
            ("DIP-ICT", "Diploma in Information Communication Technology", AcademicLevelType.DIPLOMA, "COMP", 2),
            ("DIP-JOUR", "Diploma in Journalism & Media Studies", AcademicLevelType.DIPLOMA, "SOCS", 2),
            ("DIP-LIS", "Diploma in Library & Information Science", AcademicLevelType.DIPLOMA, "EDCI", 2),
            ("DIP-MARE", "Diploma in Marine Engineering", AcademicLevelType.DIPLOMA, "MRFS", 2),
            ("DIP-NUTR", "Diploma in Nutrition & Dietetics", AcademicLevelType.DIPLOMA, "FOOD", 2),
            ("DIP-OFAD", "Diploma in Office Administration", AcademicLevelType.DIPLOMA, "BUSM", 2),
            ("DIP-PLUM", "Diploma in Plumbing", AcademicLevelType.DIPLOMA, "TECH", 2),
            ("DIP-PSCM", "Diploma in Procurement & Supply Chain Management", AcademicLevelType.DIPLOMA, "BUSM", 2),
            ("DIP-PROJ", "Diploma in Project Management", AcademicLevelType.DIPLOMA, "BUSM", 2),
            ("DIP-PUBM", "Diploma in Public Administration", AcademicLevelType.DIPLOMA, "SOCS", 2),
            ("DIP-SMKT", "Diploma in Sales & Marketing", AcademicLevelType.DIPLOMA, "BUSM", 2),
            ("DIP-SECS", "Diploma in Secretarial Studies", AcademicLevelType.DIPLOMA, "BUSM", 2),
            ("DIP-SOCW", "Diploma in Social Work", AcademicLevelType.DIPLOMA, "SOCS", 2),
            ("DIP-SOLR", "Diploma in Solar Installation", AcademicLevelType.DIPLOMA, "TECH", 2),
            ("DIP-TOUR", "Diploma in Tourism Management", AcademicLevelType.DIPLOMA, "HOSP", 2),
            ("DIP-WELD", "Diploma in Welding & Fabrication", AcademicLevelType.DIPLOMA, "TECH", 2),
            ("DIP-CHRM", "Diploma in Christian Ministry", AcademicLevelType.DIPLOMA, "PHIL", 2),

            # --- CRAFT CERTIFICATES ---
            ("CERT-APIC", "Certificate in Apiculture", AcademicLevelType.CRAFT_CERT, "ANIS", 1),
            ("CERT-AGEX", "Certificate in Agricultural Extension", AcademicLevelType.CRAFT_CERT, "CRPS", 1),
            ("CERT-AGBM", "Certificate in Agribusiness Management", AcademicLevelType.CRAFT_CERT, "AGBM", 1),
            ("CERT-ANHL", "Certificate in Animal Health", AcademicLevelType.CRAFT_CERT, "ANIS", 1),
            ("CERT-ANPR", "Certificate in Animal Production", AcademicLevelType.CRAFT_CERT, "ANIS", 1),
            ("CERT-AQUA", "Certificate in Aquaculture", AcademicLevelType.CRAFT_CERT, "MRFS", 1),
            ("CERT-CDSW", "Certificate in Community Development & Social Work", AcademicLevelType.CRAFT_CERT, "SOCS", 1),
            ("CERT-COMH", "Certificate in Community Health", AcademicLevelType.CRAFT_CERT, "PUBH", 1),
            ("CERT-CS", "Certificate in Computer Science", AcademicLevelType.CRAFT_CERT, "COMP", 1),
            ("CERT-COSM", "Certificate in Cosmetology", AcademicLevelType.CRAFT_CERT, "TECH", 1),
            ("CERT-CPSYC", "Certificate in Counselling Psychology", AcademicLevelType.CRAFT_CERT, "SOCS", 1),
            ("CERT-ECDE", "Certificate in Early Childhood Development Education", AcademicLevelType.CRAFT_CERT, "EDPS", 1),
            ("CERT-ELEC", "Certificate in Electrical Installation", AcademicLevelType.CRAFT_CERT, "TECH", 1),
            ("CERT-ENVT", "Certificate in Environmental Technology", AcademicLevelType.CRAFT_CERT, "ENVS", 1),
            ("CERT-FDGM", "Certificate in Fashion Design & Garment Making", AcademicLevelType.CRAFT_CERT, "TECH", 1),
            ("CERT-FIST", "Certificate in Fisheries Technology", AcademicLevelType.CRAFT_CERT, "MRFS", 1),
            ("CERT-FBP", "Certificate in Food & Beverage Production", AcademicLevelType.CRAFT_CERT, "HOSP", 1),
            ("CERT-FPT", "Certificate in Food Processing Technology", AcademicLevelType.CRAFT_CERT, "FOOD", 1),
            ("CERT-HOSM", "Certificate in Hospitality Management", AcademicLevelType.CRAFT_CERT, "HOSP", 1),
            ("CERT-HRM", "Certificate in Human Resource Management", AcademicLevelType.CRAFT_CERT, "BUSM", 1),
            ("CERT-ICT", "Certificate in ICT", AcademicLevelType.CRAFT_CERT, "COMP", 1),
            ("CERT-JOUR", "Certificate in Journalism & Media Studies", AcademicLevelType.CRAFT_CERT, "SOCS", 1),
            ("CERT-LIS", "Certificate in Library & Information Science", AcademicLevelType.CRAFT_CERT, "EDCI", 1),
            ("CERT-MARE", "Certificate in Marine Engineering", AcademicLevelType.CRAFT_CERT, "MRFS", 1),
            ("CERT-NUTR", "Certificate in Nutrition & Dietetics", AcademicLevelType.CRAFT_CERT, "FOOD", 1),
            ("CERT-OFAD", "Certificate in Office Administration", AcademicLevelType.CRAFT_CERT, "BUSM", 1),
            ("CERT-PLUM", "Certificate in Plumbing", AcademicLevelType.CRAFT_CERT, "TECH", 1),
            ("CERT-PSCM", "Certificate in Procurement & Supply Chain Management", AcademicLevelType.CRAFT_CERT, "BUSM", 1),
            ("CERT-PROJ", "Certificate in Project Management", AcademicLevelType.CRAFT_CERT, "BUSM", 1),
            ("CERT-PUBM", "Certificate in Public Administration", AcademicLevelType.CRAFT_CERT, "SOCS", 1),
            ("CERT-SMKT", "Certificate in Sales & Marketing", AcademicLevelType.CRAFT_CERT, "BUSM", 1),
            ("CERT-SECS", "Certificate in Secretarial Studies", AcademicLevelType.CRAFT_CERT, "BUSM", 1),
            ("CERT-SOCW", "Certificate in Social Work", AcademicLevelType.CRAFT_CERT, "SOCS", 1),
            ("CERT-SOLR", "Certificate in Solar Installation", AcademicLevelType.CRAFT_CERT, "TECH", 1),
            ("CERT-TOUR", "Certificate in Tourism Management", AcademicLevelType.CRAFT_CERT, "HOSP", 1),
            ("CERT-CHRM", "Certificate in Christian Ministry", AcademicLevelType.CRAFT_CERT, "PHIL", 1),

            # --- ARTISAN CERTIFICATES (TVET) ---
            ("ART-PLTM", "Artisan in Poultry Management", AcademicLevelType.ARTISAN, "ANIS", 1),
            ("ART-APIC", "Artisan in Apiculture", AcademicLevelType.ARTISAN, "ANIS", 1),
            ("ART-AGEX", "Artisan in Agricultural Extension", AcademicLevelType.ARTISAN, "CRPS", 1),
            ("ART-AGBM", "Artisan in Agribusiness Management", AcademicLevelType.ARTISAN, "AGBM", 1),
            ("ART-ANHL", "Artisan in Animal Health", AcademicLevelType.ARTISAN, "ANIS", 1),
            ("ART-ANPR", "Artisan in Animal Production", AcademicLevelType.ARTISAN, "ANIS", 1),
            ("ART-AQUA", "Artisan in Aquaculture", AcademicLevelType.ARTISAN, "MRFS", 1),
            ("ART-CDSW", "Artisan in Community Development & Social Work", AcademicLevelType.ARTISAN, "SOCS", 1),
            ("ART-COMH", "Artisan in Community Health", AcademicLevelType.ARTISAN, "PUBH", 1),
            ("ART-ICT", "Artisan in Information Communication Technology", AcademicLevelType.ARTISAN, "COMP", 1),
            ("ART-CHRM", "Artisan in Christian Ministry", AcademicLevelType.ARTISAN, "PHIL", 1),

            # --- MASTERS ---
            ("MA-ALIN", "Master of Arts in Applied Linguistics", AcademicLevelType.MASTERS, "LANG", 2),
            ("MA-CPSYC", "Master of Arts in Counselling Psychology", AcademicLevelType.MASTERS, "SOCS", 2),
            ("MA-ECMT", "Master of Arts in Econometrics", AcademicLevelType.MASTERS, "ECON", 2),
            ("MA-ECON", "Master of Arts in Economics", AcademicLevelType.MASTERS, "ECON", 2),
            ("MA-ENGL", "Master of Arts in English and Linguistics", AcademicLevelType.MASTERS, "LANG", 2),
            ("MA-FLAN", "Master of Arts in Foreign Languages", AcademicLevelType.MASTERS, "LANG", 2),
            ("MA-HGARC", "Master of Arts in History, Government and Archaeology", AcademicLevelType.MASTERS, "SOCS", 2),
            ("MA-KISW", "Master of Arts in Kiswahili", AcademicLevelType.MASTERS, "LANG", 2),
            ("MA-LIT", "Master of Arts in Literature", AcademicLevelType.MASTERS, "LANG", 2),
            ("MA-PHIL", "Master of Arts in Philosophy", AcademicLevelType.MASTERS, "PHIL", 2),
            ("MA-RELS", "Master of Arts in Religious Studies", AcademicLevelType.MASTERS, "PHIL", 2),
            ("MA-SOCI", "Master of Arts in Sociology", AcademicLevelType.MASTERS, "SOCS", 2),
            ("MBA", "Master of Business Administration", AcademicLevelType.MASTERS, "BUSM", 2),
            ("M-COMM", "Master of Communication and Media", AcademicLevelType.MASTERS, "SOCS", 2),
            ("M-ED", "Master in Education", AcademicLevelType.MASTERS, "EDCI", 2),
            ("MED-SNE", "Master of Education in Special Needs Education", AcademicLevelType.MASTERS, "EDPS", 2),
            ("M-EPM", "Master of Environmental Planning and Management", AcademicLevelType.MASTERS, "ENVS", 2),
            ("MSC-ESCD", "Master of Science in Environmental Studies (Community Development)", AcademicLevelType.MASTERS, "ENVB", 2),
            ("MSC-AGBM", "Master of Science in Agribusiness", AcademicLevelType.MASTERS, "AGBM", 2),
            ("MSC-AGEC", "Master of Science in Agricultural Economics", AcademicLevelType.MASTERS, "AGBM", 2),
            ("MSC-AGED", "Master of Science in Agricultural Education", AcademicLevelType.MASTERS, "CRPS", 2),
            ("MSC-AGEX", "Master of Science in Agricultural Extension", AcademicLevelType.MASTERS, "CRPS", 2),
            ("MSC-FISH", "Master of Science in Fisheries", AcademicLevelType.MASTERS, "MRFS", 2),
            ("MSC-ISFM", "Master of Science in Integrated Soil Fertility Management", AcademicLevelType.MASTERS, "CRPS", 2),
            ("MSC-LWM", "Master of Science in Land and Water Management", AcademicLevelType.MASTERS, "CRPS", 2),
            ("MSC-LIVS", "Master of Science in Livestock Science", AcademicLevelType.MASTERS, "ANIS", 2),
            ("MSC-MBF", "Master of Science in Marine Biology and Fisheries", AcademicLevelType.MASTERS, "MRFS", 2),
            ("M-PAS", "Master in Pure and Applied Sciences", AcademicLevelType.MASTERS, "SPAS-ID", 2),
            ("MSC-AACH", "Master of Science in Applied Analytical Chemistry", AcademicLevelType.MASTERS, "CHEM", 2),
            ("MSC-BIOC", "Master of Science in Biochemistry", AcademicLevelType.MASTERS, "BIOS", 2),
            ("MSC-BINF", "Master of Science in Bioinformatics", AcademicLevelType.MASTERS, "COMP", 2),
            ("MSC-BIOT", "Master of Science in Biotechnology", AcademicLevelType.MASTERS, "BIOS", 2),
            ("MSC-CHEM", "Master of Science in Chemistry", AcademicLevelType.MASTERS, "CHEM", 2),
            ("MSC-FIN", "Master of Science in Finance", AcademicLevelType.MASTERS, "FINA", 2),
            ("MSC-FND", "Master of Science in Foods, Nutrition and Dietetics", AcademicLevelType.MASTERS, "FOOD", 2),
            ("MSC-GEOG", "Master of Science in Geography", AcademicLevelType.MASTERS, "ENVS", 2),
            ("MSC-HTM", "Master of Science in Hospitality and Tourism Management", AcademicLevelType.MASTERS, "HOSP", 2),
            ("MSC-HRM", "Master of Science in Human Resource Management", AcademicLevelType.MASTERS, "BUSM", 2),
            ("MSC-IMMU", "Master of Science in Immunology", AcademicLevelType.MASTERS, "BIOS", 2),
            ("MSC-ICHEM", "Master of Science in Industrial Chemistry", AcademicLevelType.MASTERS, "CHEM", 2),
            ("MSC-MBIOC", "Master of Science in Medical Biochemistry", AcademicLevelType.MASTERS, "BIOS", 2),
            ("MSC-MICR", "Master of Science in Microbiology", AcademicLevelType.MASTERS, "BIOS", 2),
            ("MSC-PMIS", "Master of Science in Plant Microbial Sciences", AcademicLevelType.MASTERS, "BIOS", 2),
            ("MSC-PPAT", "Master of Science in Plant Pathology", AcademicLevelType.MASTERS, "CRPS", 2),
            ("MSC-ZOOL", "Master of Science in Zoology", AcademicLevelType.MASTERS, "BIOS", 2),
            ("MSC-ZOOS", "Master of Science in Zoological Sciences", AcademicLevelType.MASTERS, "BIOS", 2),

            # --- DOCTORATE (PHD) ---
            ("PHD-ANIS", "Doctor of Philosophy in Animal Sciences", AcademicLevelType.PHD, "ANIS", 3),
            ("PHD-BCBT", "Doctor of Philosophy Biochemistry and Biotechnology", AcademicLevelType.PHD, "BIOS", 3),
            ("PHD-BOTS", "Doctor of Philosophy Botanical Sciences", AcademicLevelType.PHD, "BIOS", 3),
            ("PHD-CHEM", "Doctor of Philosophy Chemistry (Analytical, Organic, Inorganic, Physical)", AcademicLevelType.PHD, "CHEM", 3),
            ("PHD-DRM", "Doctor of Philosophy in Dryland Resource Management", AcademicLevelType.PHD, "CRPS", 3),
            ("PHD-ENVS", "Doctor of Philosophy in Environmental Studies", AcademicLevelType.PHD, "ENVS", 3),
            ("PHD-ESCD", "Doctor of Philosophy in Environmental Studies (Community Development)", AcademicLevelType.PHD, "ENVB", 3),
            ("PHD-ISFM", "Doctor of Philosophy in Integrated Soil Fertility Management", AcademicLevelType.PHD, "CRPS", 3),
            ("PHD-MRFS", "Doctor of Philosophy Marine and Fisheries", AcademicLevelType.PHD, "MRFS", 3),
            ("PHD-MATH", "Doctor of Philosophy Mathematics", AcademicLevelType.PHD, "MATH", 3),
        ]

        created_count = 0
        updated_count = 0

        for code, name, level, dept_code, duration in programmes_dataset:
            dept_obj = dept_map[dept_code]
            school_obj = dept_obj.school

            prog, created = Programme.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "academic_level": level,
                    "department": dept_obj,
                    "school": school_obj,
                    "duration_years": duration,
                    "slug": slugify(f"{code}-{name}"),
                    "is_active": True,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeding completed successfully: {created_count} inserted, {updated_count} updated across {len(programmes_dataset)} total programmes."
            )
        )

        # -------------------------------------------------------------
        # 4. SYNC TO DOCUMENTS DOMAIN (FOR REGISTRATION FORM & GROUPS)
        # -------------------------------------------------------------
        from documents.academic.models import (
            Faculty as DocFaculty,
            School as DocSchool,
            Department as DocDepartment,
            Programme as DocProgramme,
            AcademicLevel,
            AcademicYear,
            Semester,
        )
        from datetime import date

        # Ensure Academic Levels exist for registration cascading dropdowns
        levels_data = [
            (1, 'Year 1', 'First year of study'),
            (2, 'Year 2', 'Second year of study'),
            (3, 'Year 3', 'Third year of study'),
            (4, 'Year 4', 'Fourth year of study'),
            (5, 'Year 5', 'Fifth year of study'),
            (6, 'Year 6', 'Sixth year of study'),
            (7, 'Masters', 'Postgraduate masters level'),
            (8, 'PhD', 'Doctoral level'),
        ]
        for lvl_num, lvl_name, lvl_desc in levels_data:
            AcademicLevel.objects.update_or_create(
                level=lvl_num,
                defaults={'name': lvl_name, 'description': lvl_desc, 'is_active': True}
            )

        # Ensure Academic Years & Semesters exist for registration cascading dropdowns
        academic_years_config = [
            ("2024/2025", False),
            ("2025/2026", False),
            ("2026/2027", True),
        ]
        for yr_code, is_curr in academic_years_config:
            start_yr = int(yr_code.split('/')[0])
            end_yr = int(yr_code.split('/')[1])
            acad_yr, _ = AcademicYear.objects.update_or_create(
                code=yr_code,
                defaults={
                    'name': yr_code,
                    'start_date': date(start_yr, 9, 1),
                    'end_date': date(end_yr, 8, 31),
                    'is_current': is_curr,
                }
            )
            for sem_num in [1, 2]:
                Semester.objects.update_or_create(
                    number=sem_num,
                    academic_year=acad_yr,
                    defaults={
                        'start_date': date(start_yr, 9, 1) if sem_num == 1 else date(end_yr, 1, 1),
                        'end_date': date(start_yr, 12, 31) if sem_num == 1 else date(end_yr, 5, 31),
                        'is_current': is_curr and sem_num == 1,
                    }
                )

        pu_faculty, _ = DocFaculty.objects.get_or_create(
            code="PU",
            defaults={"name": "Pwani University Faculties", "description": "Pwani University Statutory Body"}
        )

        doc_school_map = {}
        for s in schools_data:
            doc_s, _ = DocSchool.objects.update_or_create(
                code=s["code"],
                defaults={
                    "name": s["name"],
                    "faculty": pu_faculty,
                    "slug": slugify(s["name"]),
                }
            )
            doc_school_map[s["code"]] = doc_s

        doc_dept_map = {}
        for d in departments_data:
            doc_school_obj = doc_school_map[d["school"]]
            doc_d, _ = DocDepartment.objects.update_or_create(
                code=d["code"],
                defaults={
                    "name": d["name"],
                    "school": doc_school_obj,
                    "slug": slugify(f"{doc_school_obj.code}-{d['name']}"),
                }
            )
            doc_dept_map[d["code"]] = doc_d

        doc_prog_count = 0
        for code, name, level, dept_code, duration in programmes_dataset:
            doc_dept_obj = doc_dept_map[dept_code]
            DocProgramme.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "department": doc_dept_obj,
                    "degree_type": str(level),
                    "duration_years": duration,
                    "slug": slugify(f"{code}-{name}"),
                    "is_active": True,
                }
            )
            doc_prog_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronized {doc_prog_count} programmes, academic levels, years, and semesters into documents domain for registration form."
            )
        )

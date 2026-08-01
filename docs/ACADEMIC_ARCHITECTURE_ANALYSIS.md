# Academic Architecture Analysis

## Current State Assessment

### Existing Models

#### courses/models.py
- **Faculty**: Represents university faculties
- **Department**: Represents departments within faculties
- **School**: Legacy model (deprecated)
- **Course**: Represents academic programmes (e.g., BSc Computer Science)
- **Year**: Student year of study (1-4), linked to Course
- **Unit**: Legacy model (deprecated)
- **CourseAcademicUnit**: Junction table linking Course to AcademicUnit

#### documents/academic/models.py
- **AcademicYear**: Academic year (e.g., 2024/2025)
- **Semester**: Belongs to AcademicYear
- **Faculty**: Duplicate of courses.Faculty
- **School**: Belongs to Faculty
- **Department**: Belongs to School
- **Programme**: Belongs to Department (same concept as Course)
- **AcademicUnit**: Shared academic units
- **ProgrammeUnit**: Junction table (Programme + AcademicUnit + Semester)

#### users/models.py
- **User.course**: ForeignKey to Course (old model)
- **User.year**: ForeignKey to Year (old model)
- No references to new academic hierarchy

### Critical Issues

1. **Model Duplication**
   - Faculty exists in both `courses` and `documents.academic`
   - Department exists in both apps with different relationships
   - School has inconsistent implementation

2. **Naming Inconsistency**
   - `Course` vs `Programme` represent the same concept
   - `Year` (student level) vs `AcademicYear` (calendar year) naming confusion

3. **Legacy Models**
   - Old `Unit` model marked deprecated but still present
   - Old `School` model in courses with different structure

4. **Missing Academic Level**
   - No dedicated reusable `AcademicLevel` model
   - `Year` model is tied to specific Course, not reusable
   - Academic levels should be independent entities

5. **Incomplete Curriculum Mapping**
   - `ProgrammeUnit` lacks academic year and level information
   - Cannot determine when units are taught in the curriculum
   - Missing temporal curriculum structure

6. **Outdated User Profile**
   - User still references old Course/Year models
   - No integration with new Programme/AcademicLevel
   - Cannot support personalized recommendations

7. **Document Academic Metadata**
   - `DocumentAcademicUnit` exists but doesn't leverage curriculum
   - No automatic programme inference from unit selection
   - Missing academic level on documents

8. **Inconsistent Hierarchy**
   - courses: Faculty → Department
   - documents: Faculty → School → Department
   - Different relationship chains create confusion

## Required Refactor

### New Academic Hierarchy

```
University (optional, for multi-tenant)
↓
Faculty
↓
School
↓
Department
↓
Programme
↓
AcademicLevel (Year 1, Year 2, etc.)
↓
AcademicYear (2024/2025, 2025/2026)
↓
Semester (Semester 1, Semester 2)
↓
AcademicUnit (shared across programmes)
```

### Key Changes Needed

1. **Consolidate Models**
   - Keep single source of truth for Faculty, School, Department
   - Remove duplicates between courses and documents.academic
   - Deprecate old Course/Year/Unit models gracefully

2. **Create AcademicLevel Model**
   - Independent reusable levels (Year 1, Year 2, etc.)
   - Not tied to specific programmes
   - Can be referenced by documents, users, curriculum

3. **Enhance Curriculum Mapping**
   - Create comprehensive `CurriculumMapping` model
   - Include: Programme, AcademicLevel, AcademicYear, Semester, AcademicUnit
   - Support temporal curriculum changes

4. **Update User Profile**
   - Add references to Programme, AcademicLevel, AcademicYear, Semester
   - Maintain backward compatibility with old fields
   - Support current academic context

5. **Enhance Document Metadata**
   - Add AcademicLevel to DocumentAcademicUnit
   - Enable automatic programme inference from curriculum
   - Support shared unit discovery

6. **Improve Upload Workflow**
   - Select AcademicUnit, AcademicLevel, AcademicYear, Semester, Category
   - Automatically infer compatible programmes
   - Support shared unit visibility

### Migration Strategy

1. **Phase 1**: Create new models alongside existing ones
2. **Phase 2**: Migrate data from old models to new structure
3. **Phase 3**: Update references throughout codebase
4. **Phase 4**: Deprecate old models (keep for backward compatibility)
5. **Phase 5**: Remove deprecated models in future release

## Success Criteria

- Single source of truth for academic entities
- Reusable academic levels across all modules
- Complete curriculum mapping with temporal context
- User profiles integrated with new hierarchy
- Documents leverage curriculum for shared unit discovery
- Upload workflow supports automatic programme inference
- Backward compatibility maintained during transition

# Academic Architecture Documentation

## Overview

This document provides comprehensive documentation of the enhanced academic domain architecture for PwaniNet Document Repository. The architecture implements a normalized, scalable academic hierarchy that accurately models university curriculum structures while maintaining backward compatibility with existing functionality.

## Architecture Goals

1. **Normalization**: Create reusable academic entities independent of specific programmes
2. **Curriculum Mapping**: Explicitly model curriculum structure with temporal context
3. **Shared Units**: Support academic units shared across multiple programmes
4. **Enhanced Profiles**: Expand student academic profiles with current context
5. **Document Metadata**: Enrich document academic metadata for better discovery
6. **Backward Compatibility**: Preserve existing functionality during transition

## Academic Hierarchy

```
University (optional, for multi-tenant support)
└── Faculty
    └── School
        └── Department
            └── Programme
                └── AcademicLevel (Year 1, Year 2, etc.)
                    └── AcademicYear (2024/2025, 2025/2026)
                        └── Semester (Semester 1, Semester 2, Semester 3)
                            └── AcademicUnit (shared across programmes)
```

## Core Models

### AcademicLevel

**Purpose**: Reusable student academic levels independent of specific programmes.

**Fields**:
- `level`: Integer (1-8) representing academic progression
- `name`: Human-readable name (e.g., "Year 1", "Masters", "PhD")
- `description`: Optional description
- `is_active`: Boolean for active status

**Key Design Decisions**:
- Independent entity, not tied to specific programmes
- Supports undergraduate (Years 1-6), Masters (7), and PhD (8) levels
- Reusable across all programmes for consistency
- Enables cross-programme academic level comparisons

**Indexes**:
- `level`: For fast lookup by level number
- `is_active`: For filtering active levels

### AcademicYear

**Purpose**: Represents academic calendar years (e.g., 2024/2025).

**Fields**:
- `code`: Unique identifier (e.g., "2024/2025")
- `name`: Human-readable name
- `start_date`/`end_date`: Date range
- `is_current`: Boolean for current academic year

**Key Design Decisions**:
- Single current academic year enforced via save method
- Supports temporal curriculum changes
- Enables historical document tracking

**Indexes**:
- `code`: For unique lookup
- `is_current`: For finding current year

### Semester

**Purpose**: Represents semesters within academic years.

**Fields**:
- `number`: Integer (1-3) for semester number
- `academic_year`: ForeignKey to AcademicYear
- `start_date`/`end_date`: Date range
- `is_current`: Boolean for current semester

**Key Design Decisions**:
- Supports 3-semester systems
- Single current semester enforced
- Unique constraint on (number, academic_year)

**Indexes**:
- Composite index on (academic_year, number)
- `is_current` for finding current semester

### Faculty

**Purpose**: Top-level academic division.

**Fields**:
- `code`: Unique faculty code
- `name`: Faculty name
- `description`: Optional description
- `slug`: URL-friendly slug

**Key Design Decisions**:
- Single source of truth (consolidated from courses app)
- Supports multi-faculty universities
- Foundation for school hierarchy

### School

**Purpose**: Academic division within faculty.

**Fields**:
- `code`: Unique school code
- `name`: School name
- `faculty`: ForeignKey to Faculty
- `description`: Optional description
- `slug`: URL-friendly slug

**Key Design Decisions**:
- Belongs to Faculty (not Department)
- Enables faculty-level organization
- Consistent structure across all faculties

### Department

**Purpose**: Academic department within school.

**Fields**:
- `code`: Unique department code
- `name`: Department name
- `school`: ForeignKey to School
- `description`: Optional description
- `slug`: URL-friendly slug

**Key Design Decisions**:
- Belongs to School (not Faculty directly)
- Houses programmes
- Provides granular academic organization

### Programme

**Purpose**: Academic programme (e.g., BSc Computer Science).

**Fields**:
- `code`: Unique programme code
- `name`: Programme name
- `department`: ForeignKey to Department
- `duration_years`: Programme duration
- `description`: Optional description
- `is_active`: Boolean for active status
- `slug`: URL-friendly slug

**Key Design Decisions**:
- Replaces legacy Course model
- Belongs to Department
- Supports active/inactive status
- Enables programme-level filtering

### AcademicUnit

**Purpose**: Individual academic units/courses (e.g., CSC101).

**Fields**:
- `code`: Unique unit code (format: XXX###)
- `name`: Unit name
- `description`: Optional description
- `credit_hours`: Credit hours
- `is_active`: Boolean for active status
- `slug`: URL-friendly slug

**Key Design Decisions**:
- Shared across programmes (no direct programme FK)
- Independent entity for reusability
- Supports unit-level filtering
- Regex validation for code format

**Indexes**:
- `code`: For unique lookup
- `slug`: For URL routing
- `is_active`: For filtering active units

### ProgrammeUnit

**Purpose**: Junction table mapping programmes to academic units with full curriculum context.

**Fields**:
- `programme`: ForeignKey to Programme
- `academic_unit`: ForeignKey to AcademicUnit
- `academic_level`: ForeignKey to AcademicLevel
- `academic_year`: ForeignKey to AcademicYear
- `semester`: ForeignKey to Semester
- `is_core`: Boolean for core unit status
- `is_elective`: Boolean for elective unit status

**Key Design Decisions**:
- Many-to-many relationship with full context
- Includes temporal information (academic_year, semester)
- Includes academic level for curriculum structure
- Unique constraint on all 5 fields
- Supports core/elective classification
- Enables shared unit discovery across programmes

**Indexes**:
- Individual indexes on each FK
- Composite index on (programme, academic_level, academic_year, semester)
- Optimized for curriculum queries

**Curriculum Mapping Example**:
```
Programme: BSC Computer Science
├── Year 1 (2024/2025)
│   ├── Semester 1: CSC101, CSC102
│   └── Semester 2: CSC201, CSC202
├── Year 2 (2024/2025)
│   ├── Semester 1: CSC301, CSC302
│   └── Semester 2: CSC401
```

## Document Domain Models

### DocumentAcademicUnit

**Purpose**: Junction table linking documents to academic units with full academic context.

**Fields**:
- `document`: ForeignKey to Document
- `academic_unit`: ForeignKey to AcademicUnit
- `academic_level`: ForeignKey to AcademicLevel
- `semester`: ForeignKey to Semester
- `academic_year`: ForeignKey to AcademicYear
- `is_primary`: Boolean for primary unit status

**Key Design Decisions**:
- Documents can belong to multiple units (shared units)
- Includes full academic context for filtering
- Unique constraint on all 5 fields
- Primary flag for main unit
- Enables shared unit discovery
- Prevents duplicate uploads for shared units

**Indexes**:
- Individual indexes on each FK
- Composite index on (academic_unit, academic_level, academic_year, semester)
- Optimized for document filtering

**Use Cases**:
- Upload: Select unit, level, year, semester
- Search: Filter by any academic dimension
- Discovery: Find documents for shared units
- Recommendations: Match user's academic context

## User Profile Enhancement

### User Model Additions

**New Fields**:
- `programme`: ForeignKey to Programme (replaces legacy course)
- `academic_level`: ForeignKey to AcademicLevel (replaces legacy year)
- `academic_year`: ForeignKey to AcademicYear
- `semester`: ForeignKey to Semester

**Legacy Fields (Preserved)**:
- `course`: ForeignKey to Course (deprecated but kept)
- `year`: ForeignKey to Year (deprecated but kept)

**Key Design Decisions**:
- New fields nullable for gradual migration
- Legacy fields preserved for backward compatibility
- Profile completion checks both new and legacy fields
- Enables personalized recommendations
- Supports current academic context tracking

**Profile Completion Logic**:
```python
@property
def is_profile_complete(self):
    # Check new academic profile first
    if self.programme and self.academic_level:
        return True
    # Fallback to legacy fields for backward compatibility
    return bool(self.course and self.year)
```

## Query Optimization

### Selectors Pattern

**DocumentSelector** provides optimized queries:

1. **get_document_with_relations**: Single query with all relations
   - Uses `select_related` for FKs
   - Uses `prefetch_related` for M2M
   - Uses `only()` to limit fields
   - Minimizes N+1 queries

2. **list_documents_for_home**: Optimized listing
   - Prefetches only necessary academic unit fields
   - Applies student relevance sorting in memory

3. **_apply_student_relevance_sorting**: Personalized ranking
   - Matches user's programme units
   - Boosts for matching academic level
   - Boosts for matching semester
   - Uses optimized queries with `only()`

### Index Strategy

**AcademicLevel**:
- Index on `level` for fast lookup
- Index on `is_active` for filtering

**AcademicYear**:
- Index on `code` for unique lookup
- Index on `is_current` for finding current year

**Semester**:
- Composite index on (academic_year, number)
- Index on `is_current` for finding current semester

**AcademicUnit**:
- Index on `code` for unique lookup
- Index on `slug` for URL routing
- Index on `is_active` for filtering

**ProgrammeUnit**:
- Index on each FK field
- Composite index on (programme, academic_level, academic_year, semester)
- Optimized for curriculum queries

**DocumentAcademicUnit**:
- Index on each FK field
- Composite index on (academic_unit, academic_level, academic_year, semester)
- Optimized for document filtering

## Search and Filtering

### Enhanced Filters

**Academic Filters**:
- `category`: Document category
- `academic_unit`: Specific unit
- `academic_level`: Academic level
- `semester`: Semester
- `academic_year`: Academic year
- `programme`: Programme (via curriculum mapping)
- `school`: School (via department hierarchy)
- `department`: Department (via programme)

**Personalized Filters** (authenticated users):
- `my_programme`: User's current programme
- `my_units`: Units in user's programme
- `my_semester`: User's current semester
- `my_level`: User's current academic level
- `my_academic_year`: User's current academic year

**Filter Implementation**:
- Search service applies filters to both FTS and document queries
- Programme filter uses curriculum mapping to find relevant units
- Personalized filters use user's academic profile
- Supports multiple filter combinations

## Upload Workflow

### Enhanced Upload Form

**New Fields**:
- Academic Unit (required)
- Academic Level (required)
- Academic Year (required)
- Semester (required)
- Category (required)
- Tags (optional)

**Curriculum Integration**:
- Selecting unit + level + year + semester determines compatible programmes
- Documents automatically linked to all programmes offering that unit
- Shared unit discovery enabled
- Prevents duplicate uploads for shared units

**Document Creation**:
```python
DocumentAcademicUnit.objects.create(
    document=document,
    academic_unit_id=academic_unit_id,
    semester_id=semester_id,
    academic_year_id=academic_year_id,
    academic_level_id=academic_level_id,
    is_primary=True
)
```

## Backward Compatibility

### Legacy Model Preservation

**courses.Course**: Kept for existing references
- Mapped to documents.Programme during migration
- Gradual deprecation planned

**courses.Year**: Kept for existing references
- Mapped to documents.AcademicLevel during migration
- Gradual deprecation planned

**User.course**: Kept for existing profiles
- New User.programme field added
- Profile completion checks both
- Migration strategy documented

**User.year**: Kept for existing profiles
- New User.academic_level field added
- Profile completion checks both
- Migration strategy documented

### Migration Strategy

**Phase 1**: Create new models (✓ Completed)
**Phase 2**: Migrate data (Documented, pending execution)
**Phase 3**: Update references (Documented, pending execution)
**Phase 4**: Deprecate legacy (Planned for future release)

**Data Preservation**:
- All existing documents remain accessible
- No data loss during migration
- Legacy fields kept until validation complete
- Rollback plan documented

## Seed Data

### Enhanced Seed Command

**Command**: `python manage.py seed_enhanced_academic_data`

**Seeds**:
- Academic Levels (Year 1-6, Masters, PhD)
- Academic Years (2023/2026)
- Semesters (3 per academic year)
- Faculties (5 faculties)
- Schools (10 schools)
- Departments (15 departments)
- Programmes (20 programmes)
- Academic Units (30+ units)
- Programme Units (curriculum mappings)
- Categories (13 document categories)

**Realistic Data**:
- Based on typical university structure
- Includes shared units across programmes
- Complete curriculum mappings
- Repeatable with get_or_create

## Extension Points

### Future Enhancements

**1. Programme Specializations**:
- Add specialization field to Programme
- Create Specialization model
- Map units to specializations

**2. Prerequisite System**:
- Add prerequisite relationships to AcademicUnit
- Create Prerequisite model
- Validate student prerequisites

**3. Credit Tracking**:
- Track student credits per level
- Calculate progress to graduation
- Generate academic transcripts

**4. Timetable Integration**:
- Add schedule information to ProgrammeUnit
- Create Timetable model
- Support class scheduling

**5. Grade Management**:
- Add grade information to DocumentAcademicUnit
- Track student grades per unit
- Calculate GPA

**6. Recommendation Engine**:
- Enhance relevance scoring
- Add collaborative filtering
- Implement content-based recommendations

## Performance Considerations

### Query Optimization

1. **Use select_related for FKs**: Reduces query count
2. **Use prefetch_related for M2M**: Prevents N+1 queries
3. **Use only() to limit fields**: Reduces data transfer
4. **Add appropriate indexes**: Speeds up lookups
5. **Use bulk operations**: For large data migrations

### Monitoring

- Monitor query performance after migration
- Check index usage with EXPLAIN ANALYZE
- Track slow queries
- Optimize based on usage patterns

## Security Considerations

### Access Control

- Academic hierarchy is read-only for most users
- Admin-only access to curriculum management
- User profiles require authentication
- Document access respects visibility settings

### Data Integrity

- Foreign key constraints enforced
- Unique constraints prevent duplicates
- Cascade deletes configured appropriately
- Transactional operations for data consistency

## Testing Strategy

### Unit Tests

- Test model creation and validation
- Test query optimization
- Test filter logic
- Test profile completion logic

### Integration Tests

- Test upload workflow with new fields
- Test search with new filters
- Test personalized recommendations
- Test curriculum mapping

### End-to-End Tests

- Test complete user workflows
- Test backward compatibility
- Test performance under load
- Test migration rollback

## Conclusion

The enhanced academic architecture provides a robust, normalized foundation for PwaniNet's document repository. The design supports:

- **Scalability**: Reusable entities and efficient queries
- **Flexibility**: Supports diverse academic structures
- **Discoverability**: Enhanced filtering and search
- **Personalization**: Context-aware recommendations
- **Compatibility**: Preserves existing functionality

The architecture is designed for future growth while maintaining stability and performance.

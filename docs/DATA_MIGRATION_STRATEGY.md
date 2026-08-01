# Data Migration Strategy

## Overview

This document outlines the strategy for migrating existing data to the enhanced academic architecture while preserving all existing documents and maintaining backward compatibility.

## Migration Phases

### Phase 1: Preparation (Completed)
- Create new academic models (AcademicLevel, enhanced ProgrammeUnit, enhanced DocumentAcademicUnit)
- Add new fields to User model (programme, academic_level, academic_year, semester)
- Create migrations for new models
- Keep legacy fields for backward compatibility

### Phase 2: Data Migration (Pending)

#### Step 1: Migrate Academic Levels
- Map existing `courses.Year` model to new `AcademicLevel` model
- Create AcademicLevel records for Years 1-6
- Preserve all existing Year references

```sql
-- Example migration logic
INSERT INTO documents_academiclevel (level, name, description, is_active, created_at, updated_at)
SELECT 
    level,
    CONCAT('Year ', level),
    CONCAT('Year ', level, ' of study'),
    true,
    NOW(),
    NOW()
FROM courses_year;
```

#### Step 2: Migrate ProgrammeUnit Records
- Update existing ProgrammeUnit records with academic_level and academic_year
- Set default academic_level based on existing curriculum structure
- Set academic_year to current academic year for existing records
- Preserve all existing programme-unit relationships

```python
# Migration logic
for pu in ProgrammeUnit.objects.all():
    # Determine academic level based on programme structure
    # This may require manual mapping or inference
    pu.academic_level = AcademicLevel.objects.get(level=1)  # Default to Year 1
    pu.academic_year = AcademicYear.objects.get(is_current=True)
    pu.save()
```

#### Step 3: Migrate DocumentAcademicUnit Records
- Update existing DocumentAcademicUnit records with academic_level
- Infer academic_level from document metadata or set default
- Preserve all existing document-unit relationships
- Ensure unique constraints are satisfied

```python
# Migration logic
for dau in DocumentAcademicUnit.objects.all():
    # Infer academic level from document or set default
    dau.academic_level = AcademicLevel.objects.get(level=1)  # Default to Year 1
    dau.save()
```

#### Step 4: Migrate User Academic Profiles
- Map existing User.course to User.programme
- Map existing User.year to User.academic_level
- Set academic_year and semester to current values
- Keep legacy fields for backward compatibility

```python
# Migration logic
for user in User.objects.filter(course__isnull=False):
    # Map Course to Programme (may require manual mapping table)
    programme = Programme.objects.filter(code=user.course.code).first()
    if programme:
        user.programme = programme
    
    # Map Year to AcademicLevel
    if user.year:
        user.academic_level = AcademicLevel.objects.get(level=user.year.level)
    
    # Set current academic context
    user.academic_year = AcademicYear.objects.get(is_current=True)
    user.semester = Semester.objects.filter(is_current=True).first()
    
    user.save()
```

### Phase 3: Validation (Pending)

#### Validation Checks
1. **Data Integrity**
   - Verify all documents have valid academic metadata
   - Check all ProgrammeUnit records have required fields
   - Ensure all User profiles have valid academic references

2. **Relationship Integrity**
   - Verify foreign key constraints are satisfied
   - Check that unique constraints are not violated
   - Ensure no orphaned records exist

3. **Functional Validation**
   - Test document upload with new academic fields
   - Test search with new filters
   - Test personalized recommendations
   - Verify backward compatibility with legacy fields

### Phase 4: Rollback Plan

If migration fails, rollback strategy:

1. **Database Rollback**
   - Use Django migration rollback: `python manage.py migrate documents <previous_migration>`
   - Restore from backup if needed

2. **Data Recovery**
   - Restore from pre-migration database backup
   - Re-run seed data scripts if needed

3. **Fallback to Legacy**
   - System continues to work with legacy fields
   - New fields remain nullable until migration is successful

## Pre-Migration Checklist

- [ ] Create full database backup
- [ ] Test migration on staging environment
- [ ] Verify all existing documents are accessible
- [ ] Document any manual mapping requirements (Course → Programme)
- [ ] Prepare rollback procedures
- [ ] Notify users of scheduled maintenance

## Post-Migration Tasks

- [ ] Verify all documents are accessible
- [ ] Test upload workflow with new academic fields
- [ ] Test search with new filters
- [ ] Test personalized recommendations
- [ ] Monitor performance metrics
- [ ] Update user documentation
- [ ] Deprecate legacy fields (after validation period)

## Manual Mapping Requirements

### Course → Programme Mapping
Some legacy Course codes may not directly map to Programme codes. A manual mapping table may be required:

```python
COURSE_TO_PROGRAMME_MAPPING = {
    'BSC-COMPUTER-SCIENCE': 'BSC-CS',
    'BSC-INFORMATION-TECHNOLOGY': 'BSC-IT',
    'BBA-BUSINESS-ADMINISTRATION': 'BBA',
    # Add more mappings as needed
}
```

### Year → AcademicLevel Mapping
Direct mapping: `Year.level` → `AcademicLevel.level`

## Performance Considerations

- Use bulk operations for large datasets
- Batch updates to avoid memory issues
- Consider disabling indexes during migration
- Re-enable indexes after migration
- Update statistics after migration

## Testing Strategy

1. **Unit Tests**
   - Test model migrations
   - Test data transformation logic
   - Test constraint validation

2. **Integration Tests**
   - Test document upload with new fields
   - Test search with new filters
   - Test user profile updates

3. **End-to-End Tests**
   - Test complete user workflows
   - Test backward compatibility
   - Test performance under load

## Monitoring

After migration, monitor:
- Database query performance
- Error rates in document operations
- User feedback on new features
- System resource utilization

## Timeline Estimate

- Phase 1 (Preparation): Completed
- Phase 2 (Data Migration): 2-4 hours
- Phase 3 (Validation): 2-3 hours
- Phase 4 (Rollback Plan): 1 hour (prepared in advance)

Total estimated time: 5-8 hours including testing

## Success Criteria

- All existing documents remain accessible
- No data loss during migration
- All new academic features work correctly
- Backward compatibility maintained
- Performance metrics within acceptable range
- User acceptance testing passes

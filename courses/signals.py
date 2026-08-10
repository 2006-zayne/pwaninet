"""
Courses domain signals for event emission.
Emits events for the new notification engine.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from courses.models import Course, Unit
from notifications.events import publish_event, EventTypes, EventSources, EventActions


@receiver(post_save, sender=Course)
def course_created(sender, instance, created, **kwargs):
    """Emit event when a course is created."""
    if created:
        publish_event(
            event_type=EventTypes.COURSES_COURSE_CREATED.value,
            source=EventSources.COURSES.value,
            action=EventActions.CREATED.value,
            target_type='Course',
            target_id=str(instance.id),
            metadata={
                'course_code': instance.code,
                'course_name': instance.name
            }
        )


@receiver(post_save, sender=Unit)
def unit_created(sender, instance, created, **kwargs):
    """Emit event when a unit is created."""
    if created:
        publish_event(
            event_type=EventTypes.COURSES_UNIT_CREATED.value,
            source=EventSources.COURSES.value,
            action=EventActions.CREATED.value,
            target_type='Unit',
            target_id=str(instance.id),
            context_type='COURSE',
            context_id=str(instance.course.id),
            metadata={
                'unit_code': instance.code,
                'unit_name': instance.name,
                'course_code': instance.course.code
            }
        )

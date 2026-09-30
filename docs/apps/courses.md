# Courses app

## Purpose

`courses` contains a course catalogue and academic-structure models used by course browsing and older parts of the application. Newer registration and document-repository academic classifications also exist in `documents/academic/`.

## Main data

Models include `Faculty`, `School`, `Department`, `Programme`, `Year`, `Course`, `Unit`, and `CourseAcademicUnit`, with code enums and status fields for institutional structures.

## Main journeys

The app exposes course and academic catalogue data for browsing and related course/unit selection. Management commands seed or synchronize academic structures. Some app features still refer to legacy `Course` and `Year` user relations, while registration uses the academic models from the documents domain.

## Routes and entry points

Mounted at `/courses/` from `courses/urls.py`. Main code is in `courses/models.py`, `courses/views.py`, `courses/serializers.py`, `courses/filters.py`, and `courses/management/commands/`.

## Developer notes

- Check whether a new feature should use a `courses` model or a `documents.academic` model before adding a second academic classification.
- Data synchronization and seed commands can affect shared catalogue records; review their behavior before running against a non-development database.
- Existing migrations define production schema history. Do not edit old migrations to represent a new schema change.

"""
View modules, one per feature area (matching the SRS section they implement):

    auth.py           — login, logout, forced/voluntary password change (§4.9)
    dashboard.py       — Head and Class Leader landing pages
    classes.py         — class create/edit, class-scoped navigation (§4.8, §3.2)
    accounts.py        — Head-only account management (§4.8)
    students.py        — registration + existing-student match check (§4.1, §4.2)
    attendance.py       — attendance sheets, cells, manual add-student (§4.3, §4.5)
    marklists.py        — mark lists, columns, duplicate, manual add-student (§4.3, §4.4)
    roster.py           — roster tables, columns, calculate, duplicate (§4.6)
    removal.py          — removal requests: file / resolve (§4.7)
    activity_log.py     — Head-only activity log, filterable (§4.10)

Deliberately left empty otherwise — this package exists so each feature area's
views live in their own file rather than one long views.py, and so their
templates can mirror the same folder-for-folder split (school/templates/attendance/
matches school/views/attendance.py, etc.). school/urls.py imports directly from
each submodule (e.g. `from school.views import attendance`) rather than
re-exporting everything through this file, so nothing needs adding here as new
view functions get built.
"""
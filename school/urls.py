from django.urls import path

from .views import (
    accounts,
    activity_log,
    attendance,
    auth,
    classes,
    dashboard,
    marklists,
    removal,
    roster,
    students,
)

app_name = "school"

urlpatterns = [
    # --- auth ---
    path("login/", auth.login_view, name="login"),
    path("logout/", auth.logout_view, name="logout"),
    path("password/change/forced/", auth.forced_password_change_view, name="force_password_change"),
    path("password/change/", auth.password_change_view, name="password_change"),
    path("profile/", auth.profile_view, name="profile"),

    # --- dashboard ---
    path("", dashboard.dashboard_view, name="dashboard"),

    # --- classes ---
    path("classes/", classes.class_list, name="class_list"),
    path("classes/new/", classes.class_create, name="class_create"),
    path("classes/<int:classroom_id>/", classes.class_detail, name="class_detail"),
    path("classes/<int:classroom_id>/edit/", classes.class_edit, name="class_edit"),

    # --- accounts ---
    path("accounts/", accounts.account_list, name="account_list"),
    path("accounts/new/", accounts.account_create, name="account_create"),
    path("accounts/<int:user_id>/edit/", accounts.account_edit, name="account_edit"),
    path("accounts/<int:user_id>/reset-password/", accounts.account_reset_password, name="account_reset_password"),

    # --- students (confirmed against views/students.py) ---
    path("students/search/", students.student_search, name="student_search"),
    path("students/register/", students.student_register, name="student_register"),
    path("students/<int:student_id>/", students.student_detail, name="student_detail"),
    path("students/<int:student_id>/edit/", students.student_edit, name="student_edit"),

    # --- attendance ---
    path("classes/<int:classroom_id>/attendance/", attendance.sheet_list, name="attendance_sheet_list"),
    path("classes/<int:classroom_id>/attendance/create/", attendance.sheet_create, name="attendance_sheet_create"),
    path("attendance/<int:sheet_id>/", attendance.sheet_detail, name="attendance_sheet_detail"),
    path("attendance/<int:sheet_id>/add-student/", attendance.add_student, name="attendance_add_student"),
    path("attendance/<int:sheet_id>/mark/", attendance.mark_cell, name="attendance_mark_cell"),
    path("attendance/<int:sheet_id>/export/", attendance.sheet_export, name="attendance_sheet_export"),

    # --- mark lists ---
    path("classes/<int:classroom_id>/marklists/", marklists.mark_list_list, name="mark_list_list"),
    path("classes/<int:classroom_id>/marklists/create/", marklists.mark_list_create, name="mark_list_create"),
    path("marklists/<int:mark_list_id>/", marklists.mark_list_detail, name="mark_list_detail"),
    path("marklists/<int:mark_list_id>/duplicate/", marklists.mark_list_duplicate, name="mark_list_duplicate"),
    path("marklists/<int:mark_list_id>/edit/", marklists.mark_list_edit_header, name="mark_list_edit_header"),
    path("marklists/<int:mark_list_id>/add-student/", marklists.add_student, name="mark_list_add_student"),
    path("marklists/<int:mark_list_id>/columns/create/", marklists.column_create, name="mark_list_column_create"),
    path("marklists/<int:mark_list_id>/columns/<int:column_id>/delete/", marklists.column_delete, name="mark_list_column_delete"),
    path("marklists/<int:mark_list_id>/update-cell/", marklists.update_cell, name="mark_list_update_cell"),
    path("marklists/<int:mark_list_id>/export/", marklists.mark_list_export, name="mark_list_export"),

    # --- roster ---
    path("classes/<int:classroom_id>/roster/", roster.roster_list, name="roster_list"),
    path("classes/<int:classroom_id>/roster/create/", roster.roster_create, name="roster_create"),
    path("roster/<int:roster_id>/", roster.roster_detail, name="roster_detail"),
    path("roster/<int:roster_id>/duplicate/", roster.roster_duplicate, name="roster_duplicate"),
    path("roster/<int:roster_id>/edit/", roster.roster_edit_header, name="roster_edit_header"),
    path("roster/<int:roster_id>/columns/create/", roster.column_create, name="roster_column_create"),
    path("roster/<int:roster_id>/columns/<int:column_id>/delete/", roster.column_delete, name="roster_column_delete"),
    path("roster/<int:roster_id>/update-cell/", roster.update_cell, name="roster_update_cell"),
    path("roster/<int:roster_id>/calculate/", roster.calculate, name="roster_calculate"),
    path("roster/<int:roster_id>/export/", roster.roster_export, name="roster_export"),

    # --- removal requests ---
    path("removal/<str:kind>/<int:object_id>/request/", removal.request_removal, name="request_removal"),
    path("removal/pending/", removal.pending_list, name="removal_pending_list"),
    path("removal/<int:request_id>/resolve/", removal.resolve, name="removal_resolve"),

    # --- activity log ---
    path("activity-log/", activity_log.activity_log_list, name="activity_log_list"),
]
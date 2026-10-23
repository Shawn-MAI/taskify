"""URL routes for the boards app."""

from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("", views.users, name="users"),
    path("projects/", views.projects, name="projects"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<int:project_id>/", views.board, name="board"),
    path("projects/<int:project_id>/board.json", views.board_json, name="board_json"),
    path("projects/<int:project_id>/tasks/new/", views.task_create, name="task_create"),
    path("tasks/<int:task_id>/", views.task_detail, name="task_detail"),
    path("tasks/<int:task_id>/move/", views.task_move, name="task_move"),
    path("tasks/<int:task_id>/assign/", views.task_assign, name="task_assign"),
    path("tasks/<int:task_id>/comments/", views.comment_add, name="comment_add"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications.json", views.notifications_json, name="notifications_json"),
    path("notifications/<int:notification_id>/read/", views.notification_read, name="notification_read"),
    path("events/", views.events, name="events"),
]

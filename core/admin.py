from django.contrib import admin
from .models import Notification, PrintRequest


# =========================================================
# Notifications Admin
# =========================================================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "document",
        "type",
        "is_read",
        "created_at",
    )

    list_filter = (
        "type",
        "is_read",
        "created_at",
    )

    search_fields = (
        "recipient__username",
        "document__title",
        "message",
    )

    readonly_fields = (
        "created_at",
    )

    list_select_related = (
        "recipient",
        "document",
    )

    date_hierarchy = "created_at"


# =========================================================
# Print Requests Admin
# =========================================================
@admin.register(PrintRequest)
class PrintRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "document",
        "status",
        "created_at",
        "handled_by",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "user__username",
        "document__title",
        "reason",
    )

    readonly_fields = (
        "created_at",
        "handled_at",
    )

    list_select_related = (
        "user",
        "document",
        "handled_by",
    )

    date_hierarchy = "created_at"


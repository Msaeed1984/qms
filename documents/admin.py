from django.contrib import admin
from .models import Document, DocumentActivity


# =========================================================
# Document Admin
# =========================================================
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "department",
        "status",
        "created_by",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "status",
        "department",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "title",
        "description",
        "department__name",
        "created_by__username",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


# =========================================================
# Activity Log Admin
# =========================================================
@admin.register(DocumentActivity)
class DocumentActivityAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "user",
        "department",
        "action",
        "timestamp",
    )

    list_filter = (
        "action",
        "department",
        "timestamp",
    )

    search_fields = (
        "document__title",
        "user__username",
        "department__name",
    )

    readonly_fields = (
        "document",
        "user",
        "department",
        "action",
        "timestamp",
    )

    ordering = ("-timestamp",)
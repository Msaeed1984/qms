from django.conf import settings
from django.db import models
from django.db.models import Count
from accounts.models import Department


# =========================================================
# Document Model
# =========================================================
class Document(models.Model):
    """Single-PDF document linked to one department."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DISABLED = "disabled", "Disabled"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="documents",
        help_text="Target department for this document"
    )

    pdf_file = models.FileField(upload_to="documents/pdfs/")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )

    disabled_reason = models.CharField(max_length=255, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_documents"
    )

    # =====================================================
    # 👑 NEW: Explicit Readers (Enterprise Sharing Logic)
    # =====================================================
    readers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="shared_documents",
        help_text="Specific users allowed to read this document."
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["department"]),
        ]

    # =====================================================
    # Helpers
    # =====================================================
    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def disabled_attempts_count(self):
        """
        Count how many times users tried to open this document while disabled.
        """
        return self.activities.filter(
            action=DocumentActivity.Action.ATTEMPT_DISABLED
        ).count()

    def __str__(self):
        return f"{self.title} - {self.department.name}"


# =========================================================
# Document Activity Log
# =========================================================
class DocumentActivity(models.Model):

    class Action(models.TextChoices):
        VIEW = "view", "Viewed"
        CREATE = "create", "Created"
        EDIT = "edit", "Edited"
        DELETE = "delete", "Deleted"
        ATTEMPT_DISABLED = "attempt_disabled", "Attempted Disabled Access"

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="document_activities"
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_activities"
    )

    action = models.CharField(
        max_length=30,
        choices=Action.choices,
        db_index=True
    )

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Document Activity"
        verbose_name_plural = "Document Activities"
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        user = self.user.username if self.user else "System"
        return f"{user} {self.get_action_display()} {self.document.title}"

    # =====================================================
    # Enterprise Analytics Helpers
    # =====================================================
    @staticmethod
    def total_attempts_for_user(user):
        return DocumentActivity.objects.filter(
            user=user,
            action=DocumentActivity.Action.ATTEMPT_DISABLED
        ).count()

    @staticmethod
    def top_disabled_attempt_users(limit=5):
        return (
            DocumentActivity.objects
            .filter(action=DocumentActivity.Action.ATTEMPT_DISABLED)
            .values("user__username")
            .annotate(total=Count("id"))
            .order_by("-total")[:limit]
        )

    @staticmethod
    def top_disabled_attempt_documents(limit=5):
        return (
            DocumentActivity.objects
            .filter(action=DocumentActivity.Action.ATTEMPT_DISABLED)
            .values("document__title")
            .annotate(total=Count("id"))
            .order_by("-total")[:limit]
        )
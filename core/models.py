from django.conf import settings
from django.db import models
from documents.models import Document


# =========================================================
# Notifications
# =========================================================
class Notification(models.Model):
    """
    Smart notifications for users related to document updates.
    Used inside system (messages + future bell center).
    """

    class Type(models.TextChoices):
        UPDATED = "updated", "Document Updated"
        DISABLED = "disabled", "Document Disabled"
        REACTIVATED = "reactivated", "Document Reactivated"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        db_index=True
    )

    message = models.CharField(max_length=255, blank=True)

    is_read = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notify {self.recipient} - {self.type} - {self.document}"


# =========================================================
# Print Request (Future Feature)
# =========================================================
class PrintRequest(models.Model):
    """
    Future feature:
    Allow user to request printing a document with approval workflow.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="print_requests"
    )

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="print_requests"
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_print_requests"
    )

    handled_at = models.DateTimeField(blank=True, null=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PrintRequest - {self.user} - {self.document} - {self.status}"
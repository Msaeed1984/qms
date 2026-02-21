from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from .models import Document

User = get_user_model()


class DocumentForm(forms.ModelForm):
    """
    Enterprise Professional Form for creating & editing documents.

    Enhancements:
    - Strong file validation
    - Business rule enforcement
    - Trim inputs
    - Secure clean handling
    - Explicit Readers support (NEW)
    """

    MAX_FILE_SIZE_MB = 10
    ALLOWED_CONTENT_TYPES = ["application/pdf"]

    class Meta:
        model = Document
        fields = [
            "title",
            "description",
            "department",
            "pdf_file",
            "status",
            "disabled_reason",
            "readers",  # 👑 NEW FIELD
        ]

        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter document title",
                "autocomplete": "off",
            }),

            "description": forms.Textarea(attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "Short description (optional)"
            }),

            "department": forms.Select(attrs={
                "class": "form-select"
            }),

            "pdf_file": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "application/pdf"
            }),

            "status": forms.Select(attrs={
                "class": "form-select"
            }),

            "disabled_reason": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Required if status = Disabled"
            }),

            # 👑 Multiple User Select
            "readers": forms.SelectMultiple(attrs={
                "class": "form-select",
                "size": 6,
            }),
        }

    # =========================================================
    # INIT – Dynamic Reader Filtering
    # =========================================================
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter readers by selected department (if available)
        if self.instance and self.instance.pk:
            department = self.instance.department
        else:
            department = self.initial.get("department")

        if department:
            self.fields["readers"].queryset = User.objects.filter(
                department=department,
                is_active=True
            )
        else:
            self.fields["readers"].queryset = User.objects.filter(is_active=True)

        # Prevent selecting self
        if self.user:
            self.fields["readers"].queryset = self.fields["readers"].queryset.exclude(
                id=self.user.id
            )

    # =========================================================
    # Normalize & Trim Text Fields
    # =========================================================
    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if not title:
            raise ValidationError(_("Title cannot be empty."))
        return title

    def clean_description(self):
        description = self.cleaned_data.get("description", "")
        return description.strip()

    def clean_disabled_reason(self):
        reason = self.cleaned_data.get("disabled_reason", "")
        return reason.strip()

    # =========================================================
    # File Validation
    # =========================================================
    def clean_pdf_file(self):
        file = self.cleaned_data.get("pdf_file")

        if not file:
            if self.instance and self.instance.pk:
                return file
            raise ValidationError(_("PDF file is required."))

        if not file.name.lower().endswith(".pdf"):
            raise ValidationError(_("Only PDF files are allowed."))

        content_type = getattr(file, "content_type", None)
        if content_type and content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValidationError(_("Invalid file type. Please upload a valid PDF."))

        if file.size > self.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValidationError(
                _(f"File too large. Max size is {self.MAX_FILE_SIZE_MB}MB.")
            )

        return file

    # =========================================================
    # Business Rules Validation
    # =========================================================
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        reason = cleaned_data.get("disabled_reason")

        if status == Document.Status.DISABLED and not reason:
            self.add_error(
                "disabled_reason",
                _("Disabled reason is required when status is Disabled.")
            )

        return cleaned_data
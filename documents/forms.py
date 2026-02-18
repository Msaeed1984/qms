from django import forms
from .models import Document


class DocumentForm(forms.ModelForm):
    """
    Professional form for creating & editing documents.

    Notes:
    - Quality / Admin will use it to create/edit
    - Employee & Manager will NOT access it
    """

    MAX_FILE_SIZE_MB = 10  # 10MB limit

    class Meta:
        model = Document
        fields = [
            "title",
            "description",
            "department",
            "pdf_file",
            "status",
            "disabled_reason",
        ]

        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter document title"
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
        }

    # =========================================================
    # File Validation (Security)
    # =========================================================
    def clean_pdf_file(self):
        file = self.cleaned_data.get("pdf_file")

        if not file:
            return file

        # 1️⃣ Validate file type
        if not file.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Only PDF files are allowed.")

        # 2️⃣ Validate content type (extra safety)
        if hasattr(file, "content_type"):
            if file.content_type != "application/pdf":
                raise forms.ValidationError("Invalid file type. Please upload a valid PDF.")

        # 3️⃣ Validate size
        if file.size > self.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(
                f"File too large. Max size is {self.MAX_FILE_SIZE_MB}MB."
            )

        return file

    # =========================================================
    # Business Rules Validation
    # =========================================================
    def clean(self):
        """
        Business validation:
        - If status = DISABLED → reason required
        """
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        reason = cleaned_data.get("disabled_reason")

        if status == Document.Status.DISABLED and not reason:
            self.add_error(
                "disabled_reason",
                "Disabled reason is required when status is Disabled."
            )

        return cleaned_data
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Document, DocumentActivity
from .forms import DocumentForm
from accounts.permissions import (
    is_quality,
    is_manager,
    is_employee,
    is_admin_role,
)


# =========================================================
# Helpers (لا يكسر أي شيء - فقط لتقليل التكرار)
# =========================================================
def _can_manage_docs(user) -> bool:
    return bool(is_quality(user) or is_admin_role(user) or getattr(user, "is_superuser", False))


def _department_of(user):
    return getattr(user, "department", None)


def _can_view_document(user, document: Document) -> bool:
    """
    حماية إضافية حتى لو المستخدم فتح رابط مباشر /documents/view/<id>/
    نفس منطق document_list:
    - Quality/Admin/Superuser: كل شيء
    - Manager: قسمه فقط + غير archived
    - Employee: فقط ما أنشأه + غير archived
    """
    if is_quality(user) or is_admin_role(user) or getattr(user, "is_superuser", False):
        return True

    if is_manager(user):
        return (
            document.department_id == getattr(user, "department_id", None)
            and document.status != Document.Status.ARCHIVED
        )

    if is_employee(user):
        return (
            document.created_by_id == getattr(user, "id", None)
            and document.status != Document.Status.ARCHIVED
        )

    return False


# =========================================================
# Document List
# =========================================================
@login_required
def document_list(request):
    """
    Permission-based document viewer.

    Roles behavior:
    - Quality / admin_role / superuser: see ALL documents
    - Manager: see documents of their department only
    - Employee: see ONLY documents they created
    """
    user = request.user

    if is_quality(user) or is_admin_role(user) or user.is_superuser:
        documents = Document.objects.all().select_related("department", "created_by")

    elif is_manager(user):
        documents = (
            Document.objects.filter(department=user.department)
            .exclude(status=Document.Status.ARCHIVED)
            .select_related("department", "created_by")
        )

    elif is_employee(user):
        documents = (
            Document.objects.filter(created_by=user)
            .exclude(status=Document.Status.ARCHIVED)
            .select_related("department", "created_by")
        )

    else:
        documents = Document.objects.none()

    context = {
        "documents": documents,
        "total_docs": documents.count(),
        "can_manage": _can_manage_docs(user),
    }
    return render(request, "qms-templates/document_list.html", context)

# =========================================================
# View Document (Activity Log + PDF.js + Watermark Ready)
# =========================================================
@login_required
def document_view(request, pk):
    """
    Open PDF inside secure viewer (PDF.js) + log activity
    """

    user = request.user
    document = get_object_or_404(Document, pk=pk)

    # حماية من فتح الرابط المباشر بدون صلاحية
    if not _can_view_document(user, document):
        messages.error(request, "Access denied. You are not allowed to view this document.")
        return redirect("documents:list")

    # رابط PDF الكامل
    base_pdf_url = request.build_absolute_uri(document.pdf_file.url)

    # اسم المستخدم والقسم (للـ watermark)
    username = user.username
    department_name = getattr(user.department, "name", "")

    # رابط PDF.js Viewer
    pdf_absolute_url = (
        f"/static/pdfjs/web/viewer.html"
        f"?file={base_pdf_url}"
        f"&user={username}"
        f"&dept={department_name}"
    )

    # تسجيل القراءة
    DocumentActivity.objects.create(
        document=document,
        user=user,
        department=_department_of(user),
        action=DocumentActivity.Action.VIEW,
    )

    return render(
        request,
        "qms-templates/pdf_viewer.html",
        {
            "document": document,
            "pdf_absolute_url": pdf_absolute_url,
        },
    )

# =========================================================
# Create Document
# =========================================================
@login_required
def document_create(request):
    user = request.user

    if not _can_manage_docs(user):
        messages.error(request, "You are not allowed to upload documents.")
        return redirect("documents:list")

    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.created_by = user
            document.save()

            DocumentActivity.objects.create(
                document=document,
                user=user,
                department=_department_of(user),
                action=DocumentActivity.Action.CREATE,
            )

            messages.success(request, "Document uploaded successfully.")
            return redirect("documents:list")
    else:
        form = DocumentForm()

    return render(request, "qms-templates/document_form.html", {"form": form})


# =========================================================
# Edit Document
# =========================================================
@login_required
def document_edit(request, pk):
    user = request.user

    if not _can_manage_docs(user):
        messages.error(request, "You are not allowed to edit documents.")
        return redirect("documents:list")

    document = get_object_or_404(Document, pk=pk)

    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            form.save()

            DocumentActivity.objects.create(
                document=document,
                user=user,
                department=_department_of(user),
                action=DocumentActivity.Action.EDIT,
            )

            messages.success(request, "Document updated successfully.")
            return redirect("documents:list")
    else:
        form = DocumentForm(instance=document)

    return render(
        request,
        "qms-templates/document_form.html",
        {"form": form, "document": document},
    )


# =========================================================
# Delete Document
# =========================================================
@login_required
def document_delete(request, pk):
    user = request.user

    if not _can_manage_docs(user):
        messages.error(request, "You are not allowed to delete documents.")
        return redirect("documents:list")

    document = get_object_or_404(Document, pk=pk)

    if request.method == "POST":
        DocumentActivity.objects.create(
            document=document,
            user=user,
            department=_department_of(user),
            action=DocumentActivity.Action.DELETE,
        )

        document.delete()
        messages.success(request, "Document deleted successfully.")
        return redirect("documents:list")

    return render(request, "qms-templates/document_delete.html", {"document": document})
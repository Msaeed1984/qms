from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Document, DocumentActivity
from .forms import DocumentForm
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from accounts.models import Department
from django.http import HttpResponse
import csv
import json
from accounts.permissions import (
    is_quality,
    is_manager,
    is_employee,
    is_admin_role,
)

User = get_user_model()


@login_required
def get_department_users(request):
    department_id = request.GET.get("department_id")

    if not department_id:
        return JsonResponse({"users": []})

    users = User.objects.filter(
        department_id=department_id,
        is_active=True
    ).values("id", "username")

    return JsonResponse({"users": list(users)})

# =========================================================
# Helpers
# =========================================================
def _can_manage_docs(user) -> bool:
    return bool(
        is_quality(user)
        or is_admin_role(user)
        or getattr(user, "is_superuser", False)
    )


def _department_of(user):
    return getattr(user, "department", None)

def _can_view_document(user, document: Document) -> bool:
    """
    Enterprise Permission Logic (Fixed Version):
    - Disabled documents can ONLY be opened by Quality/Admin/Superuser
    - Explicit Readers respected (except if disabled)
    - Manager: department only + not archived
    - Employee: own documents only + not archived
    """

    # 🛑 Disabled has highest priority
    if document.status == Document.Status.DISABLED:
        if is_quality(user) or is_admin_role(user) or getattr(user, "is_superuser", False):
            return True
        return False

    # 🟢 Full Access Roles
    if is_quality(user) or is_admin_role(user) or getattr(user, "is_superuser", False):
        return True

    # 🟢 Explicit Readers
    if document.readers.filter(id=user.id).exists():
        return document.status != Document.Status.ARCHIVED

    # 🟡 Manager
    if is_manager(user):
        return (
            document.department_id == getattr(user, "department_id", None)
            and document.status != Document.Status.ARCHIVED
        )

    # 🔵 Employee (Creator Only)
    if is_employee(user):
        return (
            document.created_by_id == getattr(user, "id", None)
            and document.status != Document.Status.ARCHIVED
        )

    return False

# =========================================================
# Document List (With Department Filter + Disabled Last)
# =========================================================
@login_required
def document_list(request):

    user = request.user
    department_name = None

    # ==========================
    # Base Query (حسب الدور)
    # ==========================

    if is_quality(user) or is_admin_role(user) or user.is_superuser:
        documents = Document.objects.all()

        # 👇 فلتر الإدارة عبر GET
        department_id = request.GET.get("department")
        if department_id:
            documents = documents.filter(department_id=department_id)

        department_name = (
            documents.first().department.name
            if department_id and documents.exists()
            else "All Departments"
        )

    elif is_manager(user):
        documents = (
            Document.objects.filter(department=user.department)
            | Document.objects.filter(readers=user)
        ).exclude(status=Document.Status.ARCHIVED)

        department_name = getattr(user.department, "name", None)

    elif is_employee(user):
        documents = (
            Document.objects.filter(created_by=user)
            | Document.objects.filter(readers=user)
        ).exclude(status=Document.Status.ARCHIVED)

        department_name = getattr(user.department, "name", None)

    else:
        documents = Document.objects.none()

    # ==========================
    # Disabled Always Last
    # ==========================

    documents = (
        documents
        .select_related("department", "created_by")
        .order_by("status", "-updated_at")   # 👈 مهم
        .distinct()
    )

    context = {
        "documents": documents,
        "total_docs": documents.count(),
        "can_manage": _can_manage_docs(user),
        "context_department": department_name,
        "departments": Department.objects.filter(is_active=True),
    }

    return render(
        request,
        "qms-templates/document_list.html",
        context
    )
# =========================================================
# View Document (Secure + Enterprise Logging)
# =========================================================
@login_required
def document_view(request, pk):

    user = request.user
    document = get_object_or_404(Document, pk=pk)

    # 🔐 Permission Check
    if not _can_view_document(user, document):

        # ✅ Log Attempt ONLY if Disabled
        if document.status == Document.Status.DISABLED:
            DocumentActivity.objects.create(
                document=document,
                user=user,
                department=_department_of(user),
                action=DocumentActivity.Action.ATTEMPT_DISABLED,
            )

            message = "This document is currently disabled."
            if document.disabled_reason:
                message += f" Reason: {document.disabled_reason}"

            messages.error(request, message)

        else:
            messages.error(
                request,
                "Access denied. You are not authorized to view this document."
            )

        return redirect("documents:list")

    # ==========================================
    # Build Secure PDF URL
    # ==========================================
    base_pdf_url = request.build_absolute_uri(document.pdf_file.url)

    username = user.username
    department_name = getattr(user.department, "name", "")

    pdf_absolute_url = (
        f"/static/pdfjs/web/viewer.html"
        f"?file={base_pdf_url}"
        f"&user={username}"
        f"&dept={department_name}"
    )

    # ==========================================
    # Log Successful View
    # ==========================================
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
        form = DocumentForm(request.POST, request.FILES, user=request.user)

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
        form = DocumentForm(user=request.user)

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
        form = DocumentForm(request.POST, request.FILES, instance=document, user=request.user)

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
        form = DocumentForm(instance=document, user=request.user)

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

    return render(
        request,
        "qms-templates/document_delete.html",
        {"document": document},
    )
# =========================================================
# AUDIT MONITORING DASHBOARD
# =========================================================


@login_required
def audit_dashboard(request):

    # 🔐 Only Quality/Admin/Superuser
    if not _can_manage_docs(request.user):
        messages.error(request, "Not authorized to access audit logs.")
        return redirect("documents:list")

    logs = DocumentActivity.objects.select_related(
        "document", "user", "department"
    ).order_by("-timestamp")

    # =============================
    # Pagination
    # =============================
    paginator = Paginator(logs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # =============================
    # KPIs
    # =============================
    today = timezone.now().date()

    total_logs = DocumentActivity.objects.count()

    today_logs = DocumentActivity.objects.filter(
        timestamp__date=today
    ).count()

    disabled_today = DocumentActivity.objects.filter(
        action=DocumentActivity.Action.ATTEMPT_DISABLED,
        timestamp__date=today
    ).count()

    most_active_user = (
        DocumentActivity.objects
        .values("user__username")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    # =============================
    # Smart Security Detection (Last 24h)
    # =============================
    last_24h = timezone.now() - timedelta(hours=24)

    suspicious_users = (
        DocumentActivity.objects
        .filter(
            action=DocumentActivity.Action.ATTEMPT_DISABLED,
            timestamp__gte=last_24h
        )
        .values("user__username")
        .annotate(total=Count("id"))
        .filter(total__gte=5)
        .order_by("-total")
    )

    risky_documents = (
        DocumentActivity.objects
        .filter(
            action=DocumentActivity.Action.ATTEMPT_DISABLED,
            timestamp__gte=last_24h
        )
        .values("document__title")
        .annotate(total=Count("id"))
        .filter(total__gte=5)
        .order_by("-total")
    )

    # =============================
    # Chart Data (Activity Distribution)
    # =============================
    action_chart = (
        DocumentActivity.objects
        .values("action")
        .annotate(total=Count("id"))
    )

    chart_labels = [item["action"] for item in action_chart]
    chart_data = [item["total"] for item in action_chart]

    context = {
        "page_obj": page_obj,
        "total_logs": total_logs,
        "today_logs": today_logs,
        "disabled_today": disabled_today,
        "most_active_user": most_active_user,
        "suspicious_users": suspicious_users,
        "risky_documents": risky_documents,
        "context_labels": json.dumps(chart_labels),
        "context_data": json.dumps(chart_data),
    }

    return render(request, "qms-templates/audit_dashboard.html", context)

# =========================================================
# QUALITY CENTER DASHBOARD
# =========================================================

@login_required
def quality_center(request):

    # 🔐 Only Quality/Admin/Superuser
    if not _can_manage_docs(request.user):
        messages.error(request, "Not authorized.")
        return redirect("documents:list")

    # ========================
    # KPI Metrics
    # ========================

    kpi_total_docs = Document.objects.count()
    kpi_active_docs = Document.objects.filter(status=Document.Status.ACTIVE).count()
    kpi_archived_docs = Document.objects.filter(status=Document.Status.ARCHIVED).count()
    kpi_departments = Document.objects.values("department").distinct().count()
    kpi_users = User.objects.filter(is_active=True).count()
    kpi_activities = DocumentActivity.objects.count()

    # ========================
    # Weekly Activity (Last 7 Days)
    # ========================

    last_7_days = timezone.now() - timedelta(days=7)

    weekly_data = (
        DocumentActivity.objects
        .filter(timestamp__gte=last_7_days)
        .extra(select={"day": "date(timestamp)"})
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    weekly_labels = [str(item["day"]) for item in weekly_data]
    weekly_values = [item["total"] for item in weekly_data]

    # ========================
    # Activity by Action
    # ========================

    action_chart = (
        DocumentActivity.objects
        .values("action")
        .annotate(total=Count("id"))
    )

    action_labels = [item["action"] for item in action_chart]
    action_values = [item["total"] for item in action_chart]

    # ========================
    # Department Distribution
    # ========================

    dept_chart = (
        Document.objects
        .values("department__name")
        .annotate(total=Count("id"))
    )

    dept_labels = [item["department__name"] for item in dept_chart]
    dept_values = [item["total"] for item in dept_chart]

    # ========================
    # Recent Data
    # ========================

    recent_docs = Document.objects.select_related("department").order_by("-updated_at")[:5]
    recent_activities = DocumentActivity.objects.select_related("document", "user").order_by("-timestamp")[:5]

    # ========================
    # 🛡 Security & Risk Logic (FIXED)
    # ========================

    risk_disabled_attempts = DocumentActivity.objects.filter(
        action=DocumentActivity.Action.ATTEMPT_DISABLED
    ).count()

    # Top User (ONLY Disabled Attempts)
    top_user = (
        DocumentActivity.objects
        .filter(action=DocumentActivity.Action.ATTEMPT_DISABLED)
        .values("user__username")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    risk_top_user = top_user["user__username"] if top_user else "-"

    # Top Document (ONLY Disabled Attempts)
    top_doc = (
        DocumentActivity.objects
        .filter(action=DocumentActivity.Action.ATTEMPT_DISABLED)
        .values("document__title")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    risk_top_document = top_doc["document__title"] if top_doc else "-"

    # Risk Level Logic
    if risk_disabled_attempts > 20:
        risk_level = "High"
    elif risk_disabled_attempts > 5:
        risk_level = "Medium"
    elif risk_disabled_attempts > 0:
        risk_level = "Low"
    else:
        risk_level = "Low"

    context = {
        "kpi_total_docs": kpi_total_docs,
        "kpi_active_docs": kpi_active_docs,
        "kpi_archived_docs": kpi_archived_docs,
        "kpi_departments": kpi_departments,
        "kpi_users": kpi_users,
        "kpi_activities": kpi_activities,

        "weekly_labels": weekly_labels,
        "weekly_values": weekly_values,

        "action_labels": action_labels,
        "action_values": action_values,

        "dept_labels": dept_labels,
        "dept_values": dept_values,

        "recent_docs": recent_docs,
        "recent_activities": recent_activities,

        "risk_disabled_attempts": risk_disabled_attempts,
        "risk_top_user": risk_top_user,
        "risk_top_document": risk_top_document,
        "risk_level": risk_level,
    }

    return render(request, "qms-templates/quality_center.html", context)
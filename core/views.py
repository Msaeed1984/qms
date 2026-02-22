from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.core.cache import cache

from documents.models import Document, DocumentActivity
from accounts.models import Department
from accounts.permissions import (
    is_quality,
    is_admin_role,
    is_employee,
    is_manager,
)

User = get_user_model()


# =========================================================
# 🔐 Permission Helper (Enterprise Clean Layer)
# =========================================================
def can_add_document(user):
    return (
        user.is_authenticated and (
            is_quality(user)
            or is_admin_role(user)
            or user.is_superuser
        )
    )


# =========================================================
# Login View
# =========================================================
class QMSLoginView(LoginView):
    template_name = "qms-templates/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user

        allowed = (
            is_employee(user)
            or is_manager(user)
            or is_quality(user)
            or is_admin_role(user)
            or user.is_superuser
        )

        if not allowed:
            logout(self.request)
            messages.error(
                self.request,
                "Access denied. Your account is not assigned to an authorized group."
            )
            return redirect("core:login")

        return response

    def get_success_url(self):
        user = self.request.user

        if is_employee(user):
            return reverse_lazy("documents:list")

        if can_add_document(user):
            return reverse_lazy("core:quality")

        if is_manager(user):
            return reverse_lazy("documents:list")

        return reverse_lazy("documents:list")


# =========================================================
# Logout
# =========================================================
@require_POST
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("core:login")


# =========================================================
# Home
# =========================================================
@login_required
def home(request):
    user = request.user

    if is_employee(user):
        return redirect("documents:list")

    if can_add_document(user):
        return redirect("core:quality")

    if is_manager(user):
        return redirect("documents:list")

    return render(request, "qms-templates/home.html", {
        "can_add_document": can_add_document(user)
    })


# =========================================================
# Quality Dashboard
# =========================================================
@login_required
def quality(request):

    if not can_add_document(request.user):
        messages.error(request, "Access denied. Quality group only.")
        return redirect("core:home")

    # ================= KPIs =================
    total_docs = Document.objects.count()
    active_docs = Document.objects.filter(status=Document.Status.ACTIVE).count()
    archived_docs = Document.objects.filter(status=Document.Status.ARCHIVED).count()
    disabled_docs = Document.objects.filter(status=Document.Status.DISABLED).count()

    departments_count = Department.objects.filter(is_active=True).count()
    users_count = User.objects.count()
    total_activities = DocumentActivity.objects.count()

    attempts_disabled_total = (
        DocumentActivity.objects
        .filter(
            action=DocumentActivity.Action.ATTEMPT_DISABLED,
            user__isnull=False,
        )
        .count()
    )

        # ========================
    # 🛡 Risk Intelligence (ADD THIS)
    # ========================

    risk_disabled_attempts = attempts_disabled_total

    # Top User (Disabled Attempts Only)
    top_user = (
        DocumentActivity.objects
        .filter(
            action=DocumentActivity.Action.ATTEMPT_DISABLED,
            user__isnull=False,
        )
        .values("user__username")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    risk_top_user = top_user["user__username"] if top_user else "-"

    # Top Document (Disabled Attempts Only)
    top_doc = (
        DocumentActivity.objects
        .filter(
            action=DocumentActivity.Action.ATTEMPT_DISABLED,
        )
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

    # ================= Recent =================
    recent_docs = (
        Document.objects
        .select_related("department")
        .order_by("-updated_at")[:5]
    )

    recent_activities = (
        DocumentActivity.objects
        .select_related("document", "user", "department")
        .order_by("-timestamp")[:8]
    )

    # ================= Department Chart =================
    dept_stats = (
        Document.objects
        .values("department__name")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    dept_labels = [d["department__name"] or "N/A" for d in dept_stats]
    dept_values = [d["total"] for d in dept_stats]

    # ================= 7 Day Trend =================
    today = timezone.now().date()
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]

    weekly_labels = [d.strftime("%d %b") for d in last_7_days]
    weekly_values = [
        DocumentActivity.objects.filter(timestamp__date=day).count()
        for day in last_7_days
    ]

    # ================= Action Distribution =================
    action_stats = (
        DocumentActivity.objects
        .values("action")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    action_labels = []
    action_values = []

    for a in action_stats:
        try:
            action_labels.append(
                DocumentActivity.Action(a["action"]).label
            )
        except Exception:
            action_labels.append(str(a["action"]))

        action_values.append(a["total"])

    context = {
    # KPI
    "kpi_total_docs": total_docs,
    "kpi_active_docs": active_docs,
    "kpi_archived_docs": archived_docs,
    "kpi_disabled_docs": disabled_docs,
    "kpi_departments": departments_count,
    "kpi_users": users_count,
    "kpi_activities": total_activities,
    "kpi_attempts_disabled": attempts_disabled_total,

    # Risk
    "risk_disabled_attempts": risk_disabled_attempts,
    "risk_level": risk_level,
    "risk_top_user": risk_top_user,
    "risk_top_document": risk_top_document,

    # Charts
    "dept_labels": dept_labels,
    "dept_values": dept_values,
    "weekly_labels": weekly_labels,
    "weekly_values": weekly_values,
    "action_labels": action_labels,
    "action_values": action_values,

    # Tables
    "recent_docs": recent_docs,
    "recent_activities": recent_activities,

    "can_add_document": True,
    }
    
    return render(request, "qms-templates/quality_center.html", context)


# =========================================================
# 🔐 Security Metrics API
# =========================================================
@login_required
def security_metrics_api(request):

    if not can_add_document(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    disabled_docs = Document.objects.filter(
        status=Document.Status.DISABLED
    ).count()

    attempts_disabled_total = (
        DocumentActivity.objects
        .filter(
            action=DocumentActivity.Action.ATTEMPT_DISABLED,
            user__isnull=False,
        )
        .count()
    )

    top_user = (
        DocumentActivity.objects
        .filter(
            action=DocumentActivity.Action.ATTEMPT_DISABLED,
            user__isnull=False,
        )
        .values("user__username")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    return JsonResponse({
        "disabled_docs": disabled_docs,
        "attempts": attempts_disabled_total,
        "top_user": top_user["user__username"] if top_user else "-"
    })


# =========================================================
# 📊 Enterprise KPI Range API (Clean + Structured Version)
# =========================================================
@login_required
def kpi_enterprise_api(request):

    if not can_add_document(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    range_key = request.GET.get("range", "30")

    days_map = {
        "1": 1,
        "7": 7,
        "30": 30,
        "90": 90,
        "365": 365,
    }

    from django.utils.timezone import localtime
    now = localtime()

    # ==============================
    # Time Range Logic
    # ==============================
    if range_key == "1":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        previous_start = start - timedelta(days=1)
    else:
        days = days_map.get(range_key, 30)
        start = now - timedelta(days=days)
        previous_start = start - timedelta(days=days)

    # ==============================
    # Documents KPI (Total ثابت + Change حسب Range)
    # ==============================
    total_documents = Document.objects.count()

    range_documents = Document.objects.filter(
        created_at__gte=start
    ).count()

    prev_range_documents = Document.objects.filter(
        created_at__gte=previous_start,
        created_at__lt=start
    ).count()

    # ==============================
    # Active KPI (Total ثابت + Change حسب Range)
    # ==============================
    total_active = Document.objects.filter(
        status=Document.Status.ACTIVE
    ).count()

    range_active = Document.objects.filter(
        status=Document.Status.ACTIVE,
        created_at__gte=start
    ).count()

    prev_range_active = Document.objects.filter(
        status=Document.Status.ACTIVE,
        created_at__gte=previous_start,
        created_at__lt=start
    ).count()

    # ==============================
    # Disabled Count (ثابت)
    # ==============================
    total_disabled = Document.objects.filter(
        status=Document.Status.DISABLED
    ).count()

    # ==============================
    # Risk Intelligence (Range Aware)
    # ==============================
    risk_qs = DocumentActivity.objects.filter(
        action=DocumentActivity.Action.ATTEMPT_DISABLED,
        timestamp__gte=start,
        user__isnull=False,
    )

    risk_attempts = risk_qs.count()

    top_user = (
        risk_qs
        .values("user__username")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    top_doc = (
        risk_qs
        .values("document__title")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    risk_top_user = top_user["user__username"] if top_user else "-"
    risk_top_document = top_doc["document__title"] if top_doc else "-"

    # Risk Ratio Logic
    total_activities = DocumentActivity.objects.filter(
        timestamp__gte=start
    ).count()

    risk_ratio = (risk_attempts / total_activities) * 100 if total_activities else 0

    if risk_ratio > 60:
        risk_level = "High"
    elif risk_ratio > 25:
        risk_level = "Medium"
    elif risk_ratio > 0:
        risk_level = "Low"
    else:
        risk_level = "Low"

    # ==============================
    # Helper
    # ==============================
    def calculate_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)

    # ==============================
    # Final JSON
    # ==============================
    data = {
        "documents": total_documents,
        "documents_change": calculate_change(range_documents, prev_range_documents),

        "active_docs": total_active,
        "active_change": calculate_change(range_active, prev_range_active),

        "disabled_docs": total_disabled,

        "archived_docs": Document.objects.filter(
            status=Document.Status.ARCHIVED,
            created_at__gte=start
        ).count(),

        "activities": total_activities,

        "users": User.objects.filter(
            is_active=True
        ).count(),

        "departments": Department.objects.filter(
            is_active=True
        ).count(),

        # Risk
        "risk_attempts": risk_attempts,
        "risk_level": risk_level,
        "risk_top_user": risk_top_user,
        "risk_top_document": risk_top_document,
    }

    return JsonResponse(data)
  
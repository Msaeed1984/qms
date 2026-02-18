from django.contrib import messages
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from documents.models import Document, DocumentActivity
from accounts.models import Department
from accounts.permissions import (
    is_quality,
    is_admin_role,
    is_employee,
    is_manager,
)

User = get_user_model()


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

        # Employees → Documents مباشرة
        if is_employee(user):
            return reverse_lazy("documents:list")

        # Quality / Admin → Dashboard
        if is_quality(user) or is_admin_role(user) or user.is_superuser:
            return reverse_lazy("core:quality")

        return reverse_lazy("core:home")


@require_POST
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("core:login")


@login_required
def home(request):
    # Employees لا يدخلون Home
    if is_employee(request.user):
        return redirect("documents:list")

    # Quality يذهب إلى Dashboard
    if is_quality(request.user):
        return redirect("core:quality")

    return render(request, "qms-templates/home.html")


@login_required
def quality(request):
    # حماية الصفحة
    if not (is_quality(request.user) or is_admin_role(request.user) or request.user.is_superuser):
        messages.error(request, "Access denied. Quality group only.")
        return redirect("core:home")

    # ===============================
    # KPI Calculations
    # ===============================
    total_docs = Document.objects.count()
    active_docs = Document.objects.filter(status=Document.Status.ACTIVE).count()
    archived_docs = Document.objects.filter(status=Document.Status.ARCHIVED).count()
    departments_count = Department.objects.filter(is_active=True).count()
    users_count = User.objects.count()

    total_activities = DocumentActivity.objects.count()

    # ===============================
    # Recent Documents
    # ===============================
    recent_docs = (
        Document.objects
        .select_related("department")
        .order_by("-updated_at")[:5]
    )

    # ===============================
    # Recent Activity Log
    # ===============================
    recent_activities = (
        DocumentActivity.objects
        .select_related("document", "user", "department")
        .order_by("-timestamp")[:8]
    )

    context = {
        # KPIs
        "kpi_total_docs": total_docs,
        "kpi_active_docs": active_docs,
        "kpi_archived_docs": archived_docs,
        "kpi_departments": departments_count,
        "kpi_users": users_count,
        "kpi_activities": total_activities,

        # Tables
        "recent_docs": recent_docs,
        "recent_activities": recent_activities,
    }

    return render(request, "qms-templates/quality_center.html", context)
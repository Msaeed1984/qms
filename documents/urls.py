from django.urls import path
from . import views
from django.views.generic.base import RedirectView

app_name = "documents"

urlpatterns = [
    # =====================================================
    # List Documents
    # =====================================================
    path("", views.document_list, name="list"),

    # =====================================================
    # View Document (open PDF + Activity Log)
    # =====================================================
    path("view/<int:pk>/", views.document_view, name="view"),

    # =====================================================
    # Create / Upload Document
    # =====================================================
    path("create/", views.document_create, name="create"),

    # =====================================================
    # Edit Document
    # =====================================================
    path("edit/<int:pk>/", views.document_edit, name="edit"),

    # =====================================================
    # Delete Document
    # =====================================================
    path("delete/<int:pk>/", views.document_delete, name="delete"),
    path("ajax/department-users/", views.get_department_users, name="department_users"),
    path("audit/", views.audit_dashboard, name="audit_dashboard"),
    path(
        "quality/",RedirectView.as_view(pattern_name="core:quality", permanent=False),),
    ]
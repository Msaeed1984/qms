from django.urls import path
from . import views

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
]
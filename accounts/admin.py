from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from .models import User, Department


# ================================
# Department Admin
# ================================
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")
    list_filter = ("is_active",)
    ordering = ("name",)


# ================================
# User Admin (Enhanced)
# ================================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "department",
        "get_groups",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "department",
        "groups",
        "is_staff",
        "is_active",
    )

    search_fields = ("username", "email")

    # إضافة الحقول الخاصة بنا داخل صفحة المستخدم
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Organization Info", {
            "fields": (
                "department",
                "role",        # إبقاءه مؤقتًا حتى لا نكسر البيانات القديمة
            )
        }),
    )

    filter_horizontal = ("groups", "user_permissions")

    def get_groups(self, obj):
        return ", ".join(g.name for g in obj.groups.all())
    get_groups.short_description = "Groups"
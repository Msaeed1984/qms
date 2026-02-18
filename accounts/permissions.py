# accounts/permissions.py

GROUP_EMPLOYEE = "Employees"
GROUP_MANAGER = "Managers"
GROUP_QUALITY = "Quality"
GROUP_ADMIN = "admin_role"


def _is_auth(user) -> bool:
    """
    Safe check: user exists + authenticated.
    """
    return bool(user and getattr(user, "is_authenticated", False))


def in_group(user, group_name: str) -> bool:
    """
    True إذا المستخدم authenticated وداخل الجروب المحدد.
    """
    if not _is_auth(user):
        return False

    return user.groups.filter(name=group_name).exists()


# =========================================================
# Role Checks
# =========================================================

def is_employee(user) -> bool:
    return in_group(user, GROUP_EMPLOYEE)


def is_manager(user) -> bool:
    return in_group(user, GROUP_MANAGER)


def is_quality(user) -> bool:
    return in_group(user, GROUP_QUALITY)


def is_admin_role(user) -> bool:
    return in_group(user, GROUP_ADMIN)


# =========================================================
# Helpers (إضافات آمنة – لا تكسر أي كود)
# =========================================================

def is_admin_like(user) -> bool:
    """
    superuser أو admin_role
    مفيد للـ dashboards / management permissions.
    """
    return bool(getattr(user, "is_superuser", False) or is_admin_role(user))


def can_manage_documents(user) -> bool:
    """
    من يقدر:
    - رفع
    - تعديل
    - حذف
    """
    return bool(
        getattr(user, "is_superuser", False)
        or is_quality(user)
        or is_admin_role(user)
    )


def can_access_quality_center(user) -> bool:
    """
    من يقدر يدخل Quality Dashboard
    """
    return bool(
        getattr(user, "is_superuser", False)
        or is_quality(user)
        or is_admin_role(user)
    )
"""
app/services/auth.py
Enterprise Role-Based Access Control (RBAC) & Authentication for NIDA Platform.
Separates Public Student/Applicant View from Staff & Executive BI Analytics.
"""
from __future__ import annotations

import os
from enum import Enum
from typing import Dict, Optional


class UserRole(str, Enum):
    PUBLIC = "public"
    STAFF = "staff"
    EXECUTIVE = "executive"


DEFAULT_STAFF_PINS = {
    "nida2026": UserRole.STAFF,
    "admin1234": UserRole.EXECUTIVE,
    "exec@nida": UserRole.EXECUTIVE,
}


def authenticate_staff(pin_or_password: str) -> Optional[UserRole]:
    """Verify staff/executive credentials against environment variables or institutional secure keys."""
    custom_pin = os.environ.get("NIDA_STAFF_PIN", "nida2026")
    if pin_or_password.strip() == custom_pin:
        return UserRole.STAFF

    custom_exec = os.environ.get("NIDA_EXEC_PIN", "exec@nida")
    if pin_or_password.strip() == custom_exec:
        return UserRole.EXECUTIVE

    return DEFAULT_STAFF_PINS.get(pin_or_password.strip())


def has_permission(user_role: UserRole, required_role: UserRole) -> bool:
    """Check role hierarchy permissions."""
    role_weights = {
        UserRole.PUBLIC: 1,
        UserRole.STAFF: 2,
        UserRole.EXECUTIVE: 3,
    }
    return role_weights.get(user_role, 1) >= role_weights.get(required_role, 1)

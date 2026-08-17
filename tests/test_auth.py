"""
tests/test_auth.py
Unit tests for Role-Based Access Control (RBAC) & Authentication.
"""
import pytest
from app.services.auth import UserRole, authenticate_staff, has_permission


class TestAuthRBAC:

    def test_authenticate_staff_success(self):
        assert authenticate_staff("nida2026") == UserRole.STAFF
        assert authenticate_staff("admin1234") == UserRole.EXECUTIVE
        assert authenticate_staff("exec@nida") == UserRole.EXECUTIVE

    def test_authenticate_staff_failure(self):
        assert authenticate_staff("wrong_password") is None
        assert authenticate_staff("") is None

    def test_has_permission(self):
        assert has_permission(UserRole.EXECUTIVE, UserRole.STAFF) is True
        assert has_permission(UserRole.STAFF, UserRole.STAFF) is True
        assert has_permission(UserRole.PUBLIC, UserRole.STAFF) is False

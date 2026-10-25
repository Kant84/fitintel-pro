"""SEC2: RBAC и аудит mutations self-learning."""
import uuid
from unittest.mock import Mock

import pytest

from app.ml.pricing_engine import PricingEngine
from app.ml.self_heal import SelfHeal
from app.models.audit import AuditLog
from app.models.user import User
from app.services.rbac_service import RBACService


def _register_user(client, db_session, prefix):
    """Создать обычного пользователя и вернуть его токен и ORM-запись."""
    login = f"{prefix}_{uuid.uuid4().hex[:8]}"
    response = client.post("/api/v1/auth/register", json={
        "login": login,
        "email": f"{login}@test.ru",
        "password": "testpass123",
    })
    assert response.status_code == 200, response.text

    user = db_session.query(User).filter_by(username=login).one()
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    return headers, user


def _mock_access(monkeypatch, allowed_permissions=()):
    """Сохранить реальный RBAC dependency, управляя только его результатом."""
    checked = []

    def explain_access(self, user_id, permission_code):
        checked.append(permission_code)
        has_access = permission_code in allowed_permissions
        return {
            "user_id": user_id,
            "permission_code": permission_code,
            "has_access": has_access,
            "reason": "Permission granted" if has_access else "Permission denied",
            "granted_via_roles": ["test"] if has_access else [],
            "all_roles": ["test"],
            "all_permissions": list(allowed_permissions),
            "checked_roles_count": 1,
            "checked_permissions_count": len(allowed_permissions),
        }

    monkeypatch.setattr(RBACService, "explain_user_access", explain_access)
    return checked


def _mock_mutations(monkeypatch, pricing_result=True):
    pricing = Mock(return_value=pricing_result)
    healing = Mock(return_value=[{"fix": "credentials", "count": 2}])
    monkeypatch.setattr(PricingEngine, "apply_price", pricing)
    monkeypatch.setattr(SelfHeal, "run_all", healing)
    return pricing, healing


@pytest.mark.parametrize("path", [
    "/api/v1/self-learn/pricing/apply?tariff_id=t-1&new_price=2500",
    "/api/v1/self-learn/self-heal",
])
def test_anonymous_mutations_return_401(
        client, monkeypatch, path):
    pricing, healing = _mock_mutations(monkeypatch)

    response = client.post(path)

    assert response.status_code == 401, response.text
    pricing.assert_not_called()
    healing.assert_not_called()


@pytest.mark.parametrize("path,permission", [
    ("/api/v1/self-learn/pricing/apply?tariff_id=t-1&new_price=2500",
     "tariffs.update"),
    ("/api/v1/self-learn/self-heal", "system.admin"),
])
def test_user_without_permission_gets_403_and_denied_audit(
        client, db_session, monkeypatch, path, permission):
    headers, user = _register_user(client, db_session, "sec2_denied")
    checked = _mock_access(monkeypatch)
    pricing, healing = _mock_mutations(monkeypatch)

    response = client.post(path, headers=headers)

    assert response.status_code == 403, response.text
    assert checked == [permission]
    pricing.assert_not_called()
    healing.assert_not_called()

    denied = db_session.query(AuditLog).filter_by(
        actor_user_id=user.id,
        action="access.check.denied",
    ).all()
    assert any(
        row.after_data.get("permission_code") == permission
        for row in denied
    )


def test_pricing_apply_success_writes_audit(
        client, db_session, monkeypatch):
    headers, user = _register_user(client, db_session, "sec2_price")
    checked = _mock_access(monkeypatch, {"tariffs.update"})
    pricing, healing = _mock_mutations(monkeypatch, pricing_result=True)

    response = client.post(
        "/api/v1/self-learn/pricing/apply",
        params={"tariff_id": "tariff-not-uuid", "new_price": 2500.50},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["applied"] is True
    assert checked == ["tariffs.update"]
    pricing.assert_called_once()
    healing.assert_not_called()

    row = db_session.query(AuditLog).filter_by(
        actor_user_id=user.id,
        action="self_learning.pricing.apply",
        status="success",
    ).one()
    assert row.entity_type == "tariff"
    assert row.after_data == {
        "tariff_id": "tariff-not-uuid",
        "new_price": 2500.50,
    }


def test_pricing_apply_false_has_no_success_audit(
        client, db_session, monkeypatch):
    headers, user = _register_user(client, db_session, "sec2_missing")
    _mock_access(monkeypatch, {"tariffs.update"})
    pricing, _ = _mock_mutations(monkeypatch, pricing_result=False)

    response = client.post(
        "/api/v1/self-learn/pricing/apply",
        params={"tariff_id": "missing", "new_price": 100},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["applied"] is False
    pricing.assert_called_once()
    assert db_session.query(AuditLog).filter_by(
        actor_user_id=user.id,
        action="self_learning.pricing.apply",
    ).count() == 0


def test_self_heal_success_writes_audit(
        client, db_session, monkeypatch):
    headers, user = _register_user(client, db_session, "sec2_heal")
    checked = _mock_access(monkeypatch, {"system.admin"})
    pricing, healing = _mock_mutations(monkeypatch)

    response = client.post(
        "/api/v1/self-learn/self-heal",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["healed"] is True
    assert checked == ["system.admin"]
    healing.assert_called_once()
    pricing.assert_not_called()

    row = db_session.query(AuditLog).filter_by(
        actor_user_id=user.id,
        action="self_learning.self_heal.run",
        status="success",
    ).one()
    assert row.entity_type == "system"
    assert row.after_data == {
        "fixes_count": 1,
        "fixes": [{"fix": "credentials", "count": 2}],
    }
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


class Rec:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_delete_project_route_removes_owned_project_and_point(monkeypatch):
    from routers.project import delete_project

    calls = {"deleted": []}

    class FakePrisma:
        def __init__(self):
            self.project = SimpleNamespace(find_first=self.find_first, delete=self.delete_project)
            self.point = SimpleNamespace(delete=self.delete_point)

        def find_first(self, where):
            assert where == {"id": "abc", "userId": 9}
            return Rec(id="abc", pointId=4, userId=9)

        def delete_project(self, where):
            calls["deleted"].append(("project", where))

        def delete_point(self, where):
            calls["deleted"].append(("point", where))

    monkeypatch.setattr("routers.project.prisma", FakePrisma())
    response = delete_project("abc", user=SimpleNamespace(id=9))
    body = json.loads(response.body.decode("utf-8"))
    assert response.status_code == 200
    assert body == {"ok": True, "id": "abc"}
    assert calls["deleted"] == [("project", {"id": "abc"}), ("point", {"id": 4})]


def test_delete_project_route_404_for_foreign_or_missing(monkeypatch):
    from routers.project import delete_project

    class FakePrisma:
        def __init__(self):
            self.project = SimpleNamespace(find_first=lambda where: None)

    monkeypatch.setattr("routers.project.prisma", FakePrisma())
    with pytest.raises(HTTPException) as exc:
        delete_project("missing", user=SimpleNamespace(id=1))
    assert exc.value.status_code == 404

import pytest

from app.middleware import route_template

TASK_ID = "5f0c7f3e-0d8a-4a4e-9c55-2f4c1b9e8a10"


@pytest.mark.parametrize(
    ("path", "path_params", "template"),
    [
        ("/api/v1/auth/me", {}, "/api/v1/auth/me"),
        (f"/api/v1/tasks/{TASK_ID}/position", {"task_id": TASK_ID}, "/api/v1/tasks/{task_id}/position"),
    ],
)
def test_route_template_names_the_path_parameters(path: str, path_params: dict[str, str], template: str) -> None:
    assert route_template(path, path_params) == template

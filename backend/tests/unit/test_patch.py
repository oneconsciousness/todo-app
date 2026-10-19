import pytest

from app.domain.errors import EmptyPatch
from app.domain.patch import apply_patch
from app.domain.types import TaskPatch


def test_apply_patch_keeps_only_sent_fields() -> None:
    assert apply_patch(TaskPatch(title="Buy milk", completed=True)) == {"title": "Buy milk", "completed": True}


def test_apply_patch_keeps_a_null_due_date_to_clear_it() -> None:
    assert apply_patch(TaskPatch(due_date=None)) == {"due_date": None}


def test_apply_patch_rejects_an_empty_patch() -> None:
    with pytest.raises(EmptyPatch):
        apply_patch(TaskPatch())

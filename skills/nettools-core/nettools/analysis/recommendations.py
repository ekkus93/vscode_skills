from __future__ import annotations

from ..models import NextAction


def build_next_action(skill: str, reason: str, *, include: bool = True) -> NextAction | None:
    if not include:
        return None
    return NextAction(skill=skill, reason=reason)


def build_next_actions(candidates: list[tuple[str, str, bool]]) -> list[NextAction]:
    actions: list[NextAction] = []
    seen: set[str] = set()
    for skill, reason, include in candidates:
        action = build_next_action(skill, reason, include=include)
        if action is None or action.skill in seen:
            continue
        seen.add(action.skill)
        actions.append(action)
    return actions

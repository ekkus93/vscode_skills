from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillRequirements:
    name: str
    path: str
    registered: bool
    python_packages: tuple[str, ...]
    depends_on_skills: tuple[str, ...]


def _expect_dict(payload: object, context: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError(f"{context} must be a JSON object")
    normalized: dict[str, object] = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            raise ValueError(f"{context} keys must be strings")
        normalized[key] = value
    return normalized


def _expect_str(payload: dict[str, object], key: str, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{context}.{key} must be a string")
    return value


def _expect_bool(payload: dict[str, object], key: str, context: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{context}.{key} must be a boolean")
    return value


def _expect_str_list(payload: dict[str, object], key: str, context: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{context}.{key} must be a list")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{context}.{key} entries must be strings")
        normalized.append(item)
    return normalized


def load_skill_requirements(manifest_path: Path) -> dict[str, SkillRequirements]:
    raw_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = _expect_dict(raw_payload, "manifest")
    skills_payload = _expect_dict(manifest.get("skills"), "manifest.skills")

    requirements: dict[str, SkillRequirements] = {}
    for skill_name, entry in skills_payload.items():
        context = f"manifest.skills.{skill_name}"
        skill_entry = _expect_dict(entry, context)
        requires_entry = _expect_dict(skill_entry.get("requires"), f"{context}.requires")
        requirements[skill_name] = SkillRequirements(
            name=skill_name,
            path=_expect_str(skill_entry, "path", context),
            registered=_expect_bool(skill_entry, "registered", context),
            python_packages=tuple(_expect_str_list(requires_entry, "python_packages", context)),
            depends_on_skills=tuple(_expect_str_list(skill_entry, "depends_on_skills", context)),
        )
    return requirements


def resolve_skill_dependency_closure(
    skill_name: str, skill_requirements: dict[str, SkillRequirements]
) -> list[str]:
    if skill_name not in skill_requirements:
        raise KeyError(f"Unknown skill: {skill_name}")

    resolved: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(current_skill: str) -> None:
        if current_skill in visited:
            return
        if current_skill in visiting:
            cycle = " -> ".join([*sorted(visiting), current_skill])
            raise ValueError(f"Dependency cycle detected: {cycle}")
        if current_skill not in skill_requirements:
            raise KeyError(f"Unknown dependent skill: {current_skill}")

        visiting.add(current_skill)
        for dependency in skill_requirements[current_skill].depends_on_skills:
            visit(dependency)
        visiting.remove(current_skill)
        visited.add(current_skill)
        resolved.append(current_skill)

    visit(skill_name)
    return resolved


def collect_python_packages(
    skill_names: list[str], skill_requirements: dict[str, SkillRequirements]
) -> list[str]:
    packages = {
        package
        for skill_name in skill_names
        for package in skill_requirements[skill_name].python_packages
    }
    return sorted(packages)


def build_repo_python_packages(skill_requirements: dict[str, SkillRequirements]) -> list[str]:
    packages = {
        package
        for skill in skill_requirements.values()
        if skill.registered
        for package in skill.python_packages
    }
    return sorted(packages)


def render_requirements_text(
    *,
    header_lines: list[str],
    packages: list[str],
) -> str:
    lines = [f"# {line}" for line in header_lines]
    lines.append("")
    if packages:
        lines.extend(packages)
    else:
        lines.append("# No required Python packages for this scope.")
    lines.append("")
    return "\n".join(lines)


def write_requirements_outputs(
    *,
    manifest_path: Path,
    repo_root: Path,
    requirements_path: Path,
    per_skill_dir: Path,
) -> None:
    skill_requirements = load_skill_requirements(manifest_path)

    repo_packages = build_repo_python_packages(skill_requirements)
    requirements_path.write_text(
        render_requirements_text(
            header_lines=[
                "Generated from skills/install-manifest.json for whole-repo development.",
                "Use per-skill files under requirements/skills for partial OpenClaw installs.",
            ],
            packages=repo_packages,
        ),
        encoding="utf-8",
    )

    per_skill_dir.mkdir(parents=True, exist_ok=True)
    for skill_name in sorted(skill_requirements):
        skill = skill_requirements[skill_name]
        if not skill.registered:
            continue
        closure = resolve_skill_dependency_closure(skill_name, skill_requirements)
        packages = collect_python_packages(closure, skill_requirements)
        output_path = per_skill_dir / f"{skill_name}.txt"
        output_path.write_text(
            render_requirements_text(
                header_lines=[
                    f"Generated from skills/install-manifest.json for the {skill_name} skill.",
                    f"Resolved skills: {', '.join(closure)}",
                    (
                        "Non-Python dependencies and skill-folder dependencies "
                        "remain in the install manifest."
                    ),
                ],
                packages=packages,
            ),
            encoding="utf-8",
        )

    readme_path = repo_root / "requirements" / "README.md"
    readme_path.write_text(
        "\n".join(
            [
                "# Generated Requirements",
                "",
                (
                    "This directory contains generated Python dependency views "
                    "derived from skills/install-manifest.json."
                ),
                "",
                "Files:",
                (
                    "- requirements.txt at the repo root: union of required "
                    "Python packages for all registered skills"
                ),
                (
                    "- requirements/skills/<skill>.txt: transitive Python "
                    "packages required for one registered skill"
                ),
                "",
                "Important:",
                "- These files only describe Python packages.",
                (
                    "- Use skills/install-manifest.json for binaries, node "
                    "packages, post-install steps, and dependent skill folders."
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate repo-level and per-skill Python requirements from "
            "skills/install-manifest.json."
        )
    )
    parser.add_argument(
        "--manifest",
        default="skills/install-manifest.json",
        help="Path to the install manifest JSON file.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root where requirements outputs should be written.",
    )
    parser.add_argument(
        "--requirements-path",
        default="requirements.txt",
        help="Output path for the whole-repo requirements file, relative to repo root.",
    )
    parser.add_argument(
        "--per-skill-dir",
        default="requirements/skills",
        help="Output directory for per-skill requirements files, relative to repo root.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    manifest_path = (repo_root / args.manifest).resolve()
    requirements_path = (repo_root / args.requirements_path).resolve()
    per_skill_dir = (repo_root / args.per_skill_dir).resolve()

    write_requirements_outputs(
        manifest_path=manifest_path,
        repo_root=repo_root,
        requirements_path=requirements_path,
        per_skill_dir=per_skill_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Scientific skills for the EcoSeek agent.

Skills are loaded from Markdown definitions that Hermes can use as
system prompts or procedural knowledge. Built on patterns from
the alrobles/knowledgebase.

Structure:
- Each skill is a .md file in the definitions/ directory
- Skills have YAML frontmatter with name, description, and triggers
- The SkillLoader reads and parses them into structured objects
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Skill:
    """A loaded skill with frontmatter and body."""

    name: str
    description: str
    category: str = "general"
    triggers: List[str] = field(default_factory=list)
    body: str = ""
    source_path: Optional[str] = None


class SkillLoader:
    """Load skills from the definitions/ directory.

    Usage:
        loader = SkillLoader()
        skills = loader.list_all()
        sdm_skill = loader.get("sdm")
    """

    def __init__(self, skill_dir: Optional[str] = None):
        if skill_dir is None:
            skill_dir = str(Path(__file__).parent / "definitions")
        self._skill_dir = skill_dir
        self._skills: Dict[str, Skill] = {}
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._loaded = True
        self._load_all()

    def _load_all(self):
        """Load all .md files from the definitions directory."""
        skill_path = Path(self._skill_dir)
        if not skill_path.exists():
            return

        for md_file in sorted(skill_path.glob("*.md")):
            try:
                skill = self._parse_skill_file(md_file)
                self._skills[skill.name] = skill
            except Exception:
                pass

    def _parse_skill_file(self, path: Path) -> Skill:
        """Parse a skill markdown file with YAML frontmatter."""
        content = path.read_text(encoding="utf-8")

        # Parse YAML frontmatter if present
        name = path.stem.replace("_", "-").replace(" ", "-")
        description = ""
        category = "general"
        triggers: List[str] = []
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                body = parts[2].strip()

                for line in frontmatter.split("\n"):
                    line = line.strip()
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("description:"):
                        description = line.split(":", 1)[1].strip()
                    elif line.startswith("category:"):
                        category = line.split(":", 1)[1].strip()
                    elif line.startswith("triggers:"):
                        triggers_str = line.split(":", 1)[1].strip()
                        triggers = [
                            t.strip().strip("'\"")
                            for t in triggers_str.strip("[]").split(",")
                            if t.strip()
                        ]

        return Skill(
            name=name,
            description=description,
            category=category,
            triggers=triggers,
            body=body,
            source_path=str(path),
        )

    def get(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        self._ensure_loaded()
        return self._skills.get(name)

    def list_all(self) -> List[Skill]:
        """List all loaded skills."""
        self._ensure_loaded()
        return list(self._skills.values())

    def list_by_category(self, category: str) -> List[Skill]:
        """List skills in a category."""
        self._ensure_loaded()
        return [s for s in self._skills.values() if s.category == category]

    def as_system_prompt(self, skill_names: Optional[List[str]] = None) -> str:
        """Build a combined system prompt from loaded skills.

        Args:
            skill_names: Specific skills to include. None = all.

        Returns:
            Combined system prompt string.
        """
        self._ensure_loaded()

        skills = self._skills.values()
        if skill_names:
            skills = [self._skills[n] for n in skill_names if n in self._skills]

        parts = ["You are EcoSeek, a scientific agent for ecology.\n"]
        parts.append("Available skills:\n")

        for skill in skills:
            parts.append(f"--- {skill.name} ---")
            parts.append(skill.body)
            parts.append("")

        return "\n".join(parts)

    @property
    def skill_count(self) -> int:
        self._ensure_loaded()
        return len(self._skills)

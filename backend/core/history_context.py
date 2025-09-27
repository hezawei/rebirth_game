from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .history_data import HISTORICAL_FIGURES, GENERIC_THEMES


@dataclass
class HistoryProfile:
    name: str
    era: str
    personas: List[str]
    anchors: List[str]
    primary_conflicts: List[str]
    recommended_chapter_count: int

    @property
    def as_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "era": self.era,
            "personas": self.personas,
            "anchors": self.anchors,
            "primary_conflicts": self.primary_conflicts,
            "recommended_chapter_count": self.recommended_chapter_count,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "HistoryProfile":
        return cls(
            name=str(payload.get("name", "未知角色")),
            era=str(payload.get("era", "未知时代")),
            personas=list(payload.get("personas", [])) or ["神秘旅者"],
            anchors=list(payload.get("anchors", [])) or ["寻找关键历史事件"],
            primary_conflicts=list(payload.get("primary_conflicts", [])) or ["创造一个与众不同的篇章"],
            recommended_chapter_count=int(payload.get("recommended_chapter_count", 9)),
        )

    def to_context_block(self) -> str:
        return "\n".join(
            [
                f"角色定位：{self.name}",
                f"所属时代：{self.era}",
                "人物特质：" + "；".join(self.personas),
                "关键历史锚点：" + "；".join(self.anchors),
                "主要矛盾：" + "；".join(self.primary_conflicts),
                f"推荐章节总数：至少 {self.recommended_chapter_count} 章",
            ]
        )


def _match_historical_profile(wish: str) -> Optional[HistoryProfile]:
    for key, payload in HISTORICAL_FIGURES.items():
        if key in wish:
            return HistoryProfile(
                name=key,
                era=payload["era"],
                personas=payload["personas"],
                anchors=payload["anchors"],
                primary_conflicts=payload["primary_conflicts"],
                recommended_chapter_count=payload["recommended_chapter_count"],
            )
    return None


def build_history_profile(wish: str) -> HistoryProfile:
    wish = (wish or "").strip()
    profile = _match_historical_profile(wish)
    if profile:
        return profile

    # fallback to themed defaults
    theme = GENERIC_THEMES["历史"]
    return HistoryProfile(
        name=wish or "未知的历史人物",
        era=theme["era"],
        personas=theme["personas"],
        anchors=theme["anchors"],
        primary_conflicts=theme["primary_conflicts"],
        recommended_chapter_count=theme["recommended_chapter_count"],
    )


def build_prompt_context(wish: str) -> Dict[str, object]:
    profile = build_history_profile(wish)
    return {
        "profile": profile,
        "profile_dict": profile.as_dict,
        "context_block": profile.to_context_block(),
        "anchor_events": profile.anchors,
        "recommended_chapter_count": profile.recommended_chapter_count,
    }

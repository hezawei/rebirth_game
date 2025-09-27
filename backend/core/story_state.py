from __future__ import annotations

from typing import Dict, List, Optional

from database import crud
from database.models import StoryNode
from backend import schemas


def build_story_history(db, node: StoryNode) -> List[Dict[str, str]]:
    """重建从根节点到指定节点的对话历史, 用于提示词上下文."""
    path_nodes: List[StoryNode] = []
    cursor = node
    visited = set()

    while cursor is not None:
        if cursor.id in visited:
            break
        visited.add(cursor.id)
        path_nodes.append(cursor)
        if cursor.parent_id is None:
            break
        cursor = crud.get_node_by_id(db, cursor.parent_id)

    path_nodes.reverse()
    history: List[Dict[str, str]] = []
    for item in path_nodes:
        history.append({"role": "assistant", "content": item.story_text})
        if item.user_choice:
            history.append({"role": "user", "content": f"我选择了：{item.user_choice}"})
    return history


def extract_chapter_number(node: StoryNode) -> int:
    metadata = node.get_metadata()
    number = metadata.get("chapter_number") if isinstance(metadata, dict) else None
    if isinstance(number, int) and number > 0:
        return number
    return 1


def build_story_segment_from_node(
    db,
    node: StoryNode,
    *,
    source: Optional[str] = None,
    override_chapter: Optional[int] = None,
) -> schemas.story.StorySegment:
    chapter_number = override_chapter or extract_chapter_number(node)
    metadata = node.get_metadata()
    if not isinstance(metadata, dict):
        metadata = {}
    metadata = {**metadata}
    metadata["chapter_number"] = chapter_number
    if source:
        metadata["source"] = source

    return schemas.story.StorySegment(
        session_id=node.session_id,
        node_id=node.id,
        text=node.story_text,
        choices=node.get_choices(),
        image_url=node.image_url,
        success_rate=node.success_rate,
        metadata=metadata,
    )

"""X3D scene manipulation: modify, remove, and move nodes.

Completes the CRUD cycle for X3D scenes. Works with parsed lxml trees
and returns serialized XML strings.
"""

import logging
from lxml import etree

from src.file_ops import parse_x3d_source, find_scene

logger = logging.getLogger(__name__)


def _serialize(tree: etree._Element) -> str:
    """Serialize an lxml tree back to an X3D XML string."""
    return etree.tostring(
        tree, xml_declaration=True, encoding="UTF-8", pretty_print=True
    ).decode()


def _find_node_by_def(scene: etree._Element, def_name: str) -> etree._Element | None:
    """Find a node by DEF name within a scene tree."""
    matches = scene.xpath(f"//*[@DEF='{def_name}']")
    return matches[0] if matches else None


def _find_node_by_type(scene: etree._Element, node_type: str, index: int) -> tuple[etree._Element | None, str]:
    """Find a node by type + index. Returns (element, error_message)."""
    matches = list(scene.iter(node_type))
    if not matches:
        return None, (
            f"No '{node_type}' node found in the scene. "
            f"Use x3d_scene_stats to see which node types are present."
        )
    if index >= len(matches):
        return None, (
            f"Index {index} out of range. The scene contains {len(matches)} "
            f"'{node_type}' node(s) (valid indices: 0-{len(matches) - 1})."
        )
    return matches[index], ""


def _available_defs(scene: etree._Element) -> list[str]:
    """Return all DEF names in the scene."""
    return [el.get("DEF") for el in scene.xpath("//*[@DEF]")]


def _is_descendant_of(node: etree._Element, ancestor: etree._Element) -> bool:
    """Check if node is a descendant of ancestor."""
    parent = node.getparent()
    while parent is not None:
        if parent is ancestor:
            return True
        parent = parent.getparent()
    return False


# ─────────────────────────────────────────
# modify_node
# ─────────────────────────────────────────

def modify_node(source: str, def_name: str, field_changes: dict) -> str:
    """Modify attribute values on a DEF'd node in an X3D scene.

    Args:
        source: File path or inline X3D XML string.
        def_name: DEF name of the node to modify.
        field_changes: Dict of field_name -> new_value (string values).

    Returns the complete modified X3D document, or an error message.
    """
    if not def_name:
        return "A def_name is required to identify the node to modify."

    if not field_changes:
        return "No field_changes provided. Pass a dict of field=value pairs to modify."

    try:
        tree = parse_x3d_source(source)
    except ValueError as e:
        return str(e)

    try:
        scene = find_scene(tree)
    except ValueError as e:
        return str(e)

    target = _find_node_by_def(scene, def_name)
    if target is None:
        defs = _available_defs(scene)
        if defs:
            return (
                f"No node with DEF='{def_name}' found. "
                f"Available DEF names: {', '.join(defs)}. "
                f"Use x3d_list_defs to see all named nodes."
            )
        return (
            f"No node with DEF='{def_name}' found. The scene has no DEF'd nodes. "
            f"Use x3d_parse_scene to see the scene structure."
        )

    # Apply changes
    for field_name, value in field_changes.items():
        target.set(field_name, str(value))

    return _serialize(tree)


# ─────────────────────────────────────────
# remove_node
# ─────────────────────────────────────────

def remove_node(
    source: str,
    def_name: str = "",
    node_type: str = "",
    index: int = 0,
) -> str:
    """Remove a node (and its children) from an X3D scene.

    Identifies the target by DEF name, or by node_type + index.
    Returns the modified X3D document.
    """
    if not def_name and not node_type:
        return (
            "Specify either def_name or node_type to identify the node to remove. "
            "Use x3d_list_defs to see named nodes, or x3d_scene_stats to see node type counts."
        )

    try:
        tree = parse_x3d_source(source)
    except ValueError as e:
        return str(e)

    try:
        scene = find_scene(tree)
    except ValueError as e:
        return str(e)

    if def_name:
        target = _find_node_by_def(scene, def_name)
        if target is None:
            defs = _available_defs(scene)
            if defs:
                return (
                    f"No node with DEF='{def_name}' found. "
                    f"Available DEF names: {', '.join(defs)}"
                )
            return f"No node with DEF='{def_name}' found. The scene has no DEF'd nodes."
    else:
        target, error = _find_node_by_type(scene, node_type, index)
        if target is None:
            return error

    # Guard: don't remove the Scene element itself
    if target is scene:
        return "Cannot remove the <Scene> element itself."

    parent = target.getparent()
    if parent is None:
        return "Cannot remove the root element."

    parent.remove(target)
    return _serialize(tree)


# ─────────────────────────────────────────
# move_node
# ─────────────────────────────────────────

def move_node(source: str, def_name: str, new_parent_def: str = "") -> str:
    """Reparent a DEF'd node to a new parent in the scene.

    If new_parent_def is empty, moves the node to be a direct child of <Scene>.
    """
    if not def_name:
        return "A def_name is required to identify the node to move."

    try:
        tree = parse_x3d_source(source)
    except ValueError as e:
        return str(e)

    try:
        scene = find_scene(tree)
    except ValueError as e:
        return str(e)

    target = _find_node_by_def(scene, def_name)
    if target is None:
        defs = _available_defs(scene)
        if defs:
            return (
                f"No node with DEF='{def_name}' found. "
                f"Available DEF names: {', '.join(defs)}"
            )
        return f"No node with DEF='{def_name}' found. The scene has no DEF'd nodes."

    # Determine new parent
    if new_parent_def:
        if new_parent_def == def_name:
            return f"Cannot move a node under itself (DEF='{def_name}')."

        new_parent = _find_node_by_def(scene, new_parent_def)
        if new_parent is None:
            defs = _available_defs(scene)
            return (
                f"New parent DEF='{new_parent_def}' not found. "
                f"Available DEF names: {', '.join(defs)}"
            )

        # Check for cycle: new_parent must not be a descendant of target
        if _is_descendant_of(new_parent, target):
            return (
                f"Cannot move DEF='{def_name}' under DEF='{new_parent_def}' — "
                f"'{new_parent_def}' is a descendant of '{def_name}', which would "
                f"create a cycle in the scene graph."
            )
    else:
        new_parent = scene

    # Detach from current parent
    old_parent = target.getparent()
    if old_parent is None:
        return "Cannot move the root element."

    if old_parent is new_parent:
        return (
            f"Node DEF='{def_name}' is already a child of "
            f"{'<Scene>' if new_parent is scene else f'DEF={new_parent_def!r}'}."
        )

    old_parent.remove(target)
    new_parent.append(target)

    return _serialize(tree)

"""X3D file operations: parsing, analysis, and node extraction.

Reads existing X3D content (from files or XML strings) and provides
structured views of the scene graph, statistics, DEF listings, and
node extraction.
"""

import logging
import os
from collections import Counter
from lxml import etree

from src.x3duom_loader import get_x3duom

logger = logging.getLogger(__name__)

# Attributes to always show in the tree view (when present and non-empty)
_TREE_ATTRS = {
    "DEF", "USE", "url", "description",
    # Geometry
    "size", "radius", "height", "bottomRadius", "topRadius",
    "point", "coordIndex",
    # Transforms
    "translation", "rotation", "scale", "center",
    # Appearance
    "diffuseColor", "emissiveColor", "specularColor", "transparency",
    "ambientIntensity", "shininess",
    # Lighting
    "color", "direction", "intensity", "location",
    "ambientIntensity", "beamWidth", "cutOffAngle",
    # Viewpoint / Navigation
    "position", "orientation", "fieldOfView",
    # Textures
    "repeatS", "repeatT",
}


# ─────────────────────────────────────────
# Shared Infrastructure
# ─────────────────────────────────────────

def _parse_x3d_source(source: str) -> etree._Element:
    """Parse an X3D source (file path or inline XML string) into an lxml tree.

    Raises ValueError with a descriptive message on failure.
    """
    stripped = source.strip()

    if stripped.startswith("<?xml") or stripped.startswith("<X3D") or stripped.startswith("<!DOCTYPE"):
        try:
            parser = etree.XMLParser(remove_blank_text=True)
            return etree.fromstring(stripped.encode(), parser)
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Invalid X3D XML: {e}")

    # Treat as file path
    if not os.path.exists(stripped):
        raise ValueError(
            f"File not found: {stripped}. "
            "Provide either an absolute file path to a .x3d file or inline X3D XML."
        )

    if not stripped.lower().endswith(".x3d"):
        raise ValueError(
            f"Unsupported file extension: {os.path.splitext(stripped)[1]}. "
            "Only XML-encoded X3D files (.x3d) are supported."
        )

    try:
        with open(stripped, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise ValueError(f"Could not read file '{stripped}': {e}")

    try:
        parser = etree.XMLParser(remove_blank_text=True)
        return etree.fromstring(content.encode(), parser)
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML in file '{stripped}': {e}")


def _find_scene(tree: etree._Element) -> etree._Element:
    """Find the <Scene> element in a parsed X3D tree."""
    scene = tree.find("Scene")
    if scene is None:
        raise ValueError(
            "No <Scene> element found in the X3D document. "
            "A valid X3D document requires <X3D><Scene>...</Scene></X3D>."
        )
    return scene


# ─────────────────────────────────────────
# parse_x3d_file
# ─────────────────────────────────────────

def parse_x3d_scene(source: str) -> str:
    """Parse X3D content and return an indented scene graph tree.

    Accepts a file path or inline X3D XML string.
    """
    try:
        tree = _parse_x3d_source(source)
    except ValueError as e:
        return str(e)

    try:
        scene = _find_scene(tree)
    except ValueError as e:
        return str(e)

    profile = tree.get("profile", "unknown")
    version = tree.get("version", "unknown")

    lines = [
        f"# Scene Graph (X3D {version}, profile={profile})",
        "",
    ]

    for child in scene:
        _tree_walk(child, lines, depth=0)

    if not list(scene):
        lines.append("  (empty scene)")

    return "\n".join(lines)


def _tree_walk(el: etree._Element, lines: list[str], depth: int) -> None:
    """Recursively build the indented tree representation."""
    tag = el.tag
    if isinstance(tag, str) and tag.startswith("{"):
        tag = tag.split("}", 1)[1]

    indent = "  " * depth

    parts = [f"{indent}{tag}"]

    def_val = el.get("DEF")
    if def_val:
        parts.append(f'(DEF="{def_val}")')

    use_val = el.get("USE")
    if use_val:
        parts.append(f'(USE="{use_val}")')

    attrs = []
    for attr_name, attr_val in el.attrib.items():
        if attr_name in ("DEF", "USE"):
            continue
        if attr_name.startswith("{") or ":" in attr_name:
            continue
        if attr_name in _TREE_ATTRS:
            display_val = attr_val
            if len(display_val) > 60:
                display_val = display_val[:57] + "..."
            attrs.append(f'{attr_name}="{display_val}"')

    if attrs:
        parts.append(" ".join(attrs))

    lines.append(" ".join(parts))

    for child in el:
        _tree_walk(child, lines, depth + 1)


# ─────────────────────────────────────────
# get_scene_stats
# ─────────────────────────────────────────

def scene_stats(source: str) -> str:
    """Analyze X3D content and return statistics about the scene.

    Accepts a file path or inline X3D XML string.
    """
    try:
        tree = _parse_x3d_source(source)
    except ValueError as e:
        return str(e)

    try:
        scene = _find_scene(tree)
    except ValueError as e:
        return str(e)

    profile = tree.get("profile", "unknown")
    version = tree.get("version", "unknown")

    uom = get_x3duom()

    type_counts: Counter[str] = Counter()
    component_counts: Counter[str] = Counter()
    def_count = 0
    total_count = 0

    for el in scene.iter():
        if el is scene:
            continue
        tag = el.tag
        if isinstance(tag, str) and tag.startswith("{"):
            tag = tag.split("}", 1)[1]

        total_count += 1
        type_counts[tag] += 1

        if el.get("DEF"):
            def_count += 1

        node_info = uom.concrete_nodes.get(tag)
        if node_info:
            component_counts[node_info["component"]] += 1
        else:
            component_counts["(unrecognized)"] += 1

    lines = [
        f"# Scene Statistics",
        f"",
        f"- **X3D version:** {version}",
        f"- **Profile:** {profile}",
        f"- **Total nodes:** {total_count}",
        f"- **Named (DEF'd) nodes:** {def_count}",
        f"- **Anonymous nodes:** {total_count - def_count}",
    ]

    if type_counts:
        lines.append(f"\n## Nodes by Type ({len(type_counts)} distinct types)")
        lines.append("")
        for tag, count in type_counts.most_common():
            lines.append(f"- **{tag}**: {count}")

    if component_counts:
        real_components = {k: v for k, v in component_counts.items() if k != "(unrecognized)"}
        if real_components:
            lines.append(f"\n## Nodes by Component")
            lines.append("")
            for comp, count in sorted(real_components.items(), key=lambda x: -x[1]):
                lines.append(f"- **{comp}**: {count}")

    return "\n".join(lines)


# ─────────────────────────────────────────
# list_def_nodes
# ─────────────────────────────────────────

def list_defs(source: str) -> str:
    """List all DEF'd (named) nodes in an X3D scene.

    Accepts a file path or inline X3D XML string.
    """
    try:
        tree = _parse_x3d_source(source)
    except ValueError as e:
        return str(e)

    try:
        scene = _find_scene(tree)
    except ValueError as e:
        return str(e)

    def_nodes = scene.xpath("//*[@DEF]")

    if not def_nodes:
        return "No DEF'd nodes found in the scene. All nodes are anonymous."

    lines = [f"# DEF'd Nodes ({len(def_nodes)} found)", ""]

    for el in def_nodes:
        tag = el.tag
        if isinstance(tag, str) and tag.startswith("{"):
            tag = tag.split("}", 1)[1]

        def_name = el.get("DEF")
        parent_tag = el.getparent().tag if el.getparent() is not None else "root"
        if isinstance(parent_tag, str) and parent_tag.startswith("{"):
            parent_tag = parent_tag.split("}", 1)[1]

        child_tags = []
        for child in el:
            ctag = child.tag
            if isinstance(ctag, str) and ctag.startswith("{"):
                ctag = ctag.split("}", 1)[1]
            child_tags.append(ctag)

        entry = f"- **{def_name}** ({tag})"
        entry += f" -- parent: {parent_tag}"
        if child_tags:
            entry += f", children: {', '.join(child_tags)}"

        lines.append(entry)

    return "\n".join(lines)


# ─────────────────────────────────────────
# extract_node
# ─────────────────────────────────────────

def extract_node(
    source: str,
    def_name: str = "",
    node_type: str = "",
    index: int = 0,
) -> str:
    """Extract a node subtree from an X3D scene.

    Accepts a file path or inline X3D XML string. Identifies the target
    node by DEF name, or by node type + index (0-based).
    """
    if not def_name and not node_type:
        return (
            "Specify either def_name or node_type to identify the node to extract. "
            "Use x3d_list_defs to see named nodes, or x3d_scene_stats to see node type counts."
        )

    try:
        tree = _parse_x3d_source(source)
    except ValueError as e:
        return str(e)

    try:
        scene = _find_scene(tree)
    except ValueError as e:
        return str(e)

    if def_name:
        matches = scene.xpath(f"//*[@DEF='{def_name}']")
        if not matches:
            all_defs = [
                el.get("DEF") for el in scene.xpath("//*[@DEF]")
            ]
            if all_defs:
                return (
                    f"No node with DEF='{def_name}' found. "
                    f"Available DEF names: {', '.join(all_defs)}"
                )
            return f"No node with DEF='{def_name}' found. The scene has no DEF'd nodes."

        target = matches[0]
    else:
        matches = list(scene.iter(node_type))
        if not matches:
            return (
                f"No '{node_type}' node found in the scene. "
                f"Use x3d_scene_stats to see which node types are present."
            )

        if index >= len(matches):
            return (
                f"Index {index} out of range. The scene contains {len(matches)} "
                f"'{node_type}' node(s) (valid indices: 0-{len(matches) - 1})."
            )

        target = matches[index]

    return etree.tostring(target, pretty_print=True, encoding="unicode").strip()

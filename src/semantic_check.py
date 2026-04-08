"""Semantic validation for X3D scenes beyond XSD schema checks.

Detects common authoring issues: missing geometry, unused DEFs, broken
ROUTE references, empty groups, duplicate DEF names, and more.
"""

import logging
from dataclasses import dataclass, field
from lxml import etree

from src.file_ops import parse_x3d_source, find_scene
from src.x3duom_loader import get_x3duom

logger = logging.getLogger(__name__)

# Node types that are grouping nodes (contain children)
_GROUPING_NODES = {
    "Transform", "Group", "Switch", "Collision", "LOD", "Anchor",
    "Billboard", "StaticGroup", "CADAssembly", "CADLayer", "CADPart",
    "GeoLOD", "EspduTransform", "ReceiverPdu", "SignalPdu",
    "TransmitterPdu", "HAnimJoint", "HAnimSegment", "HAnimSite",
    "LayoutGroup", "ScreenGroup", "Viewport",
}

# Node types that qualify as geometry in a Shape
_GEOMETRY_NODES = None  # Lazy-loaded from X3DUOM


def _get_geometry_nodes() -> set[str]:
    """Get all concrete node names that can serve as geometry in a Shape."""
    global _GEOMETRY_NODES
    if _GEOMETRY_NODES is not None:
        return _GEOMETRY_NODES

    uom = get_x3duom()
    geometry_types = set()

    # Find all nodes that inherit from X3DGeometryNode (directly or indirectly)
    for name, node in uom.concrete_nodes.items():
        if _inherits_from(node, "X3DGeometryNode", uom):
            geometry_types.add(name)

    # Also include common geometry composing nodes
    geometry_types.update({
        "Box", "Sphere", "Cylinder", "Cone", "Text",
        "IndexedFaceSet", "IndexedLineSet", "IndexedTriangleSet",
        "PointSet", "LineSet", "TriangleSet",
        "ElevationGrid", "Extrusion",
    })

    _GEOMETRY_NODES = geometry_types
    return _GEOMETRY_NODES


def _inherits_from(node: dict, target_type: str, uom, visited: set | None = None) -> bool:
    """Check if a node (dict) eventually inherits from target_type."""
    if visited is None:
        visited = set()

    base = node.get("inheritance", "")
    if not base or base in visited:
        return False
    visited.add(base)

    if base == target_type:
        return True

    # Check additional inheritance
    for add_base in node.get("additionalInheritance", []):
        if add_base == target_type:
            return True

    # Walk up
    parent = uom.abstract_node_types.get(base) or uom.abstract_object_types.get(base)
    if parent and _inherits_from(parent, target_type, uom, visited):
        return True

    for add_base in node.get("additionalInheritance", []):
        parent = uom.abstract_node_types.get(add_base) or uom.abstract_object_types.get(add_base)
        if parent and _inherits_from(parent, target_type, uom, visited):
            return True

    return False


@dataclass
class Diagnostic:
    level: str       # "error", "warning", "info"
    check: str       # machine-readable check ID
    message: str     # human-readable description
    node_tag: str = ""
    def_name: str = ""


# ─────────────────────────────────────────
# Individual checkers
# ─────────────────────────────────────────

def _check_shape_completeness(scene: etree._Element) -> list[Diagnostic]:
    """Check that Shape nodes have both geometry and appearance children."""
    diagnostics = []
    geometry_nodes = _get_geometry_nodes()

    for shape in scene.iter("Shape"):
        def_name = shape.get("DEF", "")
        child_tags = {child.tag for child in shape}

        has_geometry = bool(child_tags & geometry_nodes)
        has_appearance = "Appearance" in child_tags

        if not has_geometry:
            diagnostics.append(Diagnostic(
                level="warning",
                check="shape-no-geometry",
                message=f"Shape{f' (DEF={def_name!r})' if def_name else ''} has no geometry child. "
                        f"Add a geometry node like Box, Sphere, or IndexedFaceSet.",
                node_tag="Shape",
                def_name=def_name,
            ))

        if not has_appearance:
            diagnostics.append(Diagnostic(
                level="info",
                check="shape-no-appearance",
                message=f"Shape{f' (DEF={def_name!r})' if def_name else ''} has no Appearance. "
                        f"The shape will render with a default white material.",
                node_tag="Shape",
                def_name=def_name,
            ))

    return diagnostics


def _check_empty_groups(scene: etree._Element) -> list[Diagnostic]:
    """Check for grouping nodes with no children."""
    diagnostics = []

    for tag in _GROUPING_NODES:
        for el in scene.iter(tag):
            if len(el) == 0:
                def_name = el.get("DEF", "")
                diagnostics.append(Diagnostic(
                    level="warning",
                    check="empty-group",
                    message=f"{tag}{f' (DEF={def_name!r})' if def_name else ''} has no children. "
                            f"Empty grouping nodes have no effect.",
                    node_tag=tag,
                    def_name=def_name,
                ))

    return diagnostics


def _check_duplicate_defs(scene: etree._Element) -> list[Diagnostic]:
    """Check for duplicate DEF names."""
    diagnostics = []
    seen: dict[str, str] = {}  # def_name -> first node tag

    for el in scene.iter():
        def_name = el.get("DEF")
        if not def_name:
            continue

        tag = el.tag
        if isinstance(tag, str) and tag.startswith("{"):
            tag = tag.split("}", 1)[1]

        if def_name in seen:
            diagnostics.append(Diagnostic(
                level="error",
                check="duplicate-def",
                message=f"Duplicate DEF name '{def_name}': first used on {seen[def_name]}, "
                        f"also used on {tag}. DEF names must be unique within a scene.",
                node_tag=tag,
                def_name=def_name,
            ))
        else:
            seen[def_name] = tag

    return diagnostics


def _check_def_use_consistency(scene: etree._Element) -> list[Diagnostic]:
    """Check USE references point to existing DEFs, and flag unused DEFs."""
    diagnostics = []

    defs: dict[str, str] = {}  # def_name -> tag
    uses: set[str] = set()

    for el in scene.iter():
        tag = el.tag
        if isinstance(tag, str) and tag.startswith("{"):
            tag = tag.split("}", 1)[1]

        def_name = el.get("DEF")
        if def_name:
            defs[def_name] = tag

        use_name = el.get("USE")
        if use_name:
            uses.add(use_name)

    # USE referencing undefined DEF
    for use_name in uses:
        if use_name not in defs:
            diagnostics.append(Diagnostic(
                level="error",
                check="use-undefined-def",
                message=f"USE='{use_name}' references a DEF that does not exist in this scene. "
                        f"Available DEF names: {', '.join(sorted(defs.keys())) or '(none)'}.",
                def_name=use_name,
            ))

    # DEF defined but never USEd (info, not error — many DEFs are intentional)
    unused = set(defs.keys()) - uses
    for def_name in sorted(unused):
        diagnostics.append(Diagnostic(
            level="info",
            check="unused-def",
            message=f"DEF='{def_name}' ({defs[def_name]}) is defined but never USE'd. "
                    f"This is fine if you reference it via ROUTE or externally.",
            node_tag=defs[def_name],
            def_name=def_name,
        ))

    return diagnostics


def _check_route_validity(scene: etree._Element) -> list[Diagnostic]:
    """Check ROUTE elements for valid DEF references, fields, and type matching."""
    diagnostics = []
    uom = get_x3duom()

    # Build DEF -> (element, node_type) map
    def_map: dict[str, tuple[etree._Element, str]] = {}
    for el in scene.iter():
        def_name = el.get("DEF")
        if def_name:
            tag = el.tag
            if isinstance(tag, str) and tag.startswith("{"):
                tag = tag.split("}", 1)[1]
            def_map[def_name] = (el, tag)

    for route in scene.iter("ROUTE"):
        from_node = route.get("fromNode", "")
        from_field = route.get("fromField", "")
        to_node = route.get("toNode", "")
        to_field = route.get("toField", "")

        # Check fromNode exists
        if from_node not in def_map:
            diagnostics.append(Diagnostic(
                level="error",
                check="route-missing-from-node",
                message=f"ROUTE fromNode='{from_node}' not found. "
                        f"Available DEFs: {', '.join(sorted(def_map.keys())) or '(none)'}.",
            ))
            continue

        # Check toNode exists
        if to_node not in def_map:
            diagnostics.append(Diagnostic(
                level="error",
                check="route-missing-to-node",
                message=f"ROUTE toNode='{to_node}' not found. "
                        f"Available DEFs: {', '.join(sorted(def_map.keys())) or '(none)'}.",
            ))
            continue

        _, from_type = def_map[from_node]
        _, to_type = def_map[to_node]

        # Look up fields in X3DUOM
        from_fields = {f["name"]: f for f in uom.get_all_fields(from_type)}
        to_fields = {f["name"]: f for f in uom.get_all_fields(to_type)}

        # Validate fromField
        from_field_info = from_fields.get(from_field)
        if from_field_info is None:
            diagnostics.append(Diagnostic(
                level="error",
                check="route-invalid-from-field",
                message=f"ROUTE fromField='{from_field}' does not exist on {from_type} "
                        f"(DEF='{from_node}'). "
                        f"Use x3d_node_info('{from_type}') to see available fields.",
            ))
            continue

        # Validate toField
        to_field_info = to_fields.get(to_field)
        if to_field_info is None:
            diagnostics.append(Diagnostic(
                level="error",
                check="route-invalid-to-field",
                message=f"ROUTE toField='{to_field}' does not exist on {to_type} "
                        f"(DEF='{to_node}'). "
                        f"Use x3d_node_info('{to_type}') to see available fields.",
            ))
            continue

        # Check access types
        from_access = from_field_info.get("accessType", "")
        if from_access not in ("outputOnly", "inputOutput"):
            diagnostics.append(Diagnostic(
                level="error",
                check="route-wrong-access-type",
                message=f"ROUTE fromField='{from_field}' on {from_type} has "
                        f"accessType='{from_access}' — must be 'outputOnly' or 'inputOutput' "
                        f"to be a ROUTE source.",
            ))

        to_access = to_field_info.get("accessType", "")
        if to_access not in ("inputOnly", "inputOutput"):
            diagnostics.append(Diagnostic(
                level="error",
                check="route-wrong-access-type",
                message=f"ROUTE toField='{to_field}' on {to_type} has "
                        f"accessType='{to_access}' — must be 'inputOnly' or 'inputOutput' "
                        f"to be a ROUTE destination.",
            ))

        # Check type match
        from_type_name = from_field_info.get("type", "")
        to_type_name = to_field_info.get("type", "")
        if from_type_name and to_type_name and from_type_name != to_type_name:
            diagnostics.append(Diagnostic(
                level="error",
                check="route-type-mismatch",
                message=f"ROUTE type mismatch: {from_node}.{from_field} is {from_type_name} "
                        f"but {to_node}.{to_field} is {to_type_name}. "
                        f"ROUTE requires matching field types.",
            ))

    return diagnostics


def _check_missing_viewpoint(scene: etree._Element) -> list[Diagnostic]:
    """Check if the scene has at least one Viewpoint."""
    viewpoints = list(scene.iter("Viewpoint"))
    if not viewpoints:
        return [Diagnostic(
            level="info",
            check="no-viewpoint",
            message="Scene has no Viewpoint node. The browser will use a default camera. "
                    "Consider adding a Viewpoint for a defined initial view.",
        )]
    return []


# ─────────────────────────────────────────
# Public API
# ─────────────────────────────────────────

_ALL_CHECKS = [
    _check_duplicate_defs,
    _check_def_use_consistency,
    _check_shape_completeness,
    _check_empty_groups,
    _check_route_validity,
    _check_missing_viewpoint,
]


def semantic_check(source: str) -> str:
    """Run all semantic checks on an X3D scene and return a report.

    Accepts a file path or inline X3D XML string.
    """
    try:
        tree = parse_x3d_source(source)
    except ValueError as e:
        return str(e)

    try:
        scene = find_scene(tree)
    except ValueError as e:
        return str(e)

    all_diagnostics: list[Diagnostic] = []
    for check_fn in _ALL_CHECKS:
        all_diagnostics.extend(check_fn(scene))

    if not all_diagnostics:
        return (
            "# Semantic Check: All Clear\n\n"
            "No semantic issues found. The scene looks well-structured.\n"
            "Note: This checks common authoring issues beyond XSD schema validation. "
            "Use validate_x3d for schema-level validation."
        )

    errors = [d for d in all_diagnostics if d.level == "error"]
    warnings = [d for d in all_diagnostics if d.level == "warning"]
    infos = [d for d in all_diagnostics if d.level == "info"]

    lines = [
        f"# Semantic Check Report",
        f"",
        f"Found {len(errors)} error(s), {len(warnings)} warning(s), {len(infos)} info(s).",
        "",
    ]

    if errors:
        lines.append("## Errors")
        lines.append("")
        for d in errors:
            lines.append(f"- **[{d.check}]** {d.message}")
        lines.append("")

    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for d in warnings:
            lines.append(f"- **[{d.check}]** {d.message}")
        lines.append("")

    if infos:
        lines.append("## Info")
        lines.append("")
        for d in infos:
            lines.append(f"- **[{d.check}]** {d.message}")

    return "\n".join(lines)

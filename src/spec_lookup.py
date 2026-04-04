"""X3D specification lookup tools powered by the X3DUOM."""

from src.x3duom_loader import get_x3duom


def get_node_info(node_name: str) -> str:
    """Get detailed information about an X3D node from the spec."""
    uom = get_x3duom()
    node = uom.get_node(node_name)

    if node is None:
        # Try case-insensitive search
        for name in uom.concrete_nodes:
            if name.lower() == node_name.lower():
                node = uom.concrete_nodes[name]
                break

    if node is None:
        suggestions = uom.search_nodes(node_name)
        if suggestions:
            names = ", ".join(s["name"] for s in suggestions[:8])
            return (
                f"Node '{node_name}' not found in the X3D 4.0 specification. "
                f"Did you mean: {names}? "
                f"Use x3d_search_nodes('{node_name}') for a broader search."
            )
        return (
            f"Node '{node_name}' not found in the X3D 4.0 specification. "
            f"Use x3d_search_nodes() to search by keyword, "
            f"or x3d_list_components() to browse all available nodes."
        )

    lines = [
        f"# {node['name']}",
        f"",
        f"{node['appinfo']}",
        f"",
        f"- **Component:** {node['component']} (level {node['componentLevel']})",
        f"- **Inherits from:** {node['inheritance']}",
    ]

    if node["additionalInheritance"]:
        lines.append(f"- **Also implements:** {', '.join(node['additionalInheritance'])}")

    if node["specificationUrl"]:
        lines.append(f"- **Spec:** {node['specificationUrl']}")

    # Get all fields including inherited
    all_fields = uom.get_all_fields(node["name"])

    # Separate own fields from inherited
    own_field_names = {f["name"] for f in node["fields"]}

    own_fields = [f for f in all_fields if f["name"] in own_field_names and not f.get("inheritedFrom")]
    inherited_fields = [f for f in all_fields if f["name"] not in own_field_names or f.get("inheritedFrom")]

    if own_fields:
        lines.append(f"\n## Fields ({len(own_fields)} own, {len(inherited_fields)} inherited)")
        lines.append("")
        for f in sorted(own_fields, key=lambda x: x["name"]):
            lines.append(_format_field(f))

    if inherited_fields:
        lines.append(f"\n## Inherited Fields")
        lines.append("")
        for f in sorted(inherited_fields, key=lambda x: x["name"]):
            lines.append(_format_field(f, brief=True))

    return "\n".join(lines)


def _format_field(field: dict, brief: bool = False) -> str:
    """Format a field dict into a readable string."""
    parts = [f"- **{field['name']}**"]
    parts.append(f"({field['type']}, {field['accessType']})")

    if field.get("default") is not None:
        parts.append(f"default=`{field['default']}`")

    constraints = []
    if field.get("minInclusive") is not None:
        constraints.append(f"min={field['minInclusive']}")
    if field.get("maxInclusive") is not None:
        constraints.append(f"max={field['maxInclusive']}")
    if field.get("acceptableNodeTypes"):
        constraints.append(f"accepts: {field['acceptableNodeTypes']}")
    if constraints:
        parts.append(f"[{', '.join(constraints)}]")

    line = " ".join(parts)

    if not brief and field.get("description"):
        line += f"\n  {field['description']}"

    if not brief and field.get("enumerations"):
        vals = ", ".join(e["value"] for e in field["enumerations"])
        line += f"\n  Allowed values: {vals}"

    return line


def list_nodes_by_component(component_name: str) -> str:
    """List all concrete nodes in a given X3D component."""
    uom = get_x3duom()

    # Case-insensitive match
    matched_component = None
    for comp in uom.components:
        if comp.lower() == component_name.lower():
            matched_component = comp
            break

    if matched_component is None:
        available = sorted(uom.components.keys())
        return (
            f"Component '{component_name}' not found.\n\n"
            f"Available components ({len(available)}):\n"
            + "\n".join(f"- {c} ({len(uom.components[c])} nodes)" for c in available)
        )

    nodes = sorted(uom.components[matched_component])
    lines = [f"# {matched_component} Component ({len(nodes)} nodes)", ""]
    for name in nodes:
        node = uom.concrete_nodes.get(name, {})
        desc = node.get("appinfo", "")[:100]
        lines.append(f"- **{name}**: {desc}")

    return "\n".join(lines)


def list_components() -> str:
    """List all X3D components and their node counts."""
    uom = get_x3duom()
    lines = [f"# X3D 4.0 Components ({len(uom.components)} total)", ""]
    for comp in sorted(uom.components.keys()):
        nodes = uom.components[comp]
        lines.append(f"- **{comp}**: {len(nodes)} nodes")
    return "\n".join(lines)


def list_profiles() -> str:
    """List all X3D profiles with descriptions."""
    uom = get_x3duom()
    lines = [f"# X3D 4.0 Profiles ({len(uom.profiles)} total)", ""]
    for name, appinfo in sorted(uom.profiles.items()):
        desc = appinfo[:200] if appinfo else "No description"
        lines.append(f"- **{name}**: {desc}")
    return "\n".join(lines)


def get_field_type_info(field_type: str) -> str:
    """Explain an X3D field type (SFVec3f, MFFloat, etc.)."""
    # Built-in field type documentation
    field_types = {
        "SFBool": "Single boolean value (true/false)",
        "MFBool": "Multiple boolean values",
        "SFInt32": "Single 32-bit integer",
        "MFInt32": "Multiple 32-bit integers",
        "SFFloat": "Single-precision floating point number",
        "MFFloat": "Multiple single-precision floating point numbers",
        "SFDouble": "Double-precision floating point number",
        "MFDouble": "Multiple double-precision floating point numbers",
        "SFString": "Single UTF-8 string",
        "MFString": "Multiple UTF-8 strings (array)",
        "SFVec2f": "2D vector of single-precision floats (x y)",
        "MFVec2f": "Multiple 2D vectors",
        "SFVec2d": "2D vector of double-precision floats",
        "MFVec2d": "Multiple 2D double-precision vectors",
        "SFVec3f": "3D vector of single-precision floats (x y z)",
        "MFVec3f": "Multiple 3D vectors",
        "SFVec3d": "3D vector of double-precision floats",
        "MFVec3d": "Multiple 3D double-precision vectors",
        "SFVec4f": "4D vector of single-precision floats (x y z w)",
        "MFVec4f": "Multiple 4D vectors",
        "SFVec4d": "4D vector of double-precision floats",
        "MFVec4d": "Multiple 4D double-precision vectors",
        "SFColor": "RGB color, each component in [0,1] range (r g b)",
        "MFColor": "Multiple RGB colors",
        "SFColorRGBA": "RGBA color with alpha, each component in [0,1] (r g b a)",
        "MFColorRGBA": "Multiple RGBA colors",
        "SFRotation": "Axis-angle rotation (x y z angle) where (x,y,z) is unit axis and angle is in radians",
        "MFRotation": "Multiple axis-angle rotations",
        "SFImage": "Uncompressed 2D image data (width height numComponents pixel...)",
        "MFImage": "Multiple uncompressed images",
        "SFNode": "Single X3D node reference (or NULL)",
        "MFNode": "Multiple X3D node references (array of children)",
        "SFTime": "Double-precision time value in seconds since epoch",
        "MFTime": "Multiple time values",
        "SFMatrix3f": "3x3 matrix of single-precision floats (9 values, row-major)",
        "MFMatrix3f": "Multiple 3x3 matrices",
        "SFMatrix3d": "3x3 matrix of double-precision floats",
        "MFMatrix3d": "Multiple 3x3 double-precision matrices",
        "SFMatrix4f": "4x4 matrix of single-precision floats (16 values, row-major)",
        "MFMatrix4f": "Multiple 4x4 matrices",
        "SFMatrix4d": "4x4 matrix of double-precision floats",
        "MFMatrix4d": "Multiple 4x4 double-precision matrices",
    }

    if field_type in field_types:
        prefix = "SF" if field_type.startswith("SF") else "MF"
        cardinality = "Single-valued" if prefix == "SF" else "Multiple-valued"
        return (
            f"# {field_type}\n\n"
            f"- **Cardinality:** {cardinality} ({prefix} = {cardinality.split('-')[0]} Field)\n"
            f"- **Description:** {field_types[field_type]}\n"
        )

    # Check if it's a simple type from the X3DUOM
    uom = get_x3duom()
    st = uom.simple_types.get(field_type)
    if st:
        lines = [
            f"# {st['name']}",
            f"",
            f"- **Base type:** {st['baseType']}",
            f"- **Description:** {st['appinfo']}",
        ]
        if st["enumerations"]:
            lines.append(f"\n**Allowed values:**")
            for e in st["enumerations"]:
                lines.append(f"- `{e['value']}`: {e['appinfo']}")
        return "\n".join(lines)

    return (
        f"Field type '{field_type}' not found. "
        f"X3D field types use the SF (single) or MF (multiple) prefix "
        f"followed by the base type (e.g., SFVec3f, MFString, SFColor, SFRotation). "
        f"Enumeration types from the spec are also supported (e.g., alphaModeChoices)."
    )


def search_nodes(query: str) -> str:
    """Search for X3D nodes by name or description."""
    uom = get_x3duom()
    results = uom.search_nodes(query)

    if not results:
        return (
            f"No nodes found matching '{query}'. "
            f"Try a broader term (e.g., 'light', 'texture', 'geometry') "
            f"or use x3d_list_components() to browse by component."
        )

    lines = [f"# Search results for '{query}' ({len(results)} matches)", ""]
    for r in results[:25]:
        lines.append(f"- **{r['name']}** [{r['component']}]: {r['description']}")

    if len(results) > 25:
        lines.append(f"\n... and {len(results) - 25} more results.")

    return "\n".join(lines)


def check_node_hierarchy(parent_node: str, child_node: str) -> str:
    """Check if a parent-child relationship is valid in X3D."""
    uom = get_x3duom()

    parent = uom.get_node(parent_node)
    if parent is None:
        return (
            f"Parent node '{parent_node}' not found in X3D 4.0. "
            f"Use x3d_search_nodes('{parent_node}') to find the correct name."
        )

    child = uom.get_node(child_node)
    if child is None:
        return (
            f"Child node '{child_node}' not found in X3D 4.0. "
            f"Use x3d_search_nodes('{child_node}') to find the correct name."
        )

    # Check which fields of the parent accept nodes
    all_fields = uom.get_all_fields(parent_node)
    accepting_fields = []

    for field in all_fields:
        if field["type"] not in ("SFNode", "MFNode"):
            continue
        acceptable = field.get("acceptableNodeTypes", "")
        if not acceptable:
            continue

        # Check if the child's type matches any acceptable type
        acceptable_types = [t.strip() for t in acceptable.split("|")]
        if _node_matches_types(child_node, acceptable_types, uom):
            accepting_fields.append({
                "fieldName": field["name"],
                "acceptableTypes": acceptable,
            })

    if accepting_fields:
        lines = [
            f"**Valid.** '{child_node}' can be a child of '{parent_node}' via:",
        ]
        for af in accepting_fields:
            lines.append(f"- Field `{af['fieldName']}` (accepts: {af['acceptableTypes']})")
        return "\n".join(lines)

    return (
        f"**Not directly valid.** '{child_node}' is not an accepted child of '{parent_node}' "
        f"based on the X3D 4.0 field type constraints. "
        f"Use x3d_node_info('{parent_node}') to see which node types each field accepts."
    )


def _node_matches_types(node_name: str, acceptable_types: list[str], uom) -> bool:
    """Check if a node matches any of the acceptable abstract or concrete types."""
    # Direct name match
    if node_name in acceptable_types:
        return True

    # Check if the node inherits from any acceptable abstract type
    node = uom.concrete_nodes.get(node_name)
    if node is None:
        return False

    visited = set()
    return _inherits_from_any(node, acceptable_types, uom, visited)


def _inherits_from_any(
    node: dict, acceptable_types: list[str], uom, visited: set
) -> bool:
    """Recursively check if a node inherits from any of the acceptable types."""
    base = node.get("inheritance", "")
    if not base or base in visited:
        return False
    visited.add(base)

    if base in acceptable_types:
        return True

    # Check additional inheritance
    for add_base in node.get("additionalInheritance", []):
        if add_base in acceptable_types:
            return True

    # Walk up the chain
    parent = uom.abstract_node_types.get(base) or uom.abstract_object_types.get(base)
    if parent and _inherits_from_any(parent, acceptable_types, uom, visited):
        return True

    for add_base in node.get("additionalInheritance", []):
        parent = uom.abstract_node_types.get(add_base) or uom.abstract_object_types.get(add_base)
        if parent and _inherits_from_any(parent, acceptable_types, uom, visited):
            return True

    return False

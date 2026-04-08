"""X3D animation and interaction helpers.

Generates TimeSensor + Interpolator + ROUTE chains for common animations,
validates and inserts individual ROUTE statements, and provides reference
documentation for X3D's event-driven animation system.
"""

import logging
from lxml import etree

from src.file_ops import parse_x3d_source, find_scene
from src.x3duom_loader import get_x3duom

logger = logging.getLogger(__name__)


def _serialize(tree: etree._Element) -> str:
    """Serialize an lxml tree back to an X3D XML string."""
    return etree.tostring(
        tree, xml_declaration=True, encoding="UTF-8", pretty_print=True
    ).decode()


# ─────────────────────────────────────────
# Field type → Interpolator mapping
# ─────────────────────────────────────────

# Maps X3D field types to the interpolator node that animates them.
# value_changed_field is the output field name on the interpolator.
_INTERPOLATOR_MAP = {
    "SFRotation": {
        "node": "OrientationInterpolator",
        "value_changed_field": "value_changed",
        "keyValue_hint": "axis-angle rotations (x y z angle), e.g., '0 1 0 0, 0 1 0 3.14159'",
    },
    "SFVec3f": {
        "node": "PositionInterpolator",
        "value_changed_field": "value_changed",
        "keyValue_hint": "3D positions (x y z), e.g., '0 0 0, 5 0 0'",
    },
    "SFVec2f": {
        "node": "PositionInterpolator2D",
        "value_changed_field": "value_changed",
        "keyValue_hint": "2D positions (x y), e.g., '0 0, 5 5'",
    },
    "SFColor": {
        "node": "ColorInterpolator",
        "value_changed_field": "value_changed",
        "keyValue_hint": "RGB colors (r g b) in [0,1], e.g., '1 0 0, 0 0 1'",
    },
    "SFFloat": {
        "node": "ScalarInterpolator",
        "value_changed_field": "value_changed",
        "keyValue_hint": "scalar values, e.g., '0.0, 1.0'",
    },
    "MFVec3f": {
        "node": "CoordinateInterpolator",
        "value_changed_field": "value_changed",
        "keyValue_hint": "coordinate arrays — list all points per keyframe",
    },
    "MFVec2f": {
        "node": "CoordinateInterpolator2D",
        "value_changed_field": "value_changed",
        "keyValue_hint": "2D coordinate arrays",
    },
}

# Mapping of common animation targets to their input field names.
# In X3D, the field name used as a ROUTE destination may differ from
# the attribute name (e.g., "rotation" attribute but "set_rotation" input).
# The X3DUOM lists the canonical field name; for inputOutput fields,
# both "rotation" and "set_rotation" work.
_INPUT_FIELD_ALIASES = {
    "rotation": "rotation",
    "translation": "translation",
    "scale": "scale",
    "diffuseColor": "diffuseColor",
    "emissiveColor": "emissiveColor",
    "transparency": "transparency",
    "position": "position",
    "orientation": "orientation",
}


# ─────────────────────────────────────────
# animate
# ─────────────────────────────────────────

def animate(
    source: str,
    target_def: str,
    field_name: str,
    from_value: str,
    to_value: str,
    duration: float = 5.0,
    loop: bool = True,
) -> str:
    """Generate and insert a complete animation chain into an X3D scene.

    Creates a TimeSensor, the appropriate Interpolator, and ROUTE statements
    to wire them together, then inserts all nodes into the scene.

    Returns the modified X3D document or an error message.
    """
    if not target_def:
        return "target_def is required — the DEF name of the node to animate."
    if not field_name:
        return "field_name is required — the field to animate (e.g., 'rotation', 'translation', 'diffuseColor')."
    if not from_value or not to_value:
        return "Both from_value and to_value are required (space-separated strings)."

    try:
        tree = parse_x3d_source(source)
    except ValueError as e:
        return str(e)

    try:
        scene = find_scene(tree)
    except ValueError as e:
        return str(e)

    # Find the target node
    matches = scene.xpath(f"//*[@DEF='{target_def}']")
    if not matches:
        all_defs = [el.get("DEF") for el in scene.xpath("//*[@DEF]")]
        if all_defs:
            return (
                f"No node with DEF='{target_def}' found. "
                f"Available DEF names: {', '.join(all_defs)}. "
                f"Use x3d_list_defs to see all named nodes."
            )
        return f"No node with DEF='{target_def}' found. The scene has no DEF'd nodes."

    target_el = matches[0]
    target_type = target_el.tag
    if isinstance(target_type, str) and target_type.startswith("{"):
        target_type = target_type.split("}", 1)[1]

    # Look up the field in X3DUOM to determine its type
    uom = get_x3duom()
    all_fields = {f["name"]: f for f in uom.get_all_fields(target_type)}
    field_info = all_fields.get(field_name)

    if field_info is None:
        available = sorted(
            f["name"] for f in all_fields.values()
            if f.get("accessType") in ("inputOutput", "inputOnly")
            and f.get("type") in _INTERPOLATOR_MAP
        )
        return (
            f"Field '{field_name}' not found on {target_type}. "
            f"Animatable fields: {', '.join(available[:15]) or '(none)'}. "
            f"Use x3d_node_info('{target_type}') to see all fields."
        )

    field_type = field_info.get("type", "")
    interp_info = _INTERPOLATOR_MAP.get(field_type)
    if interp_info is None:
        return (
            f"Field '{field_name}' has type {field_type}, which does not have "
            f"a standard interpolator. Supported types: "
            f"{', '.join(sorted(_INTERPOLATOR_MAP.keys()))}."
        )

    # Check access type allows animation
    access_type = field_info.get("accessType", "")
    if access_type not in ("inputOutput", "inputOnly"):
        return (
            f"Field '{field_name}' on {target_type} has accessType='{access_type}'. "
            f"Only inputOutput or inputOnly fields can be animation targets."
        )

    # Generate DEF names for the animation nodes
    timer_def = f"{target_def}_{field_name}_Timer"
    interp_def = f"{target_def}_{field_name}_Interp"
    interp_node_type = interp_info["node"]

    # Create TimeSensor element
    timer_el = etree.SubElement(scene, "TimeSensor")
    timer_el.set("DEF", timer_def)
    timer_el.set("cycleInterval", str(duration))
    timer_el.set("loop", "true" if loop else "false")

    # Create Interpolator element
    interp_el = etree.SubElement(scene, interp_node_type)
    interp_el.set("DEF", interp_def)
    interp_el.set("key", "0 1")
    interp_el.set("keyValue", f"{from_value}, {to_value}")

    # Create ROUTE: TimeSensor.fraction_changed -> Interpolator.set_fraction
    route1 = etree.SubElement(scene, "ROUTE")
    route1.set("fromNode", timer_def)
    route1.set("fromField", "fraction_changed")
    route1.set("toNode", interp_def)
    route1.set("toField", "set_fraction")

    # Create ROUTE: Interpolator.value_changed -> Target.set_<field>
    # Use the canonical field name (inputOutput fields accept both "field" and "set_field")
    dest_field = _INPUT_FIELD_ALIASES.get(field_name, f"set_{field_name}")
    route2 = etree.SubElement(scene, "ROUTE")
    route2.set("fromNode", interp_def)
    route2.set("fromField", interp_info["value_changed_field"])
    route2.set("toNode", target_def)
    route2.set("toField", dest_field)

    return _serialize(tree)


# ─────────────────────────────────────────
# route
# ─────────────────────────────────────────

def add_route(
    source: str,
    from_node: str,
    from_field: str,
    to_node: str,
    to_field: str,
) -> str:
    """Validate and insert a ROUTE statement into an X3D scene.

    Checks that DEF names exist, field names are valid, access types
    are compatible, and field types match before inserting.
    """
    if not all([from_node, from_field, to_node, to_field]):
        return "All four parameters are required: from_node, from_field, to_node, to_field."

    try:
        tree = parse_x3d_source(source)
    except ValueError as e:
        return str(e)

    try:
        scene = find_scene(tree)
    except ValueError as e:
        return str(e)

    uom = get_x3duom()

    # Build DEF -> tag map
    def_map: dict[str, str] = {}
    for el in scene.iter():
        d = el.get("DEF")
        if d:
            tag = el.tag
            if isinstance(tag, str) and tag.startswith("{"):
                tag = tag.split("}", 1)[1]
            def_map[d] = tag

    all_defs = sorted(def_map.keys())

    # Validate fromNode
    from_type = def_map.get(from_node)
    if from_type is None:
        return (
            f"fromNode DEF='{from_node}' not found in the scene. "
            f"Available DEFs: {', '.join(all_defs) or '(none)'}."
        )

    # Validate toNode
    to_type = def_map.get(to_node)
    if to_type is None:
        return (
            f"toNode DEF='{to_node}' not found in the scene. "
            f"Available DEFs: {', '.join(all_defs) or '(none)'}."
        )

    # Look up fields
    from_fields = {f["name"]: f for f in uom.get_all_fields(from_type)}
    to_fields = {f["name"]: f for f in uom.get_all_fields(to_type)}

    from_field_info = from_fields.get(from_field)
    if from_field_info is None:
        available = sorted(
            f["name"] for f in from_fields.values()
            if f.get("accessType") in ("outputOnly", "inputOutput")
        )
        return (
            f"fromField='{from_field}' does not exist on {from_type} (DEF='{from_node}'). "
            f"Output-capable fields: {', '.join(available[:15]) or '(none)'}. "
            f"Use x3d_node_info('{from_type}') to see all fields."
        )

    to_field_info = to_fields.get(to_field)
    if to_field_info is None:
        available = sorted(
            f["name"] for f in to_fields.values()
            if f.get("accessType") in ("inputOnly", "inputOutput")
        )
        return (
            f"toField='{to_field}' does not exist on {to_type} (DEF='{to_node}'). "
            f"Input-capable fields: {', '.join(available[:15]) or '(none)'}. "
            f"Use x3d_node_info('{to_type}') to see all fields."
        )

    # Check access types
    from_access = from_field_info.get("accessType", "")
    if from_access not in ("outputOnly", "inputOutput"):
        return (
            f"Cannot ROUTE from '{from_field}' on {from_type}: accessType is "
            f"'{from_access}', but must be 'outputOnly' or 'inputOutput'."
        )

    to_access = to_field_info.get("accessType", "")
    if to_access not in ("inputOnly", "inputOutput"):
        return (
            f"Cannot ROUTE to '{to_field}' on {to_type}: accessType is "
            f"'{to_access}', but must be 'inputOnly' or 'inputOutput'."
        )

    # Check type match
    from_ft = from_field_info.get("type", "")
    to_ft = to_field_info.get("type", "")
    if from_ft and to_ft and from_ft != to_ft:
        return (
            f"ROUTE type mismatch: {from_node}.{from_field} is {from_ft} "
            f"but {to_node}.{to_field} is {to_ft}. ROUTE requires matching types."
        )

    # All valid — insert the ROUTE
    route_el = etree.SubElement(scene, "ROUTE")
    route_el.set("fromNode", from_node)
    route_el.set("fromField", from_field)
    route_el.set("toNode", to_node)
    route_el.set("toField", to_field)

    return _serialize(tree)


# ─────────────────────────────────────────
# animation_info
# ─────────────────────────────────────────

def animation_info(topic: str = "") -> str:
    """Provide reference documentation about X3D animation.

    Topics: "interpolators", "timesensor", "routes", "examples", or "" for overview.
    """
    topic_lower = topic.lower().strip()

    if topic_lower in ("interpolator", "interpolators"):
        return _interpolators_reference()
    elif topic_lower in ("timesensor", "timer", "time"):
        return _timesensor_reference()
    elif topic_lower in ("route", "routes", "routing"):
        return _routes_reference()
    elif topic_lower in ("example", "examples", "patterns"):
        return _examples_reference()
    else:
        return _overview()


def _overview() -> str:
    return """\
# X3D Animation System Overview

X3D uses an **event-driven** animation system with three key components:

## 1. TimeSensor (the clock)
Generates a `fraction_changed` output (0.0 → 1.0) over a `cycleInterval` duration.
Set `loop="true"` for continuous animation.

## 2. Interpolators (the value generators)
Take a fraction input (0–1) and output interpolated values based on `key`/`keyValue` pairs.
Each field type has a dedicated interpolator:
- **SFRotation** → OrientationInterpolator
- **SFVec3f** → PositionInterpolator (for translation, scale, etc.)
- **SFColor** → ColorInterpolator
- **SFFloat** → ScalarInterpolator (for transparency, intensity, etc.)
- **MFVec3f** → CoordinateInterpolator (for morphing geometry)

## 3. ROUTE (the wiring)
Connects outputs to inputs:
```
TimeSensor.fraction_changed → Interpolator.set_fraction
Interpolator.value_changed → TargetNode.set_fieldName
```

## Quick Start
Use `x3d_animate` to generate a complete animation chain automatically.
Use `x3d_route` to add individual event connections.
Use `x3d_animation_info('examples')` for common patterns.
Use `x3d_animation_info('interpolators')` for the full interpolator reference."""


def _interpolators_reference() -> str:
    uom = get_x3duom()

    # Find all interpolator nodes from X3DUOM
    interp_nodes = []
    for name, node in sorted(uom.concrete_nodes.items()):
        if "Interpolator" in name:
            interp_nodes.append(node)

    lines = [
        "# X3D Interpolator Nodes",
        "",
        f"Found {len(interp_nodes)} interpolator nodes in X3D 4.0:",
        "",
    ]

    for node in interp_nodes:
        desc = node.get("appinfo", "")[:120]
        comp = node.get("component", "")
        lines.append(f"- **{node['name']}** [{comp}]: {desc}")

    lines.extend([
        "",
        "## Common Mappings",
        "",
        "| Target Field Type | Interpolator | Example Fields |",
        "|---|---|---|",
        "| SFRotation | OrientationInterpolator | rotation, orientation |",
        "| SFVec3f | PositionInterpolator | translation, scale, position |",
        "| SFColor | ColorInterpolator | diffuseColor, emissiveColor |",
        "| SFFloat | ScalarInterpolator | transparency, intensity |",
        "| MFVec3f | CoordinateInterpolator | point (on Coordinate) |",
        "",
        "Use `x3d_animate` to auto-select the correct interpolator for a field.",
    ])

    return "\n".join(lines)


def _timesensor_reference() -> str:
    return """\
# TimeSensor Reference

TimeSensor is the animation clock in X3D.

## Key Fields
- **cycleInterval** (SFTime): Duration of one cycle in seconds. Default: 1.0
- **loop** (SFBool): Whether the timer repeats. Default: false
- **enabled** (SFBool): Whether the timer is active. Default: true
- **startTime** (SFTime): When to start (0 = scene load). Default: 0
- **pauseTime** / **resumeTime**: Pause/resume control

## Key Outputs (for ROUTE)
- **fraction_changed** (SFFloat): 0.0 → 1.0 over cycleInterval — connect to Interpolator.set_fraction
- **time** (SFTime): Current time as the timer runs
- **cycleTime** (SFTime): Emitted at the start of each cycle
- **isActive** (SFBool): True while the timer is running

## Example
```xml
<TimeSensor DEF="Clock" cycleInterval="3" loop="true"/>
```

Use `x3d_animate` to automatically create TimeSensors wired to interpolators."""


def _routes_reference() -> str:
    return """\
# ROUTE Reference

ROUTEs connect event outputs to event inputs, forming the wiring of X3D's event system.

## Syntax
```xml
<ROUTE fromNode="SourceDEF" fromField="outputField"
       toNode="DestDEF" toField="inputField"/>
```

## Rules
1. **fromField** must have accessType `outputOnly` or `inputOutput`
2. **toField** must have accessType `inputOnly` or `inputOutput`
3. **Field types must match** (e.g., both SFVec3f, both SFFloat)
4. Both nodes must have **DEF names** (ROUTEs reference nodes by DEF)
5. ROUTEs are placed at the **Scene level** (not inside nodes)

## Fan-out and Fan-in
- One output can ROUTE to **multiple** inputs (fan-out)
- Multiple outputs can ROUTE to **one** input (fan-in — last value wins per frame)

## Common Patterns
```xml
<!-- Timer drives interpolator -->
<ROUTE fromNode="Clock" fromField="fraction_changed"
       toNode="Mover" toField="set_fraction"/>

<!-- Interpolator drives target -->
<ROUTE fromNode="Mover" fromField="value_changed"
       toNode="MyTransform" toField="translation"/>

<!-- Sensor triggers action -->
<ROUTE fromNode="ClickSensor" fromField="isActive"
       toNode="Clock" toField="enabled"/>
```

Use `x3d_route` to validate and insert ROUTEs with type checking."""


def _examples_reference() -> str:
    return """\
# X3D Animation Examples

## 1. Continuous Rotation
Rotate a Transform around the Y axis:
```xml
<TimeSensor DEF="Spinner" cycleInterval="4" loop="true"/>
<OrientationInterpolator DEF="SpinInterp"
    key="0 0.5 1"
    keyValue="0 1 0 0, 0 1 0 3.14159, 0 1 0 6.28318"/>
<ROUTE fromNode="Spinner" fromField="fraction_changed"
       toNode="SpinInterp" toField="set_fraction"/>
<ROUTE fromNode="SpinInterp" fromField="value_changed"
       toNode="MyTransform" toField="rotation"/>
```

## 2. Color Pulse
Animate a Material's diffuseColor from red to blue:
```xml
<TimeSensor DEF="ColorTimer" cycleInterval="2" loop="true"/>
<ColorInterpolator DEF="ColorInterp"
    key="0 0.5 1"
    keyValue="1 0 0, 0 0 1, 1 0 0"/>
<ROUTE fromNode="ColorTimer" fromField="fraction_changed"
       toNode="ColorInterp" toField="set_fraction"/>
<ROUTE fromNode="ColorInterp" fromField="value_changed"
       toNode="MyMaterial" toField="diffuseColor"/>
```

## 3. Path Animation
Move an object along a path:
```xml
<TimeSensor DEF="PathTimer" cycleInterval="8" loop="true"/>
<PositionInterpolator DEF="PathInterp"
    key="0 0.25 0.5 0.75 1"
    keyValue="0 0 0, 5 0 0, 5 0 5, 0 0 5, 0 0 0"/>
<ROUTE fromNode="PathTimer" fromField="fraction_changed"
       toNode="PathInterp" toField="set_fraction"/>
<ROUTE fromNode="PathInterp" fromField="value_changed"
       toNode="MyTransform" toField="translation"/>
```

## 4. Fade In/Out
Animate transparency:
```xml
<TimeSensor DEF="FadeTimer" cycleInterval="3" loop="true"/>
<ScalarInterpolator DEF="FadeInterp"
    key="0 0.5 1"
    keyValue="0, 1, 0"/>
<ROUTE fromNode="FadeTimer" fromField="fraction_changed"
       toNode="FadeInterp" toField="set_fraction"/>
<ROUTE fromNode="FadeInterp" fromField="value_changed"
       toNode="MyMaterial" toField="transparency"/>
```

**Tip:** Use `x3d_animate` to generate these patterns automatically!"""

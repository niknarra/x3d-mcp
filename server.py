"""X3D MCP Server

Provides AI models with tools to validate, look up, and work with
X3D (Extensible 3D Graphics) content per the X3D 4.0 specification.
"""

import logging
import sys

from mcp.server.fastmcp import FastMCP

from src.validation import validate_x3d_file, validate_x3d_string
from src.spec_lookup import (
    check_node_hierarchy,
    get_field_type_info,
    get_node_info,
    list_components,
    list_nodes_by_component,
    list_profiles,
    search_nodes,
)
from src.generation import (
    add_node_to_scene,
    generate_node,
    generate_scene_template,
    generate_x3dom_page,
    generate_x3dom_template,
)
from src.file_ops import (
    extract_node as extract_x3d_node,
    list_defs,
    parse_x3d_scene,
    scene_stats,
)
from src.scene_manipulation import (
    modify_node,
    remove_node,
    move_node,
)
from src.semantic_check import semantic_check
from src.animation import (
    animate,
    add_route,
    animation_info,
)

# Configure logging to stderr (stdout is reserved for MCP JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("x3d-mcp")

# Initialize the MCP server
mcp = FastMCP(
    "x3d",
    instructions=(
        "X3D MCP Server provides tools for working with X3D (Extensible 3D Graphics) content. "
        "X3D is an ISO standard (ISO/IEC 19775) for representing 3D scenes and objects. "
        "Use the validation tools to check X3D content against the official X3D 4.0 XML Schema. "
        "Use the spec lookup tools to get authoritative information about X3D nodes, fields, "
        "components, and profiles directly from the X3D Unified Object Model (X3DUOM). "
        "Use the generation tools to create valid X3D scenes, individual nodes, and X3DOM HTML pages. "
        "Use the file operations tools to parse, analyze, and extract nodes from existing X3D content. "
        "Use the scene manipulation tools to modify, remove, or move nodes within existing scenes. "
        "Use the semantic check tool for deeper analysis beyond XSD (missing geometry, broken ROUTEs, etc.). "
        "Use the animation tools to create TimeSensor + Interpolator + ROUTE chains for animations. "
        "When generating X3D content, always validate the output before returning it to the user. "
        "Use the prompts (build_scene, audit_scene, convert_to_x3dom, animate_scene) for guided workflows."
    ),
)


# ──────────────────────────────────────────────
# Phase 1: Validation Tools
# ────────��─────────────────────────────────────

@mcp.tool()
def validate_x3d(x3d_xml: str) -> str:
    """Validate an X3D XML string against the official X3D 4.0 schema.

    Use this tool to check if X3D XML content is valid before presenting it to users
    or writing it to files. Catches errors in node names, attribute types, hierarchy
    violations, and other schema constraint violations.

    Args:
        x3d_xml: A complete X3D XML document string, including the XML declaration
                 and X3D root element. Example minimal document:
                 <?xml version="1.0" encoding="UTF-8"?>
                 <X3D profile="Interchange" version="4.0"
                       xmlns:xsd="https://www.w3.org/2001/XMLSchema-instance"
                       xsd:noNamespaceSchemaLocation="https://www.web3d.org/specifications/x3d-4.0.xsd">
                   <Scene/>
                 </X3D>
    """
    result = validate_x3d_string(x3d_xml)
    return result["summary"]


@mcp.tool()
def validate_x3d_file_tool(filepath: str) -> str:
    """Validate an X3D file on disk against the official X3D 4.0 schema.

    Use this tool to check existing .x3d files for schema compliance.
    Only XML-encoded X3D files (.x3d extension) are supported.

    Args:
        filepath: Absolute path to a .x3d file on disk.
    """
    result = validate_x3d_file(filepath)
    return result["summary"]


# ─────���────────────────────────���───────────────
# Phase 2: Specification Lookup Tools
# ──────────────���───────────────────────────────

@mcp.tool()
def x3d_node_info(node_name: str) -> str:
    """Get detailed specification info about an X3D node.

    Returns the node's component, inheritance, all fields with types/defaults/constraints,
    and a link to the official specification. Use this before generating X3D content
    to ensure correct field names, types, and allowed values.

    Args:
        node_name: Exact X3D node name (case-sensitive). Examples: Box, Material,
                   Transform, IndexedFaceSet, Appearance, Viewpoint, DirectionalLight.
    """
    return get_node_info(node_name)


@mcp.tool()
def x3d_search_nodes(query: str) -> str:
    """Search for X3D nodes by name or description.

    Use this when you don't know the exact node name. Searches both node names
    and their descriptions in the X3D 4.0 spec.

    Args:
        query: Search term. Examples: "light", "texture", "animation", "sensor",
               "geometry", "audio", "physics", "CAD".
    """
    return search_nodes(query)


@mcp.tool()
def x3d_list_components(component_name: str = "") -> str:
    """List X3D components, or list all nodes in a specific component.

    Call with no arguments to see all available components.
    Call with a component name to see all nodes in that component.

    Args:
        component_name: Optional component name. Examples: Geometry3D, Lighting,
                        Shape, Texturing, Navigation, Sound, HAnim.
                        Leave empty to list all components.
    """
    if component_name:
        return list_nodes_by_component(component_name)
    return list_components()


@mcp.tool()
def x3d_list_profiles() -> str:
    """List all X3D profiles with descriptions.

    Profiles are capability tiers that define which components and nodes are available.
    Common profiles: Core, Interchange, Interactive, Immersive, CADInterchange, Full.
    """
    return list_profiles()


@mcp.tool()
def x3d_field_type_info(field_type: str) -> str:
    """Explain an X3D field type or enumeration type.

    Use this to understand what values a field accepts.

    Args:
        field_type: An X3D field type (e.g., SFVec3f, MFString, SFColor, SFRotation)
                    or an enumeration type from the spec (e.g., alphaModeChoices,
                    fogTypeChoices).
    """
    return get_field_type_info(field_type)


@mcp.tool()
def x3d_check_hierarchy(parent_node: str, child_node: str) -> str:
    """Check if a parent-child node relationship is valid in X3D.

    Verifies whether a child node can be placed inside a parent node
    based on the X3D 4.0 specification's type constraints.

    Args:
        parent_node: The parent node name (e.g., Transform, Scene, Appearance).
        child_node: The child node name (e.g., Shape, Material, Box).
    """
    return check_node_hierarchy(parent_node, child_node)


# ──────────────────────────────────────────────
# Phase 3: Scene Generation Tools
# ──────────────────────────────────────────────

@mcp.tool()
def x3d_scene_template(
    profile: str = "Interchange",
    title: str = "",
    include_viewpoint: bool = True,
    include_light: bool = True,
) -> str:
    """Generate a minimal valid X3D scene template.

    Returns a complete, valid X3D XML document with boilerplate already set up.
    Use this as a starting point and modify the scene content as needed.

    Args:
        profile: X3D profile to use. Common choices:
                 - Interchange: basic geometry and appearance (recommended default)
                 - Interactive: adds sensors and user interaction
                 - Immersive: full VR-capable scenes
                 - Full: all X3D components
        title: Optional scene title (added as metadata).
        include_viewpoint: Whether to include a default Viewpoint node.
        include_light: Whether to include a default DirectionalLight.
    """
    return generate_scene_template(profile, title, include_viewpoint, include_light)


@mcp.tool()
def x3d_generate_node(node_name: str, fields: str = "{}") -> str:
    """Generate a single X3D node with specified field values.

    Uses the official x3d.py library (X3DPSAIL) to construct the node,
    ensuring type correctness by construction. Returns the XML fragment
    for the node.

    Args:
        node_name: The X3D node name. Examples: Box, Sphere, Material, Transform,
                   Viewpoint, DirectionalLight, IndexedFaceSet, ImageTexture.
        fields: JSON string of field name-value pairs. Examples:
                '{"size": [2, 3, 1]}' for Box
                '{"diffuseColor": [1, 0, 0], "transparency": 0.5}' for Material
                '{"translation": [1, 2, 0], "rotation": [0, 1, 0, 1.57]}' for Transform
                '{"radius": 2.5}' for Sphere
                '{}' for defaults
    """
    import json
    try:
        field_dict = json.loads(fields)
    except json.JSONDecodeError as e:
        return f"Invalid JSON for fields: {e}. Pass a JSON object like '{{\"size\": [2, 2, 2]}}'"

    return generate_node(node_name, field_dict)


@mcp.tool()
def x3d_add_node(scene_xml: str, node_xml: str, parent_def: str = "") -> str:
    """Insert an X3D node into an existing scene.

    Parses both the scene and the node XML, inserts the node at the specified
    location, and returns the modified scene XML.

    Args:
        scene_xml: The complete X3D XML document to modify.
        node_xml: The X3D node XML fragment to insert. Can be generated using
                  x3d_generate_node or written manually.
        parent_def: Optional DEF name of the parent node. If provided, the node
                    is inserted as a child of the node with that DEF. If empty,
                    the node is added as a direct child of <Scene>.
    """
    return add_node_to_scene(scene_xml, node_xml, parent_def)


@mcp.tool()
def x3dom_page(
    x3d_content: str,
    title: str = "X3DOM Scene",
    width: str = "800px",
    height: str = "600px",
    show_stats: bool = False,
    show_log: bool = False,
) -> str:
    """Wrap X3D scene content in a complete X3DOM HTML page.

    Takes either a full X3D XML document or raw X3D scene nodes and produces
    a standalone HTML page that renders the 3D scene in the browser using X3DOM.

    X3DOM is a JavaScript framework that renders X3D content directly in web
    browsers without plugins. This tool handles the HTML boilerplate, CDN includes,
    and proper element structure.

    Args:
        x3d_content: Either a complete X3D XML document (the <Scene> content will
                     be extracted) or raw X3D node XML to place inside <scene>.
        title: Page title shown in the browser tab and as a heading.
        width: Width of the 3D viewport (CSS value, e.g., "800px", "100%").
        height: Height of the 3D viewport (CSS value, e.g., "600px", "100vh").
        show_stats: Show X3DOM rendering statistics overlay.
        show_log: Show X3DOM log console overlay.
    """
    return generate_x3dom_page(x3d_content, title, width, height, show_stats, show_log)


@mcp.tool()
def x3dom_starter() -> str:
    """Generate a complete starter X3DOM HTML page with an example scene.

    Returns a ready-to-open HTML file with X3DOM loaded from CDN, a simple
    3D scene (red cube with lighting and viewpoint), and clean styling.
    Save the output as an .html file and open it in any modern browser.
    """
    return generate_x3dom_template()


# ──────────────────────────────────────────────
# Prompts: Guided Workflows
# ──────────────────────────────────────────────

@mcp.prompt()
def build_scene(description: str = "a simple 3D scene") -> str:
    """Step-by-step guide to build an X3D scene from scratch.

    Walks through creating a template, adding geometry with materials,
    validating, and rendering in the browser via X3DOM.
    """
    return (
        f"Build an X3D scene: {description}\n\n"
        "Follow these steps using the X3D MCP tools:\n\n"
        "1. **Create a template:** Call x3d_scene_template(profile='Interchange', "
        "title='<your title>') to get a valid starting document with viewpoint and lighting.\n\n"
        "2. **Look up nodes:** Use x3d_search_nodes('<keyword>') to find the right geometry, "
        "then x3d_node_info('<NodeName>') to see available fields, types, and defaults.\n\n"
        "3. **Generate nodes:** Use x3d_generate_node('<NodeName>', '{...fields...}') to create "
        "each node. Wrap geometry in Shape > Appearance > Material for visible objects.\n\n"
        "4. **Compose the scene:** Use x3d_add_node(scene_xml, node_xml) to insert each node. "
        "Use parent_def to nest nodes inside DEF'd parents (e.g., inside a Transform).\n\n"
        "5. **Validate:** Call validate_x3d(scene_xml) to check the result against the "
        "official X3D 4.0 schema. Fix any errors before proceeding.\n\n"
        "6. **Render:** Call x3dom_page(scene_xml, title='<title>') to produce a standalone "
        "HTML file. Save it as .html and open in any browser.\n\n"
        "Key X3D patterns:\n"
        "- Shape = Appearance (Material + optional Texture) + Geometry (Box, Sphere, etc.)\n"
        "- Transform wraps children with translation/rotation/scale\n"
        "- DEF names let you reference nodes later\n"
        "- SFColor is 3 floats in [0,1] (e.g., 1 0 0 = red)\n"
        "- SFRotation is axis-angle: x y z angle_in_radians"
    )


@mcp.prompt()
def audit_scene(filepath: str = "") -> str:
    """Guide to analyze and audit an existing X3D file.

    Walks through parsing, getting stats, validating, and reporting issues.
    """
    source_hint = f"'{filepath}'" if filepath else "the X3D file or XML string"
    return (
        f"Audit the X3D scene at {source_hint}.\n\n"
        "Follow these steps using the X3D MCP tools:\n\n"
        "1. **Parse the scene graph:** Call x3d_parse_scene(<source>) to see the full "
        "node hierarchy with DEF names and key attributes.\n\n"
        "2. **Get statistics:** Call x3d_scene_stats(<source>) to see node counts by type "
        "and component, DEF'd vs anonymous nodes, and profile info.\n\n"
        "3. **List named nodes:** Call x3d_list_defs(<source>) to see all DEF'd nodes "
        "with their parents and children.\n\n"
        "4. **Schema validation:** Call validate_x3d(<source>) to check the document against the "
        "official X3D 4.0 schema and report any violations.\n\n"
        "5. **Semantic analysis:** Call x3d_semantic_check(<source>) for deeper checks: "
        "missing geometry, empty groups, broken ROUTE references, duplicate DEFs, etc.\n\n"
        "6. **Inspect specific nodes:** Use x3d_extract_node(<source>, def_name='<name>') "
        "to get the full XML of interesting nodes. Use x3d_node_info('<NodeType>') to check "
        "if field values are within spec constraints.\n\n"
        "7. **Report:** Summarize findings including: profile/version, scene complexity, "
        "any schema violations, semantic issues, and recommendations."
    )


@mcp.prompt()
def convert_to_x3dom() -> str:
    """Guide to convert X3D content into a browser-viewable X3DOM HTML page."""
    return (
        "Convert X3D content to an X3DOM HTML page for browser viewing.\n\n"
        "Follow these steps:\n\n"
        "1. **Get the X3D content:** Either load from a file using x3d_parse_scene(<path>) "
        "to verify it first, or use the raw X3D XML string.\n\n"
        "2. **Validate first:** Call validate_x3d(<content>) to ensure the X3D is valid "
        "before converting.\n\n"
        "3. **Convert to X3DOM:** Call x3dom_page(x3d_content=<content>, title='<title>', "
        "width='800px', height='600px'). The tool accepts either a full X3D document or "
        "raw scene nodes.\n\n"
        "4. **Save and open:** Save the returned HTML string as a .html file and open it "
        "in any modern browser (Chrome, Firefox, Safari, Edge). The X3DOM library loads "
        "from CDN -- no installation needed.\n\n"
        "Options:\n"
        "- Set width/height to '100%' for full-page rendering\n"
        "- Set show_stats=True to show the rendering stats overlay\n"
        "- For a quick demo, use x3dom_starter() to get a ready-made example page"
    )


# ──────────────────────────────────────────────
# Phase 4: File Operations Tools
# ──────────────────────────────────────────────

@mcp.tool()
def x3d_parse_scene(x3d_source: str) -> str:
    """Parse X3D content and display the scene graph as an indented tree.

    Shows every node in the scene hierarchy with its DEF name (if any) and
    key attribute values. Use this to understand the structure of an existing
    X3D scene before modifying or analyzing it.

    Args:
        x3d_source: Either an absolute file path to a .x3d file, or a complete
                    X3D XML document string. The tool auto-detects which.
    """
    return parse_x3d_scene(x3d_source)


@mcp.tool()
def x3d_scene_stats(x3d_source: str) -> str:
    """Get statistics about an X3D scene: node counts by type and component.

    Returns total node count, DEF'd vs anonymous nodes, node type breakdown,
    and grouping by X3D component (Geometry3D, Lighting, Shape, etc.).
    Use this for a quick overview before diving deeper.

    Args:
        x3d_source: Either an absolute file path to a .x3d file, or a complete
                    X3D XML document string.
    """
    return scene_stats(x3d_source)


@mcp.tool()
def x3d_list_defs(x3d_source: str) -> str:
    """List all DEF'd (named) nodes in an X3D scene.

    DEF names are unique identifiers assigned to nodes in X3D, similar to
    HTML id attributes. Returns each DEF name with the node type, parent,
    and children for context. Use this to find targets for x3d_extract_node
    or x3d_add_node.

    Args:
        x3d_source: Either an absolute file path to a .x3d file, or a complete
                    X3D XML document string.
    """
    return list_defs(x3d_source)


@mcp.tool()
def x3d_extract_node(
    x3d_source: str,
    def_name: str = "",
    node_type: str = "",
    index: int = 0,
) -> str:
    """Extract a specific node (and its children) from an X3D scene as XML.

    Identify the target node by its DEF name, or by node type + index. Returns
    the full XML subtree of the matched node. If both def_name and node_type
    are given, def_name takes precedence.

    Args:
        x3d_source: Either an absolute file path to a .x3d file, or a complete
                    X3D XML document string.
        def_name: The DEF name of the node to extract (e.g., "RedSphere").
                  Use x3d_list_defs to see available names.
        node_type: The X3D node type to extract (e.g., "Material", "Transform").
                   Combined with index to select which instance.
        index: 0-based index when extracting by node_type. Default 0 (first match).
               Use x3d_scene_stats to see how many of each type exist.
    """
    return extract_x3d_node(x3d_source, def_name, node_type, index)


# ──────────────────────────────────────────────
# Phase 5: Scene Manipulation Tools
# ──────────────────────────────────────────────

@mcp.tool()
def x3d_modify_node(x3d_source: str, def_name: str, field_changes: str) -> str:
    """Modify field values on a DEF'd node in an X3D scene.

    Finds the node by its DEF name and updates the specified attributes.
    Returns the complete modified X3D XML document.

    Args:
        x3d_source: Complete X3D XML document string or file path.
        def_name: The DEF name of the node to modify (e.g., "RedMat", "MainView").
        field_changes: JSON string of field=value changes to apply.
                       Example: '{"diffuseColor": "0 1 0", "transparency": "0.5"}'
                       Values are set as XML attribute strings.
    """
    import json
    try:
        changes = json.loads(field_changes)
    except json.JSONDecodeError as e:
        return f"Invalid JSON for field_changes: {e}. Pass a JSON object like '{{\"diffuseColor\": \"0 1 0\"}}'"
    return modify_node(x3d_source, def_name, changes)


@mcp.tool()
def x3d_remove_node(
    x3d_source: str,
    def_name: str = "",
    node_type: str = "",
    index: int = 0,
) -> str:
    """Remove a node (and its children) from an X3D scene.

    Identifies the target by DEF name, or by node_type + index. Returns
    the modified X3D XML document with the node removed.

    Args:
        x3d_source: Complete X3D XML document string or file path.
        def_name: DEF name of the node to remove. Takes precedence over node_type.
                  Use x3d_list_defs to see available names.
        node_type: Node type to remove (e.g., "DirectionalLight", "Transform").
                   Combined with index to select which instance.
        index: 0-based index when removing by node_type. Default 0 (first match).
    """
    return remove_node(x3d_source, def_name, node_type, index)


@mcp.tool()
def x3d_move_node(x3d_source: str, def_name: str, new_parent_def: str = "") -> str:
    """Reparent a node from its current parent to a new parent in the scene graph.

    Detaches the node (by DEF name) from its current location and appends it
    as a child of the new parent. Detects and prevents cycles.

    Args:
        x3d_source: Complete X3D XML document string or file path.
        def_name: DEF name of the node to move.
        new_parent_def: DEF name of the new parent node. Leave empty to move
                        to be a direct child of <Scene>.
    """
    return move_node(x3d_source, def_name, new_parent_def)


# ──────────────────────────────────────────────
# Phase 6: Semantic Validation Tools
# ──────────────────────────────────────────────

@mcp.tool()
def x3d_semantic_check(x3d_source: str) -> str:
    """Run semantic checks on an X3D scene beyond XSD schema validation.

    Detects common authoring issues that XSD cannot catch:
    - Shape nodes missing geometry or appearance
    - Empty grouping nodes (Transform, Group with no children)
    - Duplicate DEF names
    - USE referencing non-existent DEF
    - ROUTE referencing invalid DEF names, fields, or mismatched types
    - Missing Viewpoint

    Returns a structured report of errors, warnings, and informational notes.

    Args:
        x3d_source: Complete X3D XML document string or file path.
    """
    return semantic_check(x3d_source)


# ──────────────────────────────────────────────
# Phase 7: Animation & Interaction Tools
# ──────────────────────────────────────────────

@mcp.tool()
def x3d_animate(
    x3d_source: str,
    target_def: str,
    field_name: str,
    from_value: str,
    to_value: str,
    duration: float = 5.0,
    loop: bool = True,
) -> str:
    """Generate a complete X3D animation chain and insert it into a scene.

    Creates a TimeSensor, the appropriate Interpolator (auto-selected based
    on the target field's type), and ROUTE statements to wire them together.
    Inserts all nodes into the scene and returns the modified X3D document.

    Args:
        x3d_source: Complete X3D XML document string or file path.
        target_def: DEF name of the node to animate (e.g., "MyTransform").
        field_name: Field to animate. Examples:
                    - "rotation" → OrientationInterpolator
                    - "translation" → PositionInterpolator
                    - "diffuseColor" → ColorInterpolator
                    - "transparency" → ScalarInterpolator
        from_value: Starting value as a space-separated string (e.g., "0 1 0 0").
        to_value: Ending value as a space-separated string (e.g., "0 1 0 6.283").
        duration: Animation cycle duration in seconds. Default 5.0.
        loop: Whether the animation loops continuously. Default True.
    """
    return animate(x3d_source, target_def, field_name, from_value, to_value, duration, loop)


@mcp.tool()
def x3d_route(
    x3d_source: str,
    from_node: str,
    from_field: str,
    to_node: str,
    to_field: str,
) -> str:
    """Validate and insert a ROUTE statement into an X3D scene.

    ROUTEs connect event outputs to event inputs in X3D's event system.
    This tool validates that both DEF names exist, field names are valid,
    access types are compatible, and field types match before inserting.

    Args:
        x3d_source: Complete X3D XML document string or file path.
        from_node: DEF name of the source node.
        from_field: Output field on the source (must be outputOnly or inputOutput).
        to_node: DEF name of the destination node.
        to_field: Input field on the destination (must be inputOnly or inputOutput).
    """
    return add_route(x3d_source, from_node, from_field, to_node, to_field)


@mcp.tool()
def x3d_animation_info(topic: str = "") -> str:
    """Explain X3D animation concepts and list available interpolators.

    Provides reference documentation about X3D's event-driven animation system.
    Call with no topic for a general overview.

    Args:
        topic: Focus area. Options:
               - "interpolators": list all interpolator nodes with field mappings
               - "timesensor": TimeSensor fields and outputs reference
               - "routes": ROUTE syntax, rules, and patterns
               - "examples": common animation code patterns
               - "": general overview of the animation system
    """
    return animation_info(topic)


# ──────────────────────────────────────────────
# Additional Prompts
# ──────────────────────────────────────────────

@mcp.prompt()
def animate_scene(target_description: str = "a rotating object") -> str:
    """Step-by-step guide to add animation to an X3D scene."""
    return (
        f"Add animation to an X3D scene: {target_description}\n\n"
        "Follow these steps using the X3D MCP tools:\n\n"
        "1. **Understand the animation system:** Call x3d_animation_info() for an overview "
        "of how X3D animations work (TimeSensor → Interpolator → ROUTE).\n\n"
        "2. **Parse the scene:** Call x3d_parse_scene(<source>) to see the scene structure "
        "and identify DEF names of nodes you want to animate.\n\n"
        "3. **Check the target field:** Use x3d_node_info('<NodeType>') to verify the field "
        "you want to animate exists and note its type (SFRotation, SFVec3f, SFColor, etc.).\n\n"
        "4. **Look up interpolator info:** Call x3d_animation_info('interpolators') to see "
        "which interpolator matches your field type, and x3d_animation_info('examples') "
        "for common patterns.\n\n"
        "5. **Generate the animation:** Call x3d_animate(scene, target_def='<DEF>', "
        "field_name='<field>', from_value='<start>', to_value='<end>', "
        "duration=<seconds>, loop=True) to auto-generate the full animation chain.\n\n"
        "6. **Validate:** Call validate_x3d(result) to check the animated scene, "
        "then x3d_semantic_check(result) for deeper analysis.\n\n"
        "7. **Render:** Call x3dom_page(result, title='<title>') to create an HTML page "
        "and view the animation in a browser.\n\n"
        "Common animation targets:\n"
        "- **rotation**: SFRotation (axis-angle: x y z angle_radians)\n"
        "- **translation**: SFVec3f (x y z position)\n"
        "- **diffuseColor**: SFColor (r g b in [0,1])\n"
        "- **transparency**: SFFloat (0 = opaque, 1 = invisible)\n"
        "- **scale**: SFVec3f (x y z scale factors)"
    )


def main():
    logger.info("Starting X3D MCP Server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

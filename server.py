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
        "When generating X3D content, always validate the output before returning it to the user."
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


def main():
    logger.info("Starting X3D MCP Server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

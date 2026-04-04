"""X3D scene generation tools using x3d.py (X3DPSAIL).

Generates valid-by-construction X3D content using the official Python
Scene Access Interface Library, plus X3DOM HTML page wrapping.
"""

import io
import logging
import sys
from lxml import etree

# x3d.py prints a banner to stdout on import, which corrupts the
# MCP JSON-RPC stream. Suppress it by redirecting stdout temporarily.
_real_stdout = sys.stdout
sys.stdout = io.StringIO()
try:
    import x3d as x3dlib
finally:
    sys.stdout = _real_stdout

from src.validation import validate_x3d_string

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# Scene Templates
# ─────────────────────────────────────────

_VALID_PROFILES = {
    "Core", "Interchange", "CADInterchange", "Interactive",
    "Immersive", "MedicalInterchange", "MPEG4Interactive", "Full",
}


def generate_scene_template(
    profile: str = "Interchange",
    title: str = "",
    include_viewpoint: bool = True,
    include_light: bool = True,
) -> str:
    """Generate a minimal valid X3D scene template for a given profile."""
    if profile not in _VALID_PROFILES:
        return (
            f"Unknown profile '{profile}'. "
            f"Valid profiles: {', '.join(sorted(_VALID_PROFILES))}"
        )

    scene = x3dlib.X3D(profile=profile, version="4.0")

    # Head with metadata
    scene.head = x3dlib.head()
    if title:
        scene.head.children.append(x3dlib.meta(name="title", content=title))
    scene.head.children.append(
        x3dlib.meta(name="generator", content="X3D MCP Server (x3d.py)")
    )

    scene.Scene = x3dlib.Scene()

    if include_viewpoint:
        scene.Scene.children.append(
            x3dlib.Viewpoint(
                description="Default View",
                position=[0, 0, 10],
            )
        )

    if include_light:
        scene.Scene.children.append(
            x3dlib.DirectionalLight(direction=[0, -1, -1], intensity=0.8)
        )

    # Add a placeholder shape so the scene isn't empty
    shape = x3dlib.Shape()
    shape.appearance = x3dlib.Appearance()
    shape.appearance.material = x3dlib.Material(diffuseColor=[0.8, 0.8, 0.8])
    shape.geometry = x3dlib.Box(size=[2, 2, 2])
    scene.Scene.children.append(shape)

    return scene.XML()


# ─────────────────────────────────────────
# Node Generation
# ─────────────────────────────────────────

def generate_node(node_name: str, fields: dict | None = None) -> str:
    """Generate a single X3D node with the given fields using x3d.py.

    Uses the official X3DPSAIL library to construct the node, which
    ensures type correctness by construction.
    """
    node_class = getattr(x3dlib, node_name, None)
    if node_class is None:
        return (
            f"Unknown X3D node: '{node_name}'. "
            f"Use x3d_search_nodes('{node_name}') to find matching node names, "
            f"or x3d_list_components() to browse by component."
        )

    if not isinstance(node_class, type):
        return f"'{node_name}' is not an X3D node type (it may be a constant or utility in x3d.py)."

    fields = fields or {}

    try:
        node = node_class(**fields)
        return node.XML()
    except TypeError as e:
        return (
            f"Invalid field for {node_name}: {e}. "
            f"Use x3d_node_info('{node_name}') to see the valid fields, "
            f"types, and default values for this node."
        )
    except Exception as e:
        return f"Error creating {node_name}: {e}"


# ─────────────────────────────────────────
# Scene Manipulation
# ─────────────────────────────────────────

def add_node_to_scene(scene_xml: str, node_xml: str, parent_def: str = "") -> str:
    """Insert an X3D node into an existing scene.

    If parent_def is provided, inserts inside the node with that DEF name.
    Otherwise inserts as a direct child of <Scene>.
    """
    try:
        # Parse scene
        parser = etree.XMLParser(remove_blank_text=True)
        scene_tree = etree.fromstring(scene_xml.encode(), parser)
    except etree.XMLSyntaxError as e:
        return f"Error parsing scene XML: {e}. Ensure the scene_xml is a complete X3D document."

    try:
        node_tree = etree.fromstring(node_xml.encode(), parser)
    except etree.XMLSyntaxError as e:
        return (
            f"Error parsing node XML: {e}. "
            f"Use x3d_generate_node() to create well-formed node fragments."
        )

    if parent_def:
        parent = scene_tree.xpath(f"//*[@DEF='{parent_def}']")
        if not parent:
            return (
                f"No node with DEF='{parent_def}' found in the scene. "
                f"Use x3d_list_defs() to see available DEF names."
            )
        parent[0].append(node_tree)
    else:
        scene_el = scene_tree.find("Scene")
        if scene_el is None:
            return (
                "No <Scene> element found. The X3D document must have "
                "the structure <X3D><Scene>...</Scene></X3D>."
            )
        scene_el.append(node_tree)

    # Serialize back
    result = etree.tostring(
        scene_tree,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    ).decode()

    return result


# ─────────────────────────────────────────
# X3DOM HTML Generation
# ─────────────────────────────────────────

_X3DOM_CDN_CSS = "https://www.x3dom.org/download/1.8.2/x3dom.css"
_X3DOM_CDN_JS = "https://www.x3dom.org/download/1.8.2/x3dom.js"


def generate_x3dom_page(
    x3d_content: str,
    title: str = "X3DOM Scene",
    width: str = "800px",
    height: str = "600px",
    show_stats: bool = False,
    show_log: bool = False,
) -> str:
    """Wrap X3D scene content in a complete X3DOM HTML page.

    Extracts the <Scene> content from a full X3D document or uses
    raw X3D nodes directly.
    """
    # Extract just the inner scene content if a full X3D document was passed
    scene_content = _extract_scene_content(x3d_content)

    stats_attr = ' showStat="true"' if show_stats else ""
    log_attr = ' showLog="true"' if show_log else ""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{_escape_html(title)}</title>
    <link rel="stylesheet" href="{_X3DOM_CDN_CSS}">
    <script src="{_X3DOM_CDN_JS}"></script>
    <style>
        body {{
            margin: 0;
            font-family: sans-serif;
            background: #1a1a2e;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }}
        h1 {{
            color: #e0e0e0;
            margin-bottom: 16px;
        }}
        x3d {{
            border: 1px solid #333;
        }}
    </style>
</head>
<body>
    <h1>{_escape_html(title)}</h1>
    <x3d width="{width}" height="{height}"{stats_attr}{log_attr}>
        <scene>
{scene_content}
        </scene>
    </x3d>
</body>
</html>"""

    return html


def generate_x3dom_template(
    title: str = "X3DOM Scene",
    width: str = "800px",
    height: str = "600px",
) -> str:
    """Generate a starter X3DOM HTML page with a simple example scene."""
    scene_content = """\
            <viewpoint description="Default View" position="0 0 10"></viewpoint>
            <directionallight direction="0 -1 -1" intensity="0.8"></directionallight>
            <transform>
                <shape>
                    <appearance>
                        <material diffusecolor="0.8 0.2 0.2"></material>
                    </appearance>
                    <box size="2 2 2"></box>
                </shape>
            </transform>"""

    return generate_x3dom_page(scene_content, title=title, width=width, height=height)


def _extract_scene_content(x3d_content: str) -> str:
    """Extract the inner content of <Scene>...</Scene> from an X3D document
    and convert it to X3DOM-compatible HTML.

    X3DOM runs inside the browser's HTML5 parser which lowercases all tag
    names and attributes, and doesn't support self-closing tags on non-void
    elements.  This function normalises the XML accordingly.

    If the input doesn't look like a full X3D document, return it as-is
    (assumed to be raw scene content already suitable for X3DOM).
    """
    stripped = x3d_content.strip()

    if not stripped.startswith("<?xml") and not stripped.startswith("<X3D"):
        return _indent_content(stripped, 12)

    try:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(stripped.encode(), parser)
        scene_el = tree.find("Scene")
        if scene_el is None:
            return _indent_content(stripped, 12)

        parts = []
        for child in scene_el:
            parts.append(_element_to_x3dom_html(child, depth=0))
        return _indent_content("\n".join(parts), 12)
    except etree.XMLSyntaxError:
        return _indent_content(stripped, 12)


def _element_to_x3dom_html(el: etree._Element, depth: int = 0) -> str:
    """Recursively convert an lxml element to X3DOM-friendly HTML.

    Lowercases tag names and attribute names, uses explicit closing tags,
    and strips namespace declarations / prefixed attributes.
    """
    tag = el.tag
    if isinstance(tag, str) and tag.startswith("{"):
        tag = tag.split("}", 1)[1]
    tag = tag.lower()

    attrs = []
    for attr_name, attr_val in el.attrib.items():
        if attr_name.startswith("{") or ":" in attr_name:
            continue
        attrs.append(f'{attr_name.lower()}="{attr_val}"')

    indent = "    " * depth
    attr_str = (" " + " ".join(attrs)) if attrs else ""

    children = list(el)
    if children:
        inner = "\n".join(
            _element_to_x3dom_html(child, depth + 1) for child in children
        )
        return f"{indent}<{tag}{attr_str}>\n{inner}\n{indent}</{tag}>"

    text = (el.text or "").strip()
    if text:
        return f"{indent}<{tag}{attr_str}>{text}</{tag}>"
    return f"{indent}<{tag}{attr_str}></{tag}>"


def _indent_content(content: str, spaces: int) -> str:
    """Indent content by the given number of spaces."""
    prefix = " " * spaces
    lines = content.strip().split("\n")
    return "\n".join(prefix + line if line.strip() else line for line in lines)


def _escape_html(text: str) -> str:
    """Basic HTML entity escaping."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

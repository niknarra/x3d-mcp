"""Loads and indexes the X3D Unified Object Model (X3DUOM) at startup.

Parses X3dUnifiedObjectModel-4.0.xml into in-memory dictionaries for
fast lookup of nodes, fields, components, profiles, and enumerations.
"""

import logging
import os
from functools import lru_cache
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

SPEC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spec")
X3DUOM_PATH = os.path.join(SPEC_DIR, "X3dUnifiedObjectModel-4.0.xml")


def _parse_field(field_el: ET.Element) -> dict:
    """Parse a <field> element into a structured dict."""
    field = {
        "name": field_el.get("name", ""),
        "type": field_el.get("type", ""),
        "accessType": field_el.get("accessType", ""),
        "default": field_el.get("default"),
        "description": field_el.get("description", ""),
    }

    # Optional constraints
    if field_el.get("minInclusive") is not None:
        field["minInclusive"] = field_el.get("minInclusive")
    if field_el.get("maxInclusive") is not None:
        field["maxInclusive"] = field_el.get("maxInclusive")
    if field_el.get("acceptableNodeTypes"):
        field["acceptableNodeTypes"] = field_el.get("acceptableNodeTypes")
    if field_el.get("inheritedFrom"):
        field["inheritedFrom"] = field_el.get("inheritedFrom")
    if field_el.get("simpleType"):
        field["simpleType"] = field_el.get("simpleType")
    if field_el.get("baseType"):
        field["baseType"] = field_el.get("baseType")

    # Inline enumerations
    enums = field_el.findall("enumeration")
    if enums:
        field["enumerations"] = [
            {"value": e.get("value", ""), "appinfo": e.get("appinfo", "")}
            for e in enums
        ]

    # Component info for this field
    comp_info = field_el.find("componentInfo")
    if comp_info is not None:
        field["componentInfo"] = {
            "name": comp_info.get("name", ""),
            "level": int(comp_info.get("level", "1")),
        }

    return field


def _parse_node(node_el: ET.Element) -> dict:
    """Parse a ConcreteNode or AbstractNodeType element."""
    name = node_el.get("name", "")
    iface = node_el.find("InterfaceDefinition")

    node = {
        "name": name,
        "specificationUrl": "",
        "appinfo": "",
        "component": "",
        "componentLevel": 0,
        "inheritance": "",
        "additionalInheritance": [],
        "fields": [],
    }

    if iface is None:
        return node

    node["specificationUrl"] = iface.get("specificationUrl", "")
    node["appinfo"] = iface.get("appinfo", "")

    # Component info
    comp_info = iface.find("componentInfo")
    if comp_info is not None:
        node["component"] = comp_info.get("name", "")
        node["componentLevel"] = int(comp_info.get("level", "1"))

    # Inheritance
    inheritance = iface.find("Inheritance")
    if inheritance is not None:
        node["inheritance"] = inheritance.get("baseType", "")

    # Additional inheritance (multiple interfaces)
    for add_inh in iface.findall("AdditionalInheritance"):
        node["additionalInheritance"].append(add_inh.get("baseType", ""))

    # Fields
    for field_el in iface.findall("field"):
        node["fields"].append(_parse_field(field_el))

    return node


class X3DUOM:
    """In-memory index of the X3D Unified Object Model."""

    def __init__(self):
        self.concrete_nodes: dict[str, dict] = {}
        self.abstract_node_types: dict[str, dict] = {}
        self.abstract_object_types: dict[str, dict] = {}
        self.simple_types: dict[str, dict] = {}
        self.components: dict[str, list[str]] = {}  # component -> [node names]
        self.profiles: dict[str, str] = {}  # profile name -> appinfo

    def load(self, path: str = X3DUOM_PATH):
        """Parse the X3DUOM XML file and build all indexes."""
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"X3DUOM not found at {path}. "
                "Download from https://www.web3d.org/specifications/X3dUnifiedObjectModel-4.0.xml"
            )

        logger.info("Loading X3DUOM from %s", path)
        tree = ET.parse(path)
        root = tree.getroot()

        self._load_simple_types(root)
        self._load_abstract_object_types(root)
        self._load_abstract_node_types(root)
        self._load_concrete_nodes(root)
        self._load_profiles(root)

        logger.info(
            "X3DUOM loaded: %d concrete nodes, %d abstract types, %d components, %d profiles",
            len(self.concrete_nodes),
            len(self.abstract_node_types),
            len(self.components),
            len(self.profiles),
        )

    def _load_simple_types(self, root: ET.Element):
        section = root.find("SimpleTypeEnumerations")
        if section is None:
            return
        for st in section.findall("SimpleType"):
            name = st.get("name", "")
            self.simple_types[name] = {
                "name": name,
                "baseType": st.get("baseType", ""),
                "appinfo": st.get("appinfo", ""),
                "documentation": st.get("documentation", ""),
                "enumerations": [
                    {"value": e.get("value", ""), "appinfo": e.get("appinfo", "")}
                    for e in st.findall("enumeration")
                ],
            }

    def _load_abstract_object_types(self, root: ET.Element):
        section = root.find("AbstractObjectTypes")
        if section is None:
            return
        for aot in section.findall("AbstractObjectType"):
            parsed = _parse_node(aot)
            self.abstract_object_types[parsed["name"]] = parsed

    def _load_abstract_node_types(self, root: ET.Element):
        section = root.find("AbstractNodeTypes")
        if section is None:
            return
        for ant in section.findall("AbstractNodeType"):
            parsed = _parse_node(ant)
            self.abstract_node_types[parsed["name"]] = parsed

    def _load_concrete_nodes(self, root: ET.Element):
        section = root.find("ConcreteNodes")
        if section is None:
            return
        for cn in section.findall("ConcreteNode"):
            parsed = _parse_node(cn)
            self.concrete_nodes[parsed["name"]] = parsed

            # Index by component
            comp = parsed["component"]
            if comp:
                self.components.setdefault(comp, []).append(parsed["name"])

    def _load_profiles(self, root: ET.Element):
        """Extract profile definitions from the X3D statement's profile attribute."""
        section = root.find("Statements")
        if section is None:
            return
        # Profiles are defined as enumerations in the X3D statement's 'profile' field
        for stmt in section.findall("Statement"):
            if stmt.get("name") != "X3D":
                continue
            iface = stmt.find("InterfaceDefinition")
            if iface is None:
                continue
            for field_el in iface.findall("field"):
                if field_el.get("name") == "profile":
                    for enum in field_el.findall("enumeration"):
                        self.profiles[enum.get("value", "")] = enum.get("appinfo", "")
                    break

    def get_node(self, name: str) -> dict | None:
        """Look up a concrete node by name."""
        return self.concrete_nodes.get(name)

    def get_all_fields(self, node_name: str) -> list[dict]:
        """Get all fields for a node, including inherited ones.

        Walks the inheritance chain to collect fields from parent types.
        """
        node = self.concrete_nodes.get(node_name)
        if node is None:
            return []

        # Start with the node's own fields
        all_fields = {f["name"]: f for f in node["fields"]}

        # Walk the inheritance chain
        visited = set()
        self._collect_inherited_fields(node.get("inheritance", ""), all_fields, visited)

        # Also collect from additional inheritance
        for base in node.get("additionalInheritance", []):
            self._collect_inherited_fields(base, all_fields, visited)

        return list(all_fields.values())

    def _collect_inherited_fields(
        self, base_type: str, fields: dict, visited: set
    ):
        """Recursively collect fields from parent abstract types."""
        if not base_type or base_type in visited:
            return
        visited.add(base_type)

        parent = self.abstract_node_types.get(base_type) or self.abstract_object_types.get(base_type)
        if parent is None:
            return

        for f in parent["fields"]:
            if f["name"] not in fields:
                fields[f["name"]] = f

        # Continue up the chain
        self._collect_inherited_fields(parent.get("inheritance", ""), fields, visited)
        for base in parent.get("additionalInheritance", []):
            self._collect_inherited_fields(base, fields, visited)

    def search_nodes(self, query: str) -> list[dict]:
        """Search concrete nodes by name or description (case-insensitive)."""
        query_lower = query.lower()
        results = []
        for node in self.concrete_nodes.values():
            if (
                query_lower in node["name"].lower()
                or query_lower in node["appinfo"].lower()
            ):
                results.append({
                    "name": node["name"],
                    "component": node["component"],
                    "description": node["appinfo"][:200],
                })
        return results


@lru_cache(maxsize=1)
def get_x3duom() -> X3DUOM:
    """Get the singleton X3DUOM instance, loading it on first access."""
    uom = X3DUOM()
    uom.load()
    return uom

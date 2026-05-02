"""Loads X3D node/field tooltips from x3d-4.0.profile.xml.

The profile file is an X3D-Edit editor profile with rich tooltip text for every
node and attribute — descriptions, Hints, Warnings, and spec links — that are
richer than the brief appinfo strings in the X3DUOM.
"""

import logging
import os
import re
from functools import lru_cache
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

WIKI_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wiki")
TOOLTIPS_PATH = os.path.join(WIKI_DIR, "x3d-4.0.profile.xml")

_STANDARD_ENTITIES = frozenset({"amp", "lt", "gt", "quot", "apos"})


def _parse_entity_defs(internal_subset: str) -> dict[str, str]:
    """Extract <!ENTITY name "value"> declarations from a DOCTYPE internal subset."""
    entities: dict[str, str] = {}
    for m in re.finditer(
        r'<!ENTITY\s+(\S+)\s+(?:"([^"]*)"|\'([^\']*)\')', internal_subset
    ):
        name = m.group(1)
        value = m.group(2) if m.group(2) is not None else m.group(3)
        entities[name] = value
    return entities


def _expand_entities(text: str, entities: dict[str, str]) -> str:
    """Replace &name; custom entity refs, leaving standard XML entities untouched."""
    def _replace(m: re.Match) -> str:
        name = m.group(1)
        if name in _STANDARD_ENTITIES:
            return m.group(0)
        if name not in entities:
            return m.group(0)
        val = entities[name]
        # Escape double-quotes so expanded values don't break XML attribute syntax
        return val.replace('"', "&quot;")

    return re.sub(r"&([A-Za-z][A-Za-z0-9_.-]*);", _replace, text)


def _strip_header(tooltip: str) -> str:
    """Remove the leading [field-signature] [constraint] bracketed headers.

    Tooltip text format: '[fieldName accessType, type default] [0,1]\\nDescription...'
    Node tooltip format:  '[X3DAbstractType,...] NodeName description...'
    We keep everything after the trailing ] of the last leading bracket group.
    """
    return re.sub(r"^\s*(?:\[[^\]]*\]\s*)+", "", tooltip).strip()


def load_tooltips(path: str = TOOLTIPS_PATH) -> dict[str, dict[str, str]]:
    """Parse the tooltips profile and return a nested index.

    Returns:
        {node_name: {"_node": node_tooltip_text, attr_name: attr_tooltip_text, ...}}
    """
    if not os.path.exists(path):
        logger.warning("Tooltips file not found at %s — tooltip enrichment disabled", path)
        return {}

    with open(path, encoding="utf-8") as f:
        raw = f.read()

    # Extract entity definitions from the DOCTYPE internal subset
    doctype_match = re.search(r"\[(.+?)\]>", raw, re.DOTALL)
    entities: dict[str, str] = {}
    if doctype_match:
        entities = _parse_entity_defs(doctype_match.group(1))

    # Remove DOCTYPE declaration — ElementTree cannot handle internal subsets
    cleaned = re.sub(r"<!DOCTYPE[^[]*\[[^\]]*\]>", "", raw, flags=re.DOTALL)
    cleaned = re.sub(r"<!DOCTYPE[^>]*>", "", cleaned)  # fallback: no internal subset

    # Expand custom entity references
    cleaned = _expand_entities(cleaned, entities)

    try:
        root = ET.fromstring(cleaned)
    except ET.ParseError as exc:
        logger.error("Failed to parse tooltips XML: %s", exc)
        return {}

    index: dict[str, dict[str, str]] = {}
    for element in root.iter("element"):
        node_name = element.get("name")
        if not node_name:
            continue

        node_entry: dict[str, str] = {}
        node_tooltip = element.get("tooltip", "")
        if node_tooltip:
            node_entry["_node"] = _strip_header(node_tooltip)

        for attr in element.findall("attribute"):
            attr_name = attr.get("name")
            attr_tooltip = attr.get("tooltip", "")
            if attr_name and attr_tooltip:
                node_entry[attr_name] = _strip_header(attr_tooltip)

        if node_entry:
            index[node_name] = node_entry

    logger.info("Tooltips loaded: %d nodes indexed", len(index))
    return index


@lru_cache(maxsize=1)
def get_tooltips() -> dict[str, dict[str, str]]:
    """Singleton accessor for the tooltips index."""
    return load_tooltips()

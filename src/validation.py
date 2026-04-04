"""X3D validation tools using xmlschema and the official X3D 4.0 XSD."""

import logging
import os
import re
import warnings
from functools import lru_cache

import xmlschema

logger = logging.getLogger(__name__)

SPEC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spec")
XSD_PATH = os.path.join(SPEC_DIR, "x3d-4.0.xsd")

# Pattern to strip XML Schema Instance attributes from the X3D root element,
# since these are processing instructions not defined in the X3D schema itself.
_XSI_ATTRS_RE = re.compile(
    r'\s+xmlns:xsd\s*=\s*["\'][^"\']*["\']'
    r'|\s+xmlns:xsi\s*=\s*["\'][^"\']*["\']'
    r'|\s+xsd:noNamespaceSchemaLocation\s*=\s*["\'][^"\']*["\']'
    r'|\s+xsi:noNamespaceSchemaLocation\s*=\s*["\'][^"\']*["\']'
    r'|\s+xsi:schemaLocation\s*=\s*["\'][^"\']*["\']'
)


_DOCTYPE_RE = re.compile(r'<!DOCTYPE[^>]*>\s*')


def _prepare_for_validation(xml_string: str) -> str:
    """Remove XSI namespace attrs and DOCTYPE declarations for schema validation."""
    result = _XSI_ATTRS_RE.sub("", xml_string)
    result = _DOCTYPE_RE.sub("", result)
    return result


@lru_cache(maxsize=1)
def _load_schema() -> xmlschema.XMLSchema:
    """Load and cache the X3D 4.0 XML schema."""
    if not os.path.exists(XSD_PATH):
        raise FileNotFoundError(
            f"X3D 4.0 schema not found at {XSD_PATH}. "
            "Download it from https://www.web3d.org/specifications/x3d-4.0.xsd"
        )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return xmlschema.XMLSchema(XSD_PATH)


def validate_x3d_string(x3d_xml: str) -> dict:
    """Validate an X3D XML string against the X3D 4.0 schema.

    Returns a dict with 'valid' (bool), 'errors' (list of error strings),
    and 'summary' (human-readable summary).
    """
    schema = _load_schema()
    errors = []

    # Strip XSI attributes that aren't part of the X3D schema
    cleaned_xml = _prepare_for_validation(x3d_xml)

    try:
        validation_errors = list(schema.iter_errors(cleaned_xml))
        errors = [str(e) for e in validation_errors]
    except xmlschema.XMLSchemaException as e:
        errors.append(f"Schema error: {e}")
    except Exception as e:
        errors.append(f"Parsing error: {e}")

    valid = len(errors) == 0

    if valid:
        summary = "Valid X3D 4.0 document. No schema violations found."
    else:
        summary = f"Invalid X3D document. Found {len(errors)} schema violation(s):\n"
        for i, err in enumerate(errors[:10], 1):
            err_str = _humanize_validation_error(str(err))
            summary += f"\n{i}. {err_str}"
        if len(errors) > 10:
            summary += f"\n\n... and {len(errors) - 10} more error(s)."
        summary += (
            "\n\nUse x3d_node_info('<NodeName>') to check valid fields and types, "
            "or x3d_check_hierarchy to verify parent-child relationships."
        )

    return {"valid": valid, "errors": errors[:20], "summary": summary}


def _humanize_validation_error(err: str) -> str:
    """Make xmlschema error messages more readable with X3D context."""
    if len(err) > 500:
        err = err[:500] + "..."
    err = err.replace("failed validating", "Schema violation:")
    return err


def validate_x3d_file(filepath: str) -> dict:
    """Validate an X3D file on disk against the X3D 4.0 schema.

    Returns the same dict structure as validate_x3d_string.
    """
    if not os.path.exists(filepath):
        return {
            "valid": False,
            "errors": [f"File not found: {filepath}"],
            "summary": f"File not found: {filepath}",
        }

    if not filepath.lower().endswith(".x3d"):
        return {
            "valid": False,
            "errors": ["File does not have .x3d extension. Only XML-encoded X3D files (.x3d) are supported for schema validation."],
            "summary": "Unsupported file format. This tool validates XML-encoded X3D files (.x3d) against the X3D 4.0 XSD schema.",
        }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Could not read file: {e}"],
            "summary": f"Could not read file: {e}",
        }

    result = validate_x3d_string(content)
    result["filepath"] = filepath
    return result

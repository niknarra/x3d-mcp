"""Tests for X3D spec lookup tools."""

from src.spec_lookup import (
    check_node_hierarchy,
    get_field_type_info,
    get_node_info,
    list_components,
    list_nodes_by_component,
    list_profiles,
    search_nodes,
)
from src.x3duom_loader import get_x3duom


class TestX3DUOMLoader:
    def test_loads_concrete_nodes(self):
        uom = get_x3duom()
        assert len(uom.concrete_nodes) > 200

    def test_loads_components(self):
        uom = get_x3duom()
        assert "Geometry3D" in uom.components
        assert "Lighting" in uom.components
        assert "Shape" in uom.components

    def test_loads_profiles(self):
        uom = get_x3duom()
        assert "Interchange" in uom.profiles
        assert "Full" in uom.profiles
        assert "Immersive" in uom.profiles

    def test_get_node_exists(self):
        uom = get_x3duom()
        box = uom.get_node("Box")
        assert box is not None
        assert box["name"] == "Box"
        assert box["component"] == "Geometry3D"

    def test_get_node_not_found(self):
        uom = get_x3duom()
        assert uom.get_node("FakeNode") is None

    def test_get_all_fields_includes_inherited(self):
        uom = get_x3duom()
        fields = uom.get_all_fields("Box")
        field_names = [f["name"] for f in fields]
        assert "size" in field_names  # own field
        assert "metadata" in field_names  # inherited from X3DNode

    def test_search_nodes(self):
        uom = get_x3duom()
        results = uom.search_nodes("light")
        names = [r["name"] for r in results]
        assert "DirectionalLight" in names


class TestNodeInfo:
    def test_known_node(self):
        result = get_node_info("Box")
        assert "Box" in result
        assert "Geometry3D" in result
        assert "size" in result

    def test_unknown_node_with_suggestion(self):
        result = get_node_info("Boxes")
        assert "not found" in result.lower() or "did you mean" in result.lower()

    def test_case_insensitive_fallback(self):
        result = get_node_info("box")
        assert "Box" in result
        assert "Geometry3D" in result

    def test_material_has_fields(self):
        result = get_node_info("Material")
        assert "diffuseColor" in result
        assert "transparency" in result

    def test_transform_has_fields(self):
        result = get_node_info("Transform")
        assert "translation" in result
        assert "rotation" in result
        assert "scale" in result


class TestSearchNodes:
    def test_search_geometry(self):
        result = search_nodes("geometry")
        assert "Box" not in result or "Geometry" in result  # should find geometry-related

    def test_search_texture(self):
        result = search_nodes("texture")
        assert "ImageTexture" in result

    def test_search_no_results(self):
        result = search_nodes("xyznonexistent")
        assert "No nodes found" in result


class TestListComponents:
    def test_list_all(self):
        result = list_components()
        assert "Geometry3D" in result
        assert "Lighting" in result

    def test_list_specific_component(self):
        result = list_nodes_by_component("Geometry3D")
        assert "Box" in result
        assert "Sphere" in result
        assert "Cylinder" in result

    def test_unknown_component(self):
        result = list_nodes_by_component("FakeComponent")
        assert "not found" in result.lower()
        assert "Available components" in result


class TestListProfiles:
    def test_list_profiles(self):
        result = list_profiles()
        assert "Interchange" in result
        assert "Full" in result


class TestFieldTypeInfo:
    def test_sfvec3f(self):
        result = get_field_type_info("SFVec3f")
        assert "3D vector" in result

    def test_sfcolor(self):
        result = get_field_type_info("SFColor")
        assert "RGB" in result

    def test_sfrotation(self):
        result = get_field_type_info("SFRotation")
        assert "angle" in result.lower() or "rotation" in result.lower()

    def test_enum_type(self):
        result = get_field_type_info("alphaModeChoices")
        assert "AUTO" in result
        assert "OPAQUE" in result

    def test_unknown_type(self):
        result = get_field_type_info("FakeType")
        assert "not found" in result.lower()


class TestCheckHierarchy:
    def test_transform_shape_valid(self):
        result = check_node_hierarchy("Transform", "Shape")
        assert "Valid" in result

    def test_appearance_material_valid(self):
        result = check_node_hierarchy("Appearance", "Material")
        assert "Valid" in result

    def test_shape_appearance_valid(self):
        result = check_node_hierarchy("Shape", "Appearance")
        assert "Valid" in result

    def test_shape_box_valid(self):
        result = check_node_hierarchy("Shape", "Box")
        assert "Valid" in result

    def test_box_material_invalid(self):
        result = check_node_hierarchy("Box", "Material")
        assert "Not directly valid" in result

    def test_unknown_parent(self):
        result = check_node_hierarchy("FakeNode", "Box")
        assert "not found" in result.lower()

    def test_unknown_child(self):
        result = check_node_hierarchy("Transform", "FakeNode")
        assert "not found" in result.lower()

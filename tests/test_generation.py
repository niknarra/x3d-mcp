"""Tests for X3D scene generation tools."""

from src.generation import (
    add_node_to_scene,
    generate_node,
    generate_scene_template,
    generate_x3dom_page,
    generate_x3dom_template,
)
from src.validation import validate_x3d_string


class TestSceneTemplate:
    def test_interchange_profile(self):
        result = generate_scene_template("Interchange")
        assert "<X3D" in result
        assert "profile='Interchange'" in result
        assert "<Scene>" in result

    def test_template_validates(self):
        result = generate_scene_template("Interchange", "Test Scene")
        assert validate_x3d_string(result)["valid"] is True

    def test_full_profile(self):
        result = generate_scene_template("Full")
        assert "profile='Full'" in result

    def test_invalid_profile(self):
        result = generate_scene_template("FakeProfile")
        assert "Unknown profile" in result

    def test_no_viewpoint(self):
        result = generate_scene_template("Interchange", include_viewpoint=False)
        assert "Viewpoint" not in result

    def test_no_light(self):
        result = generate_scene_template("Interchange", include_light=False)
        assert "DirectionalLight" not in result

    def test_title_in_metadata(self):
        result = generate_scene_template("Interchange", title="My Scene")
        assert "My Scene" in result


class TestGenerateNode:
    def test_box_default(self):
        result = generate_node("Box")
        assert "<Box/>" in result

    def test_box_with_size(self):
        result = generate_node("Box", {"size": [3, 3, 3]})
        assert "size=" in result

    def test_sphere_with_radius(self):
        result = generate_node("Sphere", {"radius": 2.5})
        assert "radius=" in result

    def test_material_with_color(self):
        result = generate_node("Material", {"diffuseColor": [1, 0, 0]})
        assert "diffuseColor=" in result

    def test_transform_with_def(self):
        result = generate_node("Transform", {"DEF": "MyT", "translation": [1, 2, 3]})
        assert "DEF=" in result
        assert "translation=" in result

    def test_unknown_node(self):
        result = generate_node("FakeNode")
        assert "Unknown" in result

    def test_invalid_field(self):
        result = generate_node("Box", {"nonexistent_field": 42})
        assert "Error" in result


class TestAddNodeToScene:
    def test_add_to_scene_root(self):
        scene = generate_scene_template("Interchange")
        node = '<Shape><Appearance><Material diffuseColor="0 1 0"/></Appearance><Sphere/></Shape>'
        result = add_node_to_scene(scene, node)
        assert "<Sphere" in result
        assert validate_x3d_string(result)["valid"] is True

    def test_add_to_def_parent(self):
        scene = '<?xml version="1.0" encoding="UTF-8"?><X3D profile="Interchange" version="4.0"><Scene><Transform DEF="Parent"></Transform></Scene></X3D>'
        node = "<Shape><Box/></Shape>"
        result = add_node_to_scene(scene, node, parent_def="Parent")
        assert "<Box" in result
        assert "Parent" in result

    def test_missing_def(self):
        scene = generate_scene_template("Interchange")
        node = "<Box/>"
        result = add_node_to_scene(scene, node, parent_def="NonExistent")
        assert "No node found" in result

    def test_invalid_scene_xml(self):
        result = add_node_to_scene("not xml", "<Box/>")
        assert "Error" in result

    def test_invalid_node_xml(self):
        scene = generate_scene_template("Interchange")
        result = add_node_to_scene(scene, "not xml")
        assert "Error" in result


class TestX3DOMPage:
    def test_basic_page(self):
        html = generate_x3dom_page("<shape><box/></shape>", title="Test")
        assert "x3dom.js" in html
        assert "x3dom.css" in html
        assert "<x3d" in html
        assert "<scene>" in html
        assert "box" in html
        assert "<title>Test</title>" in html

    def test_from_full_x3d_document(self):
        x3d = generate_scene_template("Interchange", "Source Scene")
        html = generate_x3dom_page(x3d, title="Converted")
        assert "x3dom.js" in html
        assert "Viewpoint" in html or "viewpoint" in html.lower()
        assert "<title>Converted</title>" in html

    def test_custom_dimensions(self):
        html = generate_x3dom_page("<box/>", width="100%", height="100vh")
        assert '100%' in html
        assert '100vh' in html

    def test_show_stats(self):
        html = generate_x3dom_page("<box/>", show_stats=True)
        assert 'showStat="true"' in html

    def test_show_log(self):
        html = generate_x3dom_page("<box/>", show_log=True)
        assert 'showLog="true"' in html

    def test_html_escaping_in_title(self):
        html = generate_x3dom_page("<box/>", title='<script>alert("xss")</script>')
        assert "<script>" not in html.split("<title>")[1].split("</title>")[0]


class TestX3DOMTemplate:
    def test_generates_complete_page(self):
        html = generate_x3dom_template("Starter")
        assert "<!DOCTYPE html>" in html
        assert "x3dom.js" in html
        assert "<scene>" in html
        assert "box" in html
        assert "material" in html
        assert "directionalLight" in html.lower() or "directionallight" in html.lower()

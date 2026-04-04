"""Tests for X3D validation."""

from src.validation import validate_x3d_string, validate_x3d_file


VALID_MINIMAL = '''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="4.0">
  <Scene/>
</X3D>'''

VALID_SCENE = '''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="4.0"
     xmlns:xsd="https://www.w3.org/2001/XMLSchema-instance"
     xsd:noNamespaceSchemaLocation="https://www.web3d.org/specifications/x3d-4.0.xsd">
  <Scene>
    <Shape>
      <Appearance>
        <Material diffuseColor="1 0 0"/>
      </Appearance>
      <Box size="2 2 2"/>
    </Shape>
  </Scene>
</X3D>'''

INVALID_NODE = '''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="4.0">
  <Scene>
    <FakeNode/>
  </Scene>
</X3D>'''

INVALID_ATTR = '''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="4.0">
  <Scene>
    <Shape>
      <Appearance>
        <Material diffuseColor="not a color"/>
      </Appearance>
      <Box size="2 2 2"/>
    </Shape>
  </Scene>
</X3D>'''


def test_valid_minimal():
    result = validate_x3d_string(VALID_MINIMAL)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_valid_scene_with_xsi_attrs():
    result = validate_x3d_string(VALID_SCENE)
    assert result["valid"] is True


def test_invalid_node_name():
    result = validate_x3d_string(INVALID_NODE)
    assert result["valid"] is False
    assert any("FakeNode" in e for e in result["errors"])


def test_invalid_attribute_value():
    result = validate_x3d_string(INVALID_ATTR)
    assert result["valid"] is False


def test_validates_x3d_py_output():
    import x3d
    scene = x3d.X3D(profile='Interchange', version='4.0')
    scene.Scene = x3d.Scene()
    shape = x3d.Shape()
    shape.geometry = x3d.Box(size=[2, 2, 2])
    shape.appearance = x3d.Appearance()
    shape.appearance.material = x3d.Material(diffuseColor=[1, 0, 0])
    scene.Scene.children.append(shape)
    result = validate_x3d_string(scene.XML())
    assert result["valid"] is True


def test_file_not_found():
    result = validate_x3d_file("/nonexistent/path/file.x3d")
    assert result["valid"] is False
    assert "not found" in result["summary"].lower()


def test_wrong_extension(tmp_path):
    obj_file = tmp_path / "model.obj"
    obj_file.write_text("v 0 0 0")
    result = validate_x3d_file(str(obj_file))
    assert result["valid"] is False
    assert ".x3d" in result["summary"]


def test_garbage_input():
    result = validate_x3d_string("this is not xml at all")
    assert result["valid"] is False

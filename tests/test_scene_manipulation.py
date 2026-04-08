"""Tests for X3D scene manipulation: modify, remove, and move nodes."""

from src.scene_manipulation import modify_node, remove_node, move_node
from src.validation import validate_x3d_string


SAMPLE_SCENE = '''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="4.0">
  <Scene>
    <Viewpoint DEF="MainView" description="Default View" position="0 0 10"/>
    <DirectionalLight DEF="Sun" direction="0 -1 -1" intensity="0.8"/>
    <Transform DEF="RedGroup" translation="2 0 0">
      <Shape DEF="RedShape">
        <Appearance>
          <Material DEF="RedMat" diffuseColor="1 0 0"/>
        </Appearance>
        <Sphere radius="1.5"/>
      </Shape>
    </Transform>
    <Transform DEF="BlueGroup" translation="-2 0 0">
      <Shape DEF="BlueShape">
        <Appearance>
          <Material DEF="BlueMat" diffuseColor="0 0 1" transparency="0.3"/>
        </Appearance>
        <Box size="2 2 2"/>
      </Shape>
    </Transform>
  </Scene>
</X3D>'''


# ──────────────────────────────────────────────
# modify_node
# ──────────────────────────────────────────────

class TestModifyNode:
    def test_modify_single_attribute(self):
        result = modify_node(SAMPLE_SCENE, "RedMat", {"diffuseColor": "0 1 0"})
        assert 'diffuseColor="0 1 0"' in result
        assert "1 0 0" not in result.split("RedMat")[1].split("/>")[0]

    def test_modify_multiple_fields(self):
        result = modify_node(SAMPLE_SCENE, "RedGroup", {
            "translation": "5 5 5",
            "rotation": "0 1 0 1.57",
        })
        assert 'translation="5 5 5"' in result
        assert 'rotation="0 1 0 1.57"' in result

    def test_modify_preserves_other_attributes(self):
        result = modify_node(SAMPLE_SCENE, "BlueMat", {"diffuseColor": "0 1 0"})
        assert 'diffuseColor="0 1 0"' in result
        assert 'transparency="0.3"' in result

    def test_modify_nonexistent_def(self):
        result = modify_node(SAMPLE_SCENE, "DoesNotExist", {"foo": "bar"})
        assert "DoesNotExist" in result
        assert "Available DEF names" in result

    def test_modify_no_def(self):
        result = modify_node(SAMPLE_SCENE, "", {"foo": "bar"})
        assert "def_name is required" in result.lower()

    def test_modify_no_changes(self):
        result = modify_node(SAMPLE_SCENE, "RedMat", {})
        assert "No field_changes" in result

    def test_modified_scene_validates(self):
        result = modify_node(SAMPLE_SCENE, "RedMat", {"diffuseColor": "0 1 0"})
        assert validate_x3d_string(result)["valid"] is True

    def test_modify_adds_new_attribute(self):
        result = modify_node(SAMPLE_SCENE, "RedMat", {"shininess": "0.8"})
        assert 'shininess="0.8"' in result


# ──────────────────────────────────────────────
# remove_node
# ──────────────────────────────────────────────

class TestRemoveNode:
    def test_remove_by_def(self):
        result = remove_node(SAMPLE_SCENE, def_name="RedGroup")
        assert "RedGroup" not in result
        assert "BlueGroup" in result

    def test_remove_by_type_and_index(self):
        result = remove_node(SAMPLE_SCENE, node_type="Transform", index=1)
        # Second Transform (BlueGroup) should be removed
        assert "BlueGroup" not in result
        assert "RedGroup" in result

    def test_remove_preserves_siblings(self):
        result = remove_node(SAMPLE_SCENE, def_name="Sun")
        assert "Sun" not in result
        assert "MainView" in result
        assert "RedGroup" in result
        assert "BlueGroup" in result

    def test_remove_nonexistent_def(self):
        result = remove_node(SAMPLE_SCENE, def_name="FakeNode")
        assert "FakeNode" in result
        assert "Available DEF names" in result

    def test_remove_nonexistent_type(self):
        result = remove_node(SAMPLE_SCENE, node_type="IndexedFaceSet")
        assert "IndexedFaceSet" in result

    def test_remove_type_index_out_of_range(self):
        result = remove_node(SAMPLE_SCENE, node_type="Transform", index=99)
        assert "out of range" in result.lower()

    def test_remove_no_identifiers(self):
        result = remove_node(SAMPLE_SCENE)
        assert "def_name" in result.lower() or "node_type" in result.lower()

    def test_removed_scene_validates(self):
        result = remove_node(SAMPLE_SCENE, def_name="RedGroup")
        assert validate_x3d_string(result)["valid"] is True

    def test_remove_leaf_node(self):
        result = remove_node(SAMPLE_SCENE, def_name="RedMat")
        assert "RedMat" not in result
        assert "RedGroup" in result  # Parent still exists


# ──────────────────────────────────────────────
# move_node
# ──────────────────────────────────────────────

class TestMoveNode:
    def test_move_to_new_parent(self):
        result = move_node(SAMPLE_SCENE, "RedShape", new_parent_def="BlueGroup")
        assert "RedShape" in result
        assert "BlueGroup" in result
        # RedShape should now be a child of BlueGroup, not RedGroup

    def test_move_to_scene_root(self):
        result = move_node(SAMPLE_SCENE, "RedShape", new_parent_def="")
        assert "RedShape" in result

    def test_move_nonexistent_source(self):
        result = move_node(SAMPLE_SCENE, "FakeNode", new_parent_def="BlueGroup")
        assert "FakeNode" in result

    def test_move_nonexistent_target(self):
        result = move_node(SAMPLE_SCENE, "RedShape", new_parent_def="FakeParent")
        assert "FakeParent" in result

    def test_move_to_self(self):
        result = move_node(SAMPLE_SCENE, "RedGroup", new_parent_def="RedGroup")
        assert "Cannot move" in result or "itself" in result.lower()

    def test_move_to_descendant(self):
        result = move_node(SAMPLE_SCENE, "RedGroup", new_parent_def="RedMat")
        assert "cycle" in result.lower() or "descendant" in result.lower()

    def test_move_already_at_parent(self):
        result = move_node(SAMPLE_SCENE, "RedShape", new_parent_def="RedGroup")
        assert "already" in result.lower()

    def test_moved_scene_validates(self):
        result = move_node(SAMPLE_SCENE, "Sun", new_parent_def="RedGroup")
        assert validate_x3d_string(result)["valid"] is True

    def test_move_no_def(self):
        result = move_node(SAMPLE_SCENE, "")
        assert "def_name is required" in result.lower()

"""Tests for X3D file operations: parse, stats, list DEFs, extract."""

from src.file_ops import extract_node, list_defs, parse_x3d_scene, scene_stats


SAMPLE_SCENE = '''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="4.0">
  <Scene>
    <Viewpoint DEF="MainView" description="Default View" position="0 0 10"/>
    <DirectionalLight DEF="Sun" direction="0 -1 -1" intensity="0.8"/>
    <Transform DEF="RedGroup" translation="2 0 0">
      <Shape>
        <Appearance>
          <Material DEF="RedMat" diffuseColor="1 0 0"/>
        </Appearance>
        <Sphere radius="1.5"/>
      </Shape>
    </Transform>
    <Transform translation="-2 0 0">
      <Shape>
        <Appearance>
          <Material diffuseColor="0 0 1" transparency="0.3"/>
        </Appearance>
        <Box size="2 2 2"/>
      </Shape>
    </Transform>
  </Scene>
</X3D>'''

EMPTY_SCENE = '''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="4.0">
  <Scene/>
</X3D>'''

NO_DEF_SCENE = '''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="4.0">
  <Scene>
    <Shape>
      <Box size="1 1 1"/>
    </Shape>
  </Scene>
</X3D>'''


# ──────────────────────────────────────────────
# parse_x3d_scene
# ──────────────────────────────────────────────

class TestParseScene:
    def test_shows_tree_structure(self):
        result = parse_x3d_scene(SAMPLE_SCENE)
        assert "Viewpoint" in result
        assert "DirectionalLight" in result
        assert "Transform" in result
        assert "Shape" in result
        assert "Material" in result

    def test_shows_def_names(self):
        result = parse_x3d_scene(SAMPLE_SCENE)
        assert 'DEF="MainView"' in result
        assert 'DEF="RedGroup"' in result
        assert 'DEF="RedMat"' in result

    def test_shows_key_attributes(self):
        result = parse_x3d_scene(SAMPLE_SCENE)
        assert "translation=" in result
        assert "diffuseColor=" in result
        assert "radius=" in result

    def test_shows_profile_and_version(self):
        result = parse_x3d_scene(SAMPLE_SCENE)
        assert "4.0" in result
        assert "Interchange" in result

    def test_empty_scene(self):
        result = parse_x3d_scene(EMPTY_SCENE)
        assert "empty scene" in result.lower()

    def test_invalid_xml(self):
        result = parse_x3d_scene("not xml at all")
        assert "not found" in result.lower() or "invalid" in result.lower()

    def test_indentation_shows_hierarchy(self):
        result = parse_x3d_scene(SAMPLE_SCENE)
        lines = result.strip().split("\n")
        transform_line = next(l for l in lines if "RedGroup" in l)
        shape_line_idx = lines.index(transform_line) + 1
        shape_line = lines[shape_line_idx]
        assert len(shape_line) - len(shape_line.lstrip()) > len(transform_line) - len(transform_line.lstrip())


# ──────────────────────────────────────────────
# scene_stats
# ──────────────────────────────────────────────

class TestSceneStats:
    def test_total_node_count(self):
        result = scene_stats(SAMPLE_SCENE)
        assert "Total nodes" in result

    def test_def_count(self):
        result = scene_stats(SAMPLE_SCENE)
        assert "DEF'd" in result

    def test_nodes_by_type(self):
        result = scene_stats(SAMPLE_SCENE)
        assert "Shape" in result
        assert "Material" in result
        assert "Transform" in result

    def test_nodes_by_component(self):
        result = scene_stats(SAMPLE_SCENE)
        assert "Component" in result

    def test_profile_info(self):
        result = scene_stats(SAMPLE_SCENE)
        assert "Interchange" in result

    def test_empty_scene(self):
        result = scene_stats(EMPTY_SCENE)
        assert "Total nodes" in result
        assert "0" in result

    def test_invalid_source(self):
        result = scene_stats("/nonexistent/path/file.x3d")
        assert "not found" in result.lower()


# ──────────────────────────────────────────────
# list_defs
# ──────────────────────────────────────────────

class TestListDefs:
    def test_finds_all_defs(self):
        result = list_defs(SAMPLE_SCENE)
        assert "MainView" in result
        assert "Sun" in result
        assert "RedGroup" in result
        assert "RedMat" in result

    def test_shows_node_type(self):
        result = list_defs(SAMPLE_SCENE)
        assert "Viewpoint" in result
        assert "DirectionalLight" in result
        assert "Transform" in result
        assert "Material" in result

    def test_shows_parent(self):
        result = list_defs(SAMPLE_SCENE)
        assert "parent:" in result.lower()

    def test_shows_children(self):
        result = list_defs(SAMPLE_SCENE)
        assert "children:" in result.lower()

    def test_no_defs(self):
        result = list_defs(NO_DEF_SCENE)
        assert "no def" in result.lower()

    def test_def_count(self):
        result = list_defs(SAMPLE_SCENE)
        assert "4" in result


# ──────────────────────────────────────────────
# extract_node
# ──────────────────────────────────────────────

class TestExtractNode:
    def test_extract_by_def(self):
        result = extract_node(SAMPLE_SCENE, def_name="RedGroup")
        assert "<Transform" in result
        assert 'DEF="RedGroup"' in result
        assert "<Shape" in result
        assert "<Sphere" in result

    def test_extract_by_def_leaf(self):
        result = extract_node(SAMPLE_SCENE, def_name="RedMat")
        assert "<Material" in result
        assert 'diffuseColor="1 0 0"' in result

    def test_extract_by_type_first(self):
        result = extract_node(SAMPLE_SCENE, node_type="Material")
        assert "<Material" in result
        assert "1 0 0" in result

    def test_extract_by_type_second(self):
        result = extract_node(SAMPLE_SCENE, node_type="Material", index=1)
        assert "<Material" in result
        assert "0 0 1" in result

    def test_def_takes_precedence(self):
        result = extract_node(SAMPLE_SCENE, def_name="RedMat", node_type="Box")
        assert "<Material" in result

    def test_nonexistent_def(self):
        result = extract_node(SAMPLE_SCENE, def_name="DoesNotExist")
        assert "DoesNotExist" in result
        assert "Available DEF names" in result

    def test_nonexistent_type(self):
        result = extract_node(SAMPLE_SCENE, node_type="IndexedFaceSet")
        assert "IndexedFaceSet" in result
        assert "x3d_scene_stats" in result

    def test_index_out_of_range(self):
        result = extract_node(SAMPLE_SCENE, node_type="Material", index=99)
        assert "out of range" in result.lower()

    def test_no_identifiers(self):
        result = extract_node(SAMPLE_SCENE)
        assert "def_name" in result.lower() or "node_type" in result.lower()

    def test_invalid_source(self):
        result = extract_node("definitely not xml", def_name="Foo")
        assert "not found" in result.lower() or "invalid" in result.lower()


# ──────────────────────────────────────────────
# File path handling
# ──────────────────────────────────────────────

class TestFilePathHandling:
    def test_file_not_found(self):
        result = parse_x3d_scene("/nonexistent/file.x3d")
        assert "not found" in result.lower()

    def test_wrong_extension(self):
        result = parse_x3d_scene("/some/file.obj")
        assert "unsupported" in result.lower() or "not found" in result.lower()

    def test_file_on_disk(self, tmp_path):
        x3d_file = tmp_path / "test.x3d"
        x3d_file.write_text(SAMPLE_SCENE)
        result = parse_x3d_scene(str(x3d_file))
        assert "Viewpoint" in result
        assert "RedGroup" in result

    def test_stats_from_file(self, tmp_path):
        x3d_file = tmp_path / "test.x3d"
        x3d_file.write_text(SAMPLE_SCENE)
        result = scene_stats(str(x3d_file))
        assert "Total nodes" in result

    def test_defs_from_file(self, tmp_path):
        x3d_file = tmp_path / "test.x3d"
        x3d_file.write_text(SAMPLE_SCENE)
        result = list_defs(str(x3d_file))
        assert "MainView" in result

    def test_extract_from_file(self, tmp_path):
        x3d_file = tmp_path / "test.x3d"
        x3d_file.write_text(SAMPLE_SCENE)
        result = extract_node(str(x3d_file), def_name="RedGroup")
        assert "<Transform" in result

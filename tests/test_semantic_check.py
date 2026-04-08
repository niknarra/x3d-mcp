"""Tests for X3D semantic validation checks."""

from src.semantic_check import semantic_check


CLEAN_SCENE = '''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="4.0">
  <Scene>
    <Viewpoint DEF="MainView" description="Default View" position="0 0 10"/>
    <DirectionalLight direction="0 -1 -1" intensity="0.8"/>
    <Transform DEF="Group1" translation="0 0 0">
      <Shape>
        <Appearance>
          <Material diffuseColor="1 0 0"/>
        </Appearance>
        <Box size="2 2 2"/>
      </Shape>
    </Transform>
  </Scene>
</X3D>'''


# ──────────────────────────────────────────────
# Shape completeness
# ──────────────────────────────────────────────

class TestShapeCompleteness:
    def test_shape_no_geometry(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Shape><Appearance><Material/></Appearance></Shape>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "shape-no-geometry" in result

    def test_shape_no_appearance(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Shape><Box/></Shape>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "shape-no-appearance" in result

    def test_complete_shape_no_warning(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Viewpoint position="0 0 10"/>
            <Shape>
                <Appearance><Material diffuseColor="1 0 0"/></Appearance>
                <Box/>
            </Shape>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "shape-no-geometry" not in result


# ──────────────────────────────────────────────
# Empty groups
# ──────────────────────────────────────────────

class TestEmptyGroups:
    def test_empty_transform(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Viewpoint position="0 0 10"/>
            <Transform DEF="Empty"/>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "empty-group" in result
        assert "Empty" in result

    def test_transform_with_children_ok(self):
        result = semantic_check(CLEAN_SCENE)
        assert "empty-group" not in result


# ──────────────────────────────────────────────
# DEF/USE consistency
# ──────────────────────────────────────────────

class TestDefUseConsistency:
    def test_use_references_undefined_def(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Viewpoint position="0 0 10"/>
            <Shape USE="NonExistent"/>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "use-undefined-def" in result
        assert "NonExistent" in result

    def test_unused_def_info(self):
        result = semantic_check(CLEAN_SCENE)
        assert "unused-def" in result  # MainView and Group1 are DEF'd but not USE'd

    def test_consistent_def_use(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Viewpoint position="0 0 10"/>
            <Material DEF="SharedMat" diffuseColor="1 0 0"/>
            <Shape>
                <Appearance><Material USE="SharedMat"/></Appearance>
                <Box/>
            </Shape>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "use-undefined-def" not in result


# ──────────────────────────────────────────────
# Duplicate DEFs
# ──────────────────────────────────────────────

class TestDuplicateDefs:
    def test_duplicate_def_names(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Viewpoint position="0 0 10"/>
            <Box DEF="Dup"/>
            <Sphere DEF="Dup"/>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "duplicate-def" in result
        assert "Dup" in result

    def test_unique_defs_ok(self):
        result = semantic_check(CLEAN_SCENE)
        assert "duplicate-def" not in result


# ──────────────────────────────────────────────
# ROUTE validity
# ──────────────────────────────────────────────

class TestRouteValidity:
    def test_route_nonexistent_from_node(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Viewpoint position="0 0 10"/>
            <Transform DEF="T1"/>
            <ROUTE fromNode="Ghost" fromField="fraction_changed"
                   toNode="T1" toField="translation"/>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "route-missing-from-node" in result

    def test_route_nonexistent_to_node(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Viewpoint position="0 0 10"/>
            <TimeSensor DEF="T1" cycleInterval="2"/>
            <ROUTE fromNode="T1" fromField="fraction_changed"
                   toNode="Ghost" toField="set_fraction"/>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "route-missing-to-node" in result

    def test_route_invalid_field(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Viewpoint position="0 0 10"/>
            <TimeSensor DEF="Timer" cycleInterval="2"/>
            <Transform DEF="Mover"/>
            <ROUTE fromNode="Timer" fromField="nonexistent_field"
                   toNode="Mover" toField="translation"/>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "route-invalid-from-field" in result

    def test_valid_route_no_error(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Viewpoint position="0 0 10"/>
            <TimeSensor DEF="Timer" cycleInterval="2"/>
            <PositionInterpolator DEF="Mover" key="0 1" keyValue="0 0 0, 5 0 0"/>
            <ROUTE fromNode="Timer" fromField="fraction_changed"
                   toNode="Mover" toField="set_fraction"/>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "route-missing" not in result
        assert "route-invalid" not in result


# ──────────────────────────────────────────────
# Missing Viewpoint
# ──────────────────────────────────────────────

class TestMissingViewpoint:
    def test_no_viewpoint_info(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Shape><Appearance><Material/></Appearance><Box/></Shape>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "no-viewpoint" in result

    def test_with_viewpoint_ok(self):
        result = semantic_check(CLEAN_SCENE)
        assert "no-viewpoint" not in result


# ──────────────────────────────────────────────
# Overall report
# ──────────────────────────────────────────────

class TestOverallReport:
    def test_clean_scene_structure(self):
        result = semantic_check(CLEAN_SCENE)
        # Clean scene should still have info-level items (unused DEFs)
        assert "Semantic Check" in result

    def test_multiple_issues_all_reported(self):
        scene = '''<?xml version="1.0" encoding="UTF-8"?>
        <X3D profile="Interchange" version="4.0"><Scene>
            <Transform DEF="Empty"/>
            <Shape><Box/></Shape>
            <Shape USE="Ghost"/>
        </Scene></X3D>'''
        result = semantic_check(scene)
        assert "empty-group" in result
        assert "shape-no-appearance" in result
        assert "use-undefined-def" in result
        assert "no-viewpoint" in result

    def test_invalid_xml_source(self):
        result = semantic_check("this is not xml")
        assert "not found" in result.lower() or "invalid" in result.lower()

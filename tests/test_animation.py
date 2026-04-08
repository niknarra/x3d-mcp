"""Tests for X3D animation and interaction helpers."""

from src.animation import animate, add_route, animation_info
from src.validation import validate_x3d_string


ANIM_SCENE = '''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="4.0">
  <Scene>
    <Viewpoint DEF="MainView" description="Default View" position="0 0 10"/>
    <DirectionalLight direction="0 -1 -1" intensity="0.8"/>
    <Transform DEF="Spinner" translation="0 0 0">
      <Shape>
        <Appearance>
          <Material DEF="ColorMat" diffuseColor="1 0 0"/>
        </Appearance>
        <Box size="2 2 2"/>
      </Shape>
    </Transform>
  </Scene>
</X3D>'''

ROUTE_SCENE = '''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="4.0">
  <Scene>
    <Viewpoint position="0 0 10"/>
    <TimeSensor DEF="Clock" cycleInterval="3" loop="true"/>
    <PositionInterpolator DEF="Mover" key="0 1" keyValue="0 0 0, 5 0 0"/>
    <Transform DEF="Target" translation="0 0 0">
      <Shape><Appearance><Material/></Appearance><Box/></Shape>
    </Transform>
  </Scene>
</X3D>'''


# ──────────────────────────────────────────────
# animate
# ──────────────────────────────────────────────

class TestAnimate:
    def test_rotation_animation(self):
        result = animate(
            ANIM_SCENE, "Spinner", "rotation",
            "0 1 0 0", "0 1 0 6.28318", duration=4.0,
        )
        assert "OrientationInterpolator" in result
        assert "TimeSensor" in result
        assert "ROUTE" in result

    def test_translation_animation(self):
        result = animate(
            ANIM_SCENE, "Spinner", "translation",
            "0 0 0", "5 0 0", duration=3.0,
        )
        assert "PositionInterpolator" in result
        assert "TimeSensor" in result

    def test_color_animation(self):
        result = animate(
            ANIM_SCENE, "ColorMat", "diffuseColor",
            "1 0 0", "0 0 1", duration=2.0,
        )
        assert "ColorInterpolator" in result

    def test_scalar_animation(self):
        result = animate(
            ANIM_SCENE, "ColorMat", "transparency",
            "0", "1", duration=3.0,
        )
        assert "ScalarInterpolator" in result

    def test_animation_creates_timer_and_routes(self):
        result = animate(
            ANIM_SCENE, "Spinner", "rotation",
            "0 1 0 0", "0 1 0 6.28318",
        )
        assert result.count("ROUTE") >= 2
        assert "TimeSensor" in result
        assert "fraction_changed" in result
        assert "value_changed" in result

    def test_animation_loop_true(self):
        result = animate(
            ANIM_SCENE, "Spinner", "rotation",
            "0 1 0 0", "0 1 0 6.28318", loop=True,
        )
        assert 'loop="true"' in result

    def test_animation_loop_false(self):
        result = animate(
            ANIM_SCENE, "Spinner", "rotation",
            "0 1 0 0", "0 1 0 6.28318", loop=False,
        )
        assert 'loop="false"' in result

    def test_animation_custom_duration(self):
        result = animate(
            ANIM_SCENE, "Spinner", "rotation",
            "0 1 0 0", "0 1 0 6.28318", duration=10.0,
        )
        assert 'cycleInterval="10.0"' in result

    def test_animate_nonexistent_def(self):
        result = animate(
            ANIM_SCENE, "FakeNode", "rotation",
            "0 1 0 0", "0 1 0 6.28318",
        )
        assert "FakeNode" in result
        assert "Available DEF names" in result or "not found" in result.lower()

    def test_animate_invalid_field(self):
        result = animate(
            ANIM_SCENE, "Spinner", "nonexistent_field",
            "0", "1",
        )
        assert "not found" in result.lower() or "nonexistent_field" in result

    def test_animate_no_target_def(self):
        result = animate(ANIM_SCENE, "", "rotation", "0 0 0 0", "0 1 0 3.14")
        assert "target_def is required" in result

    def test_animate_no_field(self):
        result = animate(ANIM_SCENE, "Spinner", "", "0", "1")
        assert "field_name is required" in result

    def test_animate_no_values(self):
        result = animate(ANIM_SCENE, "Spinner", "rotation", "", "0 1 0 3.14")
        assert "from_value" in result.lower() or "required" in result.lower()


# ──────────────────────────────────────────────
# add_route
# ──────────────────────────────────────────────

class TestAddRoute:
    def test_valid_route_inserted(self):
        result = add_route(
            ROUTE_SCENE, "Clock", "fraction_changed", "Mover", "set_fraction",
        )
        assert "<ROUTE" in result
        assert 'fromNode="Clock"' in result
        assert 'toNode="Mover"' in result

    def test_route_nonexistent_from_def(self):
        result = add_route(
            ROUTE_SCENE, "Ghost", "fraction_changed", "Mover", "set_fraction",
        )
        assert "Ghost" in result
        assert "not found" in result.lower()

    def test_route_nonexistent_to_def(self):
        result = add_route(
            ROUTE_SCENE, "Clock", "fraction_changed", "Ghost", "set_fraction",
        )
        assert "Ghost" in result

    def test_route_invalid_from_field(self):
        result = add_route(
            ROUTE_SCENE, "Clock", "fake_field", "Mover", "set_fraction",
        )
        assert "fake_field" in result

    def test_route_invalid_to_field(self):
        result = add_route(
            ROUTE_SCENE, "Clock", "fraction_changed", "Mover", "fake_field",
        )
        assert "fake_field" in result

    def test_route_missing_params(self):
        result = add_route(ROUTE_SCENE, "", "fraction_changed", "Mover", "set_fraction")
        assert "required" in result.lower()


# ──────────────────────────────────────────────
# animation_info
# ──────────────────────────────────────────────

class TestAnimationInfo:
    def test_general_overview(self):
        result = animation_info()
        assert "TimeSensor" in result
        assert "Interpolator" in result
        assert "ROUTE" in result

    def test_interpolators_topic(self):
        result = animation_info("interpolators")
        assert "OrientationInterpolator" in result
        assert "PositionInterpolator" in result
        assert "ColorInterpolator" in result
        assert "ScalarInterpolator" in result

    def test_timesensor_topic(self):
        result = animation_info("timesensor")
        assert "cycleInterval" in result
        assert "fraction_changed" in result

    def test_routes_topic(self):
        result = animation_info("routes")
        assert "fromNode" in result
        assert "outputOnly" in result
        assert "inputOnly" in result

    def test_examples_topic(self):
        result = animation_info("examples")
        assert "Continuous Rotation" in result
        assert "Color Pulse" in result

    def test_unknown_topic_returns_overview(self):
        result = animation_info("some_unknown_thing")
        assert "Animation System Overview" in result

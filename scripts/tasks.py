"""
30 evaluation tasks for the baseline vs. treatment experiment.

Each task is a natural-language authoring prompt sent to Claude.
Levels:
  1 — Basic structure (single nodes, simple shapes, lights, viewpoints)
  2 — Relationships (DEF/USE, nesting, texture, special nodes)
  3 — Animation and interaction (TimeSensor, Interpolators, ROUTEs)
"""

TASKS = [
    # ── Level 1: Basic structure ───────────────────────────────────────────────
    {
        "id": "task_01",
        "level": 1,
        "category": "basic_shape",
        "prompt": (
            "Create an X3D 4.0 scene with a red box. "
            "The box should be 2x2x2 units, centered at the origin."
        ),
    },
    {
        "id": "task_02",
        "level": 1,
        "category": "basic_shape",
        "prompt": (
            "Create an X3D 4.0 scene with a blue sphere of radius 1 "
            "and a PointLight positioned at (0, 5, 0)."
        ),
    },
    {
        "id": "task_03",
        "level": 1,
        "category": "transform",
        "prompt": (
            "Create an X3D 4.0 scene with a Transform node that translates "
            "to (3, 0, 0) and contains a yellow cone."
        ),
    },
    {
        "id": "task_04",
        "level": 1,
        "category": "viewpoint",
        "prompt": (
            "Create an X3D 4.0 scene with a Viewpoint positioned at (0, 0, 10) "
            "looking toward the origin, with description 'Default View'."
        ),
    },
    {
        "id": "task_05",
        "level": 1,
        "category": "basic_shape",
        "prompt": (
            "Create an X3D 4.0 scene with a Shape containing a Cylinder geometry "
            "(radius 0.5, height 2) and a green Material."
        ),
    },
    {
        "id": "task_06",
        "level": 1,
        "category": "def_naming",
        "prompt": (
            "Create an X3D 4.0 scene with two separate Shape nodes. "
            "The first contains a red box with DEF='RedBox', "
            "the second contains a blue sphere with DEF='BlueSphere'."
        ),
    },
    {
        "id": "task_07",
        "level": 1,
        "category": "geometry",
        "prompt": (
            "Create an X3D 4.0 scene with an IndexedFaceSet that defines a flat square "
            "in the XZ plane using 4 vertices at (-1,0,-1), (1,0,-1), (1,0,1), (-1,0,1). "
            "Give it a white material."
        ),
    },
    {
        "id": "task_08",
        "level": 1,
        "category": "environment",
        "prompt": (
            "Create an X3D 4.0 scene with a Background node. "
            "Set the sky color to light blue (0.5, 0.7, 1.0) and "
            "the ground color to dark green (0.1, 0.3, 0.1)."
        ),
    },
    {
        "id": "task_09",
        "level": 1,
        "category": "lighting",
        "prompt": (
            "Create an X3D 4.0 scene with a DirectionalLight pointing straight down "
            "(direction 0, -1, 0) with intensity 0.8, and a white box to illuminate."
        ),
    },
    {
        "id": "task_10",
        "level": 1,
        "category": "text",
        "prompt": (
            "Create an X3D 4.0 scene with a Text node displaying the string 'Hello X3D'. "
            "Use a FontStyle with size 1.0. Give the text a black material."
        ),
    },

    # ── Level 2: Relationships and structure ───────────────────────────────────
    {
        "id": "task_11",
        "level": 2,
        "category": "def_use",
        "prompt": (
            "Create an X3D 4.0 scene with a Shape containing a red box, DEF='MyBox'. "
            "Then USE='MyBox' twice — once at translation (3,0,0) and once at (-3,0,0)."
        ),
    },
    {
        "id": "task_12",
        "level": 2,
        "category": "nesting",
        "prompt": (
            "Create an X3D 4.0 scene with a Transform hierarchy 3 levels deep. "
            "Each level translates by (1,0,0) relative to its parent. "
            "Place a small box at the innermost level."
        ),
    },
    {
        "id": "task_13",
        "level": 2,
        "category": "texture",
        "prompt": (
            "Create an X3D 4.0 scene with a Shape that has an Appearance containing "
            "an ImageTexture referencing 'texture.png'. "
            "The geometry should be a Box of size 2 2 2."
        ),
    },
    {
        "id": "task_14",
        "level": 2,
        "category": "shape_completeness",
        "prompt": (
            "Create an X3D 4.0 scene where a Shape node has both a geometry child "
            "(a Sphere of radius 1) and a fully specified Appearance child "
            "(Material with diffuseColor 0.8 0.2 0.2, specularColor 1 1 1, shininess 0.5)."
        ),
    },
    {
        "id": "task_15",
        "level": 2,
        "category": "grouping",
        "prompt": (
            "Create an X3D 4.0 scene with a Group node containing 5 box shapes "
            "arranged in a row along the X axis, spaced 2 units apart. "
            "Each box should have a different color."
        ),
    },
    {
        "id": "task_16",
        "level": 2,
        "category": "navigation",
        "prompt": (
            "Create an X3D 4.0 scene with a NavigationInfo node set to EXAMINE "
            "navigation type, speed 1.0, and a red sphere at the origin."
        ),
    },
    {
        "id": "task_17",
        "level": 2,
        "category": "environment",
        "prompt": (
            "Create an X3D 4.0 scene with a Fog node using fogType 'LINEAR', "
            "color 0.8 0.8 0.8, visibilityRange 20. "
            "Include a few boxes at varying distances to show the fog effect."
        ),
    },
    {
        "id": "task_18",
        "level": 2,
        "category": "sensors",
        "prompt": (
            "Create an X3D 4.0 scene with a ProximitySensor centered at the origin "
            "with size 10 10 10, DEF='AreaSensor'. "
            "Include a box and a Viewpoint in the scene."
        ),
    },
    {
        "id": "task_19",
        "level": 2,
        "category": "lod",
        "prompt": (
            "Create an X3D 4.0 scene with a LOD node containing two levels: "
            "at close range (< 10) show a detailed sphere (radius 1, many segments), "
            "at far range show a simple box. Set LOD center at origin."
        ),
    },
    {
        "id": "task_20",
        "level": 2,
        "category": "switch",
        "prompt": (
            "Create an X3D 4.0 scene with a Switch node (DEF='MySwitch', whichChoice=0) "
            "containing two children: a red box and a blue sphere. "
            "Only the first child should be visible."
        ),
    },

    # ── Level 3: Animation and interaction ─────────────────────────────────────
    {
        "id": "task_21",
        "level": 3,
        "category": "rotation_animation",
        "prompt": (
            "Create an X3D 4.0 scene where a box (DEF='SpinBox') rotates 360 degrees "
            "around the Y axis over 4 seconds, looping indefinitely. "
            "Use a TimeSensor and OrientationInterpolator wired via ROUTEs."
        ),
    },
    {
        "id": "task_22",
        "level": 3,
        "category": "translation_animation",
        "prompt": (
            "Create an X3D 4.0 scene where a sphere (DEF='MovingSphere') translates "
            "from position (0,0,0) to (5,0,0) over 3 seconds, then stops. "
            "Use a TimeSensor and PositionInterpolator wired via ROUTEs."
        ),
    },
    {
        "id": "task_23",
        "level": 3,
        "category": "color_animation",
        "prompt": (
            "Create an X3D 4.0 scene where a box's material color (DEF='ColorMat') "
            "animates from red (1,0,0) to blue (0,0,1) over 2 seconds, looping. "
            "Use a TimeSensor and ColorInterpolator wired via ROUTEs."
        ),
    },
    {
        "id": "task_24",
        "level": 3,
        "category": "scalar_animation",
        "prompt": (
            "Create an X3D 4.0 scene where a material's transparency "
            "(DEF='FadeMat') animates from 0 (fully opaque) to 1 (fully transparent) "
            "over 3 seconds, looping. Use a TimeSensor and ScalarInterpolator."
        ),
    },
    {
        "id": "task_25",
        "level": 3,
        "category": "route_wiring",
        "prompt": (
            "Create an X3D 4.0 scene with a Transform (DEF='MoverTransform') containing a box. "
            "Add a TimeSensor (DEF='Clock', cycleInterval=5, loop=true) and a "
            "PositionInterpolator (DEF='PosInterp') with keys [0,0.5,1] and "
            "keyValues [(0,0,0),(0,3,0),(0,0,0)]. "
            "Wire all ROUTEs correctly: Clock→PosInterp→MoverTransform."
        ),
    },
    {
        "id": "task_26",
        "level": 3,
        "category": "interaction",
        "prompt": (
            "Create an X3D 4.0 scene with a box that has a TouchSensor (DEF='Clicker') "
            "and a TimeSensor (DEF='Timer', cycleInterval=2). "
            "Wire a ROUTE so that clicking the box (TouchSensor.touchTime) "
            "triggers the timer (TimeSensor.startTime)."
        ),
    },
    {
        "id": "task_27",
        "level": 3,
        "category": "scale_animation",
        "prompt": (
            "Create an X3D 4.0 scene where a Transform (DEF='ScaleXform') containing a sphere "
            "animates its scale from (1,1,1) to (3,3,3) and back over 2 seconds, looping. "
            "Use a TimeSensor and PositionInterpolator targeting the scale field."
        ),
    },
    {
        "id": "task_28",
        "level": 3,
        "category": "multi_animation",
        "prompt": (
            "Create an X3D 4.0 scene with two independent animations running simultaneously: "
            "1) A box (DEF='RotBox') rotating around Y over 3 seconds, looping. "
            "2) A sphere (DEF='MovSphere') translating between (-3,0,0) and (3,0,0) over 2 seconds, looping. "
            "Each animation should have its own TimeSensor and Interpolator."
        ),
    },
    {
        "id": "task_29",
        "level": 3,
        "category": "keyframe_animation",
        "prompt": (
            "Create an X3D 4.0 scene with a Transform (DEF='SpinXform') containing a box. "
            "Add an OrientationInterpolator (DEF='OriInterp') with exactly 4 keyframes "
            "that rotate the box 90 degrees around Y at each step (0, 90, 180, 270 degrees). "
            "Wire a looping TimeSensor (cycleInterval=4) to drive it."
        ),
    },
    {
        "id": "task_30",
        "level": 3,
        "category": "sensor_triggered_animation",
        "prompt": (
            "Create an X3D 4.0 scene with a ProximitySensor (DEF='Zone', size 8 8 8) "
            "that triggers an animation when the user enters the area. "
            "When triggered, a box (DEF='JumpBox') should translate upward from (0,0,0) to (0,3,0) "
            "over 1.5 seconds. Wire ProximitySensor.enterTime → TimeSensor.startTime."
        ),
    },
]

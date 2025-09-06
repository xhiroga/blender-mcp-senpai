import math
from logging import getLogger

import bpy
from bpy.types import Operator

logger = getLogger(__name__)


def _is_image_empty(obj: bpy.types.Object) -> bool:
    if obj is None:
        return False
    if obj.type != 'EMPTY':
        return False
    # IMAGE empty only
    if getattr(obj, 'empty_display_type', None) != 'IMAGE':
        return False
    # Ensure it has an image datablock and image_user
    img = getattr(obj, 'data', None)
    if img is None or img.__class__.__name__ != 'Image':
        return False
    if getattr(obj, 'image_user', None) is None:
        return False
    # Optionally ensure the source is movie or sequence
    src = getattr(img, 'source', None)
    if src not in {"MOVIE", "SEQUENCE", "FILE", None}:  # allow FILE for image sequences handled via frames
        return False
    return True


def _read_props_from_object(obj: bpy.types.Object) -> dict:
    d = obj.get
    return {
        'enabled': bool(d('bs_turntable_enabled', False)),
        'axis': int(d('bs_axis', 2)),
        'step_deg': float(d('bs_step_deg', 4.444)),
        'offset0': int(d('bs_offset0', 0)),
        'invert': bool(d('bs_invert', True)),
        'wrap': bool(d('bs_wrap', True)),
    }


def _write_props_to_object(obj: bpy.types.Object, props: dict) -> None:
    obj['bs_turntable_enabled'] = bool(props.get('enabled', True))
    obj['bs_axis'] = int(props.get('axis', 2))
    obj['bs_step_deg'] = float(props.get('step_deg', 4.444))
    obj['bs_offset0'] = int(props.get('offset0', 0))
    obj['bs_invert'] = bool(props.get('invert', True))
    obj['bs_wrap'] = bool(props.get('wrap', True))


class BLENDER_SENPAI_OT_turntable_settings(Operator):
    bl_idname = "blender_senpai.turntable_settings"
    bl_label = "Turntable Settings"
    bl_description = "Configure turntable properties for the selected image Empty"
    bl_options = {"REGISTER", "UNDO"}

    # Operator properties (mirrors custom props)
    axis: bpy.props.IntProperty(name="Axis", description="Rotation axis (0=X, 1=Y, 2=Z)", min=0, max=2, default=2)  # type: ignore
    step_deg: bpy.props.FloatProperty(name="Step (deg)", description="Degrees per frame step", min=0.001, max=360.0, default=4.444, precision=3)  # type: ignore
    offset0: bpy.props.IntProperty(name="Base Offset", description="Base frame offset", default=0)  # type: ignore
    invert: bpy.props.BoolProperty(name="Invert Angle (pi - theta)", default=True)  # type: ignore
    wrap: bpy.props.BoolProperty(name="Wrap Frames", description="Wrap frame offset within duration", default=True)  # type: ignore
    enabled: bpy.props.BoolProperty(name="Enable Turntable", default=True)  # type: ignore

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return _is_image_empty(obj)

    def invoke(self, context, event):
        obj = context.active_object
        if not _is_image_empty(obj):
            self.report({'WARNING'}, "Active object is not an image Empty")
            return {'CANCELLED'}

        # Load defaults from object custom properties if present
        vals = _read_props_from_object(obj)
        self.axis = vals['axis']
        self.step_deg = vals['step_deg']
        self.offset0 = vals['offset0']
        self.invert = vals['invert']
        self.wrap = vals['wrap']
        # Respect saved flag; if not present, default to True in the dialog
        self.enabled = vals.get('enabled', True)

        return context.window_manager.invoke_props_dialog(self, width=360)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(self, "enabled")
        col.prop(self, "axis")
        col.prop(self, "step_deg")
        col.prop(self, "offset0")
        col.prop(self, "invert")
        col.prop(self, "wrap")

        # Show preview information (read-only)
        obj = context.active_object
        img = getattr(obj, 'data', None)
        if img is not None:
            sub = layout.box()
            sub.label(text=f"Image source: {getattr(img, 'source', 'UNKNOWN')}")
            dur = None
            try:
                dur = getattr(obj.image_user, 'frame_duration', None)
            except Exception:
                dur = None
            if dur is not None:
                sub.label(text=f"Frame duration: {dur}")

    def execute(self, context):
        obj = context.active_object
        if not _is_image_empty(obj):
            self.report({'WARNING'}, "Active object is not an image Empty")
            return {'CANCELLED'}

        props = {
            'enabled': bool(self.enabled),
            'axis': int(self.axis),
            'step_deg': float(self.step_deg),
            'offset0': int(self.offset0),
            'invert': bool(self.invert),
            'wrap': bool(self.wrap),
        }
        _write_props_to_object(obj, props)
        logger.info(
            f"Turntable props applied to {obj.name}: enabled={props['enabled']}, axis={props['axis']}, step_deg={props['step_deg']}, offset0={props['offset0']}, invert={props['invert']}, wrap={props['wrap']}"
        )
        return {'FINISHED'}


classes = (
    BLENDER_SENPAI_OT_turntable_settings,
)


def _menu_draw_turntable_settings(self, context):
    obj = context.active_object
    if _is_image_empty(obj):
        self.layout.separator()
        op = self.layout.operator(
            BLENDER_SENPAI_OT_turntable_settings.bl_idname,
            text="Turntable Settings…",
            icon='MOD_TIME',
        )
        # Pre-populate operator properties from this object's custom properties
        vals = _read_props_from_object(obj)
        op.enabled = vals.get('enabled', True)
        op.axis = vals.get('axis', 2)
        op.step_deg = vals.get('step_deg', 4.444)
        op.offset0 = vals.get('offset0', 0)
        op.invert = vals.get('invert', True)
        op.wrap = vals.get('wrap', True)


# ----------------------------
# Draw handler implementation
# ----------------------------

_draw_handle = None


def _get_view_euler() -> 'bpy.types.Euler | None':
    # Prefer current screen's first VIEW_3D space
    screen = bpy.context.screen
    if not screen:
        return None
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    try:
                        return space.region_3d.view_rotation.to_euler()
                    except Exception:
                        continue
    return None


def _iter_enabled_image_empties():
    for obj in bpy.data.objects:
        if obj.get('bs_turntable_enabled'):
            if _is_image_empty(obj):
                yield obj


def _apply_turntable(obj: bpy.types.Object, euler):
    # Sync billboard rotation
    try:
        obj.rotation_euler = euler
    except Exception:
        pass

    axis = int(obj.get('bs_axis', 2))
    step_deg = float(obj.get('bs_step_deg', 4.444)) or 4.444
    offset0 = int(obj.get('bs_offset0', 0))
    invert = bool(obj.get('bs_invert', True))
    wrap = bool(obj.get('bs_wrap', True))

    try:
        angle = euler[axis]
    except Exception:
        return

    if invert:
        angle = math.pi - angle
    deg = math.degrees(angle)  # roughly -180..180

    try:
        # quantize by step degrees
        q = int(deg // step_deg) if step_deg != 0 else 0
    except Exception:
        q = 0
    offset = offset0 + q

    # frame duration if available
    duration = None
    try:
        duration = getattr(obj.image_user, 'frame_duration', None)
    except Exception:
        duration = None

    if isinstance(duration, int) and duration > 0:
        if wrap:
            offset = offset % duration
        else:
            offset = max(0, min(duration - 1, offset))

    try:
        if getattr(obj, 'image_user', None) is not None:
            if obj.image_user.frame_offset != offset:
                obj.image_user.frame_offset = offset
    except Exception:
        pass


def _draw_callback():
    euler = _get_view_euler()
    if euler is None:
        return
    for obj in _iter_enabled_image_empties():
        _apply_turntable(obj, euler)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    try:
        bpy.types.VIEW3D_MT_object_context_menu.append(_menu_draw_turntable_settings)
    except Exception:
        # Fallback for Blender versions where menu name may differ
        try:
            bpy.types.VIEW3D_MT_object.append(_menu_draw_turntable_settings)
        except Exception:
            logger.exception("Failed to append Turntable Settings to context menu")

    # Add global draw handler once
    global _draw_handle
    if _draw_handle is None:
        try:
            _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                _draw_callback, (), 'WINDOW', 'POST_VIEW'
            )
        except Exception:
            logger.exception("Failed to add SpaceView3D draw handler for turntable")


def unregister():
    try:
        bpy.types.VIEW3D_MT_object_context_menu.remove(_menu_draw_turntable_settings)
    except Exception:
        try:
            bpy.types.VIEW3D_MT_object.remove(_menu_draw_turntable_settings)
        except Exception:
            pass
    global _draw_handle
    if _draw_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
        except Exception:
            pass
        _draw_handle = None
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

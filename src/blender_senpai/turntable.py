import math
from logging import getLogger

import bpy
from bpy.types import Operator

logger = getLogger(__name__)


def _is_image_empty(obj: bpy.types.Object) -> bool:
    if not obj or obj.type != 'EMPTY':
        return False
    if getattr(obj, 'empty_display_type', None) != 'IMAGE':
        return False
    return getattr(obj, 'data', None).__class__.__name__ == 'Image' and getattr(obj, 'image_user', None) is not None


def _read_props_from_object(obj: bpy.types.Object) -> dict:
    d = obj.get
    return {
        'enabled': bool(d('bs_turntable_enabled', False)),
        'offset0': int(d('bs_offset0', 0)),
    }


def _write_props_to_object(obj: bpy.types.Object, props: dict) -> None:
    obj['bs_turntable_enabled'] = bool(props.get('enabled', True))
    obj['bs_offset0'] = int(props.get('offset0', 0))


class BLENDER_SENPAI_OT_turntable_settings(Operator):
    bl_idname = "blender_senpai.turntable_settings"
    bl_label = "Turntable Settings"
    bl_description = "Configure turntable properties for the selected image Empty"
    bl_options = {"REGISTER", "UNDO"}

    # Operator properties (mirrors custom props)
    offset0: bpy.props.IntProperty(name="Base Offset", description="Base frame offset", default=0)  # type: ignore
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
        self.offset0 = vals['offset0']
        # Respect saved flag; if not present, default to True in the dialog
        self.enabled = vals.get('enabled', True)

        return context.window_manager.invoke_props_dialog(self, width=360)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(self, "enabled")
        col.prop(self, "offset0")
        # always wrap; no toggle

        # Preview (read-only)
        obj = context.active_object
        img = getattr(obj, 'data', None)
        if img is not None:
            sub = layout.box()
            sub.label(text=f"Image source: {getattr(img, 'source', 'UNKNOWN')}")
            dur = getattr(img, 'frame_duration', None)
            if isinstance(dur, int):
                sub.label(text=f"Frame duration: {dur}")

    def execute(self, context):
        obj = context.active_object
        if not _is_image_empty(obj):
            self.report({'WARNING'}, "Active object is not an image Empty")
            return {'CANCELLED'}

        props = {
            'enabled': bool(self.enabled),
            'offset0': int(self.offset0),
        }
        _write_props_to_object(obj, props)
        logger.info(
            f"Turntable props applied to {obj.name}: enabled={props['enabled']}, offset0={props['offset0']}"
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
        op.offset0 = vals.get('offset0', 0)


# ----------------------------
# Draw handler implementation
# ----------------------------

_draw_handle = None


def _get_view_euler():
    screen = bpy.context.screen
    if not screen:
        return None
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            if space and space.type == 'VIEW_3D':
                return space.region_3d.view_rotation.to_euler()
    return None


def _iter_enabled_image_empties():
    for obj in bpy.data.objects:
        if obj.get('bs_turntable_enabled'):
            if _is_image_empty(obj):
                yield obj


def _apply_turntable(obj: bpy.types.Object, euler):
    obj.rotation_euler = euler

    offset0 = int(obj.get('bs_offset0', 0))

    angle = math.pi - euler[2]
    deg = math.degrees(angle)

    iu = getattr(obj, 'image_user', None)
    img = getattr(obj, 'data', None)
    duration = getattr(iu, 'frame_duration', None) or getattr(img, 'frame_duration', None)

    if isinstance(duration, int) and duration > 0:
        step = 360.0 / float(duration)
        q = int(deg // step)
        offset = offset0 + q
        offset = offset % duration
    else:
        offset = offset0

    if iu and iu.frame_offset != offset:
        iu.frame_offset = offset


def _draw_callback():
    euler = _get_view_euler()
    if euler is None:
        return
    for obj in _iter_enabled_image_empties():
        _apply_turntable(obj, euler)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object_context_menu.append(_menu_draw_turntable_settings)

    global _draw_handle
    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_callback, (), 'WINDOW', 'POST_VIEW'
        )


def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(_menu_draw_turntable_settings)
    global _draw_handle
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
        _draw_handle = None
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

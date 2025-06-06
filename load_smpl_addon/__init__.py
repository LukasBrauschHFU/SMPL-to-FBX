bl_info = {
    "name": "Load SMPL from pickle",
    "author": "Joachim Tesch, Max Planck Institute for Intelligent Systems",
    "version": (2023, 6, 11),
    "blender": (2, 80, 0),
    "location": "Viewport > Right panel",
    "description": "Load SMPL",
    "wiki_url": "https://smpl.is.tue.mpg.de/",
    "category": "SMPL"
}

import os
import pickle
import logging

import bpy
from bpy.props import EnumProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup
from bpy_extras.io_utils import ImportHelper

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter('[%(asctime)s] %(message)s', '%Y-%m-%d %H:%M:%S')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

from .helper import InstallScipy, GetAnimation

class SMPLProperties(PropertyGroup):
    smpl_gender: EnumProperty(
        name="Model",
        description="SMPL model",
        items=[("female", "Female", ""), ("male", "Male", "")]
    )

class OpenSmplPklOperator(bpy.types.Operator, ImportHelper):
    bl_idname = "scene.smpl_open_pkl"
    bl_label = "Open Pickle File"
    bl_description = "Load a smpl file stored as a pickle file"
    bl_options = {'REGISTER'}

    filename_ext = ".pkl"
    filter_glob: StringProperty(default="*.pkl", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        try:
            if (context.active_object is None) or (context.active_object.mode == 'OBJECT'):
                return True
            else:
                return False
        except:
            return False

    def execute(self, context):
        extension = self.filepath.split(".")[-1]
        if extension != "pkl":
            self.report({'ERROR'}, f"File should be a pickle file with .pkl extension, got {extension} from {self.filepath}")
            return {'CANCELLED'}

        # Read smpl file
        with open(self.filepath, "rb") as fp:
            data = pickle.load(fp)
            smpl_params = {
                "smpl_poses": data["smpl_poses"],
                "smpl_trans": data["smpl_trans"] / 100000  # still normalized, but not used now
            }

        logging.info(f"Read SMPL from {self.filepath}")

        gender = context.window_manager.smpl_loader.smpl_gender
        path = os.path.dirname(os.path.realpath(__file__))
        objects_path = os.path.join(path, "data", "smpl-model-20200803.blend", "Object")
        object_name = "SMPL-mesh-" + gender

        bpy.ops.wm.append(filename=object_name, directory=str(objects_path))

        # Select object
        object_name = context.selected_objects[-1].name
        obj = bpy.data.objects[object_name]
        obj.select_set(True)

        # Write animation
        rotation_euler_xyz, _ = GetAnimation(smpl_params)  # discard translation output
        for b in obj.pose.bones:
            b.rotation_mode = "XYZ"
        obj.animation_data_create()
        obj.animation_data.action = bpy.data.actions.new(name="SMPL motion")

        for bone_name, bone_data in rotation_euler_xyz.items():
            fcurve_0 = obj.animation_data.action.fcurves.new(
                data_path=f'pose.bones["{bone_name}"].rotation_euler', index=0
            )
            fcurve_1 = obj.animation_data.action.fcurves.new(
                data_path=f'pose.bones["{bone_name}"].rotation_euler', index=1
            )
            fcurve_2 = obj.animation_data.action.fcurves.new(
                data_path=f'pose.bones["{bone_name}"].rotation_euler', index=2
            )
            for frame in range(1, bone_data.shape[0] + 1):
                fcurve_0.keyframe_points.insert(frame=frame, value=bone_data[frame - 1, 0])
                fcurve_1.keyframe_points.insert(frame=frame, value=bone_data[frame - 1, 1])
                fcurve_2.keyframe_points.insert(frame=frame, value=bone_data[frame - 1, 2])

        obj.animation_data.action.frame_start = 1
        obj.animation_data.action.frame_end = bone_data.shape[0]

        bpy.context.scene.render.fps = 30

        return {'FINISHED'}

class SMPL_PT_Panel(bpy.types.Panel):
    bl_label = "SMPL Load File"
    bl_category = "SMPL_Load_File"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        col.prop(context.window_manager.smpl_loader, "smpl_gender")
        col.separator()
        col.label(text="Read pickle:")
        col.operator("scene.smpl_open_pkl", text="Open Pickle")

classes = [
    SMPLProperties,
    OpenSmplPklOperator,
    SMPL_PT_Panel,
]

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.WindowManager.smpl_loader = PointerProperty(type=SMPLProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
    del bpy.types.WindowManager.smpl_loader

if __name__ == "__main__":
    print("Add SMPL_Load")
    register()

import bpy
from bpy.types import Operator
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector, Matrix, Quaternion, Euler
import math
from pathlib import Path
import json
import sys
import os
import bmesh


def delete_scene_objects(scene=None):
    """Delete a scene and all its objects."""
    #
    # Sort out the scene object.
    if scene is None:
        # Not specified: it's the current scene.
        scene = bpy.context.scene
    else:
        if isinstance(scene, str):
            # Specified by name: get the scene object.
            scene = bpy.data.scenes[scene]
        # Otherwise, assume it's a scene object already.
    #
    # Remove objects.
    for object_ in scene.objects:
        bpy.data.objects.remove(object_, do_unlink=True)
    #


def parse_json_vector2_array(json_vector_array):
    return_list = []
    for json_vec in json_vector_array:
        vec = Vector((float(json_vec["x"]), float(json_vec["y"])))
        return_list.append(vec)
    return return_list


def parse_json_vector3_array(json_vector_array):
    return_list = []
    for json_vec in json_vector_array:
        vec = Vector((float(json_vec["x"]), float(
            json_vec["z"]), float(json_vec["y"])))  # switch y and z
        return_list.append(vec)
    return return_list


def trianglelist_to_facelist(triangle_list):
    face_list = []
    for i in range(int(len(triangle_list)/3)):
        face_list.append(
            [triangle_list[i*3+0], triangle_list[i*3+1], triangle_list[i*3+2]])
    return face_list

def load_material_json(path):
    with open(str(path), 'r', encoding='utf-8') as file:
        datastore = json.load(file)
    return datastore

def create_blendermaterial_from_visualmaterial(visualmaterial_hash, exports_root_path):

    visualmaterial = load_material_json(exports_root_path / "Materials" / ("VisualMaterial_"+visualmaterial_hash+".json"))
    texture = visualmaterial["textures"][0]["texture"]
    texture_name = ""
    if texture is not None:
        texture_name = texture["name"]

    mat = bpy.data.materials.get("vismat_"+visualmaterial_hash)

    if mat is None:
        mat = bpy.data.materials.new(
            name="vismat_"+visualmaterial_hash)
        tex = bpy.data.textures.get(
            "texture_"+visualmaterial_hash)
        if tex is None:

            texture_path = exports_root_path / "Resources" / "Textures" / (texture_name+".png")

            img = bpy.data.images.load(str(texture_path.absolute()), check_existing=True)
            print(img)
            print(img.filepath)

            mat.use_nodes = True
            mat.blend_method = 'CLIP'
            nodes = mat.node_tree.nodes
            
            nodes.clear()

            node_output = nodes.new('ShaderNodeOutputMaterial')
            node_output.location = (900, 0)

            node_diffuse = nodes.new('ShaderNodeBsdfDiffuse')
            node_diffuse.location = (300, 200)

            node_image = nodes.new('ShaderNodeTexImage')
            node_image.image = img
            node_image.location = (0, 0)

            node_invert = nodes.new('ShaderNodeInvert')
            node_invert.location = (300, 0)

            node_transparent_bsdf = nodes.new('ShaderNodeBsdfTransparent')
            node_transparent_bsdf.location = (300, -200)

            node_mix_shader = nodes.new('ShaderNodeMixShader')
            node_mix_shader.location = (600, 0)

            links = mat.node_tree.links

            # link texture to diffuse node, then diffuse node to output
            links.new(node_image.outputs[0], node_diffuse.inputs[0])
            links.new(node_image.outputs[1], node_invert.inputs[1])
            links.new(node_transparent_bsdf.outputs[0], node_mix_shader.inputs[2])
            links.new(node_diffuse.outputs[0], node_mix_shader.inputs[1])
            links.new(node_invert.outputs[0], node_mix_shader.inputs[0])
            links.new(node_mix_shader.outputs[0], node_output.inputs[0])

    return mat

def func_generateobjectlistsblend(exports_root, family_name, output_path):

    exports_root_path = Path(exports_root)
    family_name = family_name  # family .json file
    output_path = output_path  # .blend file that will be output

    family_path = exports_root_path / "Families" / \
        family_name / ("Family_"+family_name+".json")

    with open(str(family_path), 'r') as family_file:
        family_data = json.load(family_file)

        entry_iter = -1

        for val_objectlist in family_data["objectLists"]:

            objectlist_path = family_path.parent / \
                ("ObjectList_" + val_objectlist + ".json")
            with open(str(objectlist_path), 'r', encoding='utf-8') as olf:
                objectlist_data = json.load(olf)

                objectlist_path = Path(output_path) / family_name / ("Family_" + family_name + "_" + val_objectlist + ".blend")

                if not objectlist_path.parent.exists():
                    os.makedirs(str(objectlist_path.parent))

                for val in objectlist_data:
                    entry_iter += 1
                    if (val["po"] is None):
                        continue
                    visualset = val["po"]["visualSet"][0]
                    obj = visualset["obj"]
                    vertices = parse_json_vector3_array(obj["vertices"])
                    normals = parse_json_vector3_array(obj["normals"])

                    subblocks = obj["subblocks"]
                    subblock_iter = 0

                    subblock_objects = []

                    for subblock in subblocks:

                        if subblock["$type"] == "OpenSpaceImplementation.Visual.MeshElement":
                            uvs = parse_json_vector2_array(subblock["uvs"])

                            triangles = subblock["disconnected_triangles_spe"]
                            mapping_uvs_spe = subblock["mapping_uvs_spe"]
                            subblock_normals = subblock["normals_spe"]
                            faces = trianglelist_to_facelist(triangles)

                            # make blender material from visual material
                            visualmaterial_hash = subblock["visualMaterial"]["Hash"]

                            mat = create_blendermaterial_from_visualmaterial(visualmaterial_hash, exports_root_path)

                            # let blender build the mesh
                            mesh = bpy.data.meshes.new(
                                name="mesh_subblock_"+str(subblock_iter))
                            mesh.from_pydata(vertices, [], faces)

                            # set normals
                            for vertex in mesh.vertices:
                                vertex.normal = normals[vertex.index]

                            subblock_object = bpy.data.objects.new(
                                "subblock_"+str(subblock_iter), mesh)
                            subblock_object.data.materials.append(mat)

                            #bm = bmesh.new()
                            # bm.from_mesh(mesh)

                            for face in subblock_object.data.polygons:
                                for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                                    uv_layer = mesh.uv_layers.active
                                    if (uv_layer is None):
                                        uv_layer = mesh.uv_layers.new(name="uvs")
                                        uv_layer.active = True

                                    uv_coords = subblock_object.data.uv_layers.active.data[loop_idx].uv
                                    triangle_start = int(face.index*3)

                                    triangle_slice = triangles[triangle_start:triangle_start+3]

                                    # select triangle in the triangle list and check index of the vertex in the list
                                    vertex_index_in_trianglelist = triangle_start + \
                                        triangle_slice.index(vert_idx)

                                    uv_coords.x = uvs[mapping_uvs_spe[0]
                                                      [vertex_index_in_trianglelist]].x
                                    uv_coords.y = uvs[mapping_uvs_spe[0]
                                                      [vertex_index_in_trianglelist]].y

                            #subblockObject.parent = entryObject
                            bpy.context.scene.collection.objects.link(subblock_object)
                            subblock_objects.append(subblock_object)

                            print ("Add subblock")
                            print(subblock_object)

                        elif subblock["$type"] == "OpenSpaceImplementation.Visual.SpriteElement":

                            sprites = subblock["sprites"]
                            sprite_first = sprites[0]

                            # make blender material from visual material
                            visualmaterial_hash = sprite_first["visualMaterial"]["Hash"]

                            mat = create_blendermaterial_from_visualmaterial(visualmaterial_hash, exports_root_path)

                            mesh = bpy.data.meshes.new(
                                name="sprite_subblock_"+str(subblock_iter))

                            sprite_size_x = sprite_first["info_scale"]["x"]
                            sprite_size_y = sprite_first["info_scale"]["y"]

                            plane_vertices = [
                                (-sprite_size_x, 0, -sprite_size_y),
                                (sprite_size_x, 0, -sprite_size_y),
                                (sprite_size_x, 0, sprite_size_y),
                                (-sprite_size_x, 0, sprite_size_y)
                            ]
                            plane_faces = [(0, 1, 2, 3)]
                            mesh.from_pydata(plane_vertices, [], plane_faces)

                            plane_uvs = [
                                (0, 0),
                                (1, 0),
                                (1, 1),
                                (0, 1)
                            ]

                            subblock_object = bpy.data.objects.new(
                                "subblock_"+str(subblock_iter), mesh)
                            subblock_object.data.materials.append(mat)

                            face = subblock_object.data.polygons[0]
                            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                                uv_layer = mesh.uv_layers.active
                                if uv_layer is None:
                                    uv_layer = mesh.uv_layers.new(name="uvs")
                                    uv_layer.active = True

                                uv_coords = subblock_object.data.uv_layers.active.data[loop_idx].uv

                                uv_coords.x = plane_uvs[vert_idx][0]
                                uv_coords.y = plane_uvs[vert_idx][1]

                            bpy.context.scene.collection.objects.link(subblock_object)
                            subblock_objects.append(subblock_object)

                        subblock_iter += 1

                        if not subblock_objects: # length = 0
                            continue

                        # Join objects together
                        bpy.ops.object.select_all(action='DESELECT')
                        for sbo in subblock_objects:
                            sbo.select_set(True)
                        bpy.context.view_layer.objects.active = subblock_objects[0]
                        bpy.ops.object.join()

                        subblock_objects = subblock_objects[:1] # after joining, only one element remains 

                        context = bpy.context

                        # Remove doubles
                        bpy.ops.object.select_all(action='DESELECT')

                        for sbo in subblock_objects:
                            sbo.select_set(True)
                        distance = 0.0001
                        meshes = set(
                            o.data for o in context.selected_objects if o.type == 'MESH')

                        bmesh_removedoubles = bmesh.new()

                        for mesh in meshes:
                            bmesh_removedoubles.from_mesh(mesh)
                            bmesh.ops.remove_doubles(
                                bmesh_removedoubles, verts=bmesh_removedoubles.verts, dist=distance)
                            bmesh_removedoubles.to_mesh(mesh)
                            mesh.update()
                            bmesh_removedoubles.clear()

                        bmesh_removedoubles.free()

                        mesh = context.object.data
                        for polygon in mesh.polygons:
                            polygon.use_smooth = True

                        # Deselect again
                        bpy.ops.object.select_all(action='DESELECT')

                    if not subblock_objects:  # length = 0
                        print("no object_"+str(entry_iter))
                        continue
                    subblock_objects[0].name = "object_"+str(entry_iter)
                    subblock_objects[0].location = (
                        int(((entry_iter+1) % 10)*5), (int((entry_iter+1)/10)*5), 0)

                    print("object_"+str(entry_iter))

                bpy.ops.wm.save_as_mainfile(filepath=str(
                    objectlist_path.absolute()), relative_remap=True)


def func_buildanimations(exports_root, family_name, blendfile_dir):

    exports_root_path = Path(exports_root)
    family_name = family_name  # family .json file
    blend_path = Path(blendfile_dir)  # directory of .blend object lists

    family_path = exports_root_path / "Families" / \
        family_name / ("Family_"+family_name+".json")

    with open(str(family_path), 'r', encoding='utf-8') as f:
        datastore = json.load(f)

        entry_iter = -1

        for val_objectlist in datastore["objectLists"]:

            objectlist_path = family_path.parent / \
                ("ObjectList_" + val_objectlist + ".json")
            with open(str(objectlist_path), 'r', encoding='utf-8') as olf:
                objectlist_data = json.load(olf)

                states = datastore["states"]
                state_count = len(states)

                objectsToKeep = []

                for state in states:
                    state_index = state["index"]
                    state_path = family_path.parent / \
                        ("State_" + str(state_index) + ".json")

                    print("State "+str(state_index)+"/"+str(state_count))

                    with open(str(state_path), encoding='utf-8') as sf:
                        state_data = json.load(sf)
                        print("animation length: " +
                              str(state_data["animationLength"]))

                        delete_scene_objects()

                        blendfile_path = Path(
                            blend_path) / family_name / ("Family_"+family_name+"_"+val_objectlist+".blend")

                        bpy.ops.wm.open_mainfile(filepath=str(blendfile_path))
                        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

                        anim_length = state_data["animationLength"]
                        bpy.context.scene.frame_end = anim_length

                        bpy.ops.object.select_all(action='DESELECT')

                        state_objects = {}

                        if (state_data["instances"] is None):
                            continue

                        for instance in state_data["instances"]:

                            object_name = (
                                "object_"+str(instance["familyObjectIndex"]))

                            if (not(object_name in bpy.data.objects)):
                                print("Didn't find "+object_name)
                                continue
                            family_object = bpy.data.objects[object_name]

                            family_object.select_set(True)
                            copied_family_object = family_object.copy()
                            bpy.context.scene.collection.objects.link(
                                copied_family_object)
                            objectsToKeep.append(copied_family_object)

                            if instance["channelId"] not in state_objects:
                                state_objects[instance["channelId"]] = {}

                            #copiedFamObj = bpy.context.active_object

                            # Set the scale to 1
                            copied_family_object.scale = Vector((1, 1, 1))
                            # Set the location at rest (edit) pose bone position
                            copied_family_object.location = Vector((0, 0, 0))

                            state_objects[instance["channelId"]
                                          ][instance["familyObjectIndex"]] = copied_family_object

                            for frame in range(0, anim_length):
                                copied_family_object.hide_viewport = not(
                                    bool(instance["visibilities"][frame]))
                                copied_family_object.hide_render = not(
                                    bool(instance["visibilities"][frame]))
                                copied_family_object.keyframe_insert(
                                    data_path="hide_viewport", frame=frame)
                                copied_family_object.keyframe_insert(
                                    data_path="hide_render", frame=frame)

                        # Create Armature for state
                        armature = bpy.data.armatures.new("armature")
                        armature_object = bpy.data.objects.new(
                            ('Armature_'+str(state_index)), armature)
                        bpy.context.scene.collection.objects.link(armature_object)
                        objectsToKeep.append(armature_object)

                        # Set edit mode
                        bpy.context.view_layer.objects.active = armature_object
                        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
                        edit_bones = armature_object.data.edit_bones

                        print(state_data["channels"].keys())

                        for channel_id in state_data["channels"].keys():

                            channel_id = channel_id.encode("ascii", errors="ignore").decode()
                            # Edit mode to create bones
                            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

                            if channel_id == "$type":
                                continue

                            if int(channel_id) not in state_objects:
                                continue

                            channel = state_data["channels"][channel_id]

                            bone_name = u'Channel_'+str(int(channel_id))
                            bone = edit_bones.new(bone_name)
                            edit_bones.active = bone

                            # a new bone will have zero length and not be kept
                            # move the head/tail to keep the bone

                            bone_x = float(channel["positions"][0]["x"])
                            bone_y = float(channel["positions"][0]["y"])
                            bone_z = float(channel["positions"][0]["z"])
                            bone.head = (0, 0.0001, 0)
                            bone.tail = (0, 0, 0)

                            # Object mode to parent objects to bones
                            bpy.ops.object.mode_set(mode='OBJECT')

                            for state_object in state_objects[int(channel_id)].values():

                                state_object.parent = armature_object
                                state_object.parent_type = 'BONE'

                                state_object.parent_bone = bone_name
                                state_object.location = (0, 0, 0)

                        # exit edit mode to save bones so they can be used in pose mode
                        bpy.ops.object.mode_set(mode='OBJECT')

                        for channel_id in state_data["channels"].keys():

                            if channel_id == "$type":
                                continue

                            for frame in range(0, anim_length):

                                # enter pose mode
                                bpy.ops.object.mode_set(mode='POSE')

                                channel = state_data["channels"][channel_id]
                                channel_name = 'Channel_'+str(channel_id)

                                if channel_name not in armature_object.pose.bones:
                                    continue

                                bone = armature_object.pose.bones[channel_name]
                                # a new bone will have zero length and not be kept
                                # move the head/tail to keep the bone

                                bone_x = float(
                                    channel["positions"][frame]["x"])
                                bone_y = float(
                                    channel["positions"][frame]["y"])
                                bone_z = float(
                                    channel["positions"][frame]["z"])

                                # -y,-z-x,w

                                rotation_x = float(
                                    channel["rotations"][frame]["x"])
                                rotation_y = float(
                                    channel["rotations"][frame]["y"])
                                rotation_z = float(
                                    channel["rotations"][frame]["z"])
                                rotation_w = float(
                                    channel["rotations"][frame]["w"])

                                scale_x = float(channel["scales"][frame]["x"])
                                scale_y = float(channel["scales"][frame]["y"])
                                scale_z = float(channel["scales"][frame]["z"])

                                bone.location = (bone_x, bone_z, bone_y)

                                rot = Quaternion(
                                    (-rotation_w, rotation_x, rotation_z, rotation_y))

                                bone.rotation_quaternion = rot
                                bone.scale = (scale_x, scale_z, scale_y)

                                # Object Mode for keyframe insertion
                                bpy.ops.object.mode_set(mode='OBJECT')

                                #b.keyframe_insert(data_path="hide" ,frame=frame)
                                #b.keyframe_insert(data_path="hide_render" ,frame=frame)
                                bone.keyframe_insert(
                                    data_path="location", frame=frame)
                                bone.keyframe_insert(
                                    data_path="rotation_quaternion", frame=frame)
                                bone.keyframe_insert(
                                    data_path="scale", frame=frame)

                    scene = bpy.context.scene #bpy.context.screen.scene

                    # Remove objects.
                    for object_ in scene.objects:
                        if object_ not in objectsToKeep:
                            bpy.data.objects.remove(object_, do_unlink=True)

                    state_blend_path = blend_path / family_name / \
                        (family_name + "_" + val_objectlist +
                         ("_State"+str(state_index))+".blend")
                    if not state_blend_path.parent.exists():
                        os.makedirs(str(state_blend_path.parent))
                        
                    bpy.ops.wm.save_as_mainfile(filepath=str(
                        state_blend_path.absolute()), relative_remap=True)

# Delete the current scene.
delete_scene_objects()

ARGV = sys.argv
ARGV = ARGV[ARGV.index("--") + 1:]  # get all args after "--"
ACTION = ARGV[0]

if ACTION == 'generateObjectLists':
    EXPORTS_ROOT = ARGV[1]
    FAMILY_NAME = ARGV[2]  # family .json file
    OUTPUT_PATH = ARGV[3]  # .blend file that will be output

    func_generateobjectlistsblend(EXPORTS_ROOT, FAMILY_NAME, OUTPUT_PATH)
elif ACTION == 'buildAnimations':

    EXPORTS_ROOT = ARGV[1]
    FAMILY_NAME = ARGV[2]  # family .json file
    BLENDFILE_DIR = ARGV[3]  # directory of .blend object lists

    func_buildanimations(EXPORTS_ROOT, FAMILY_NAME, BLENDFILE_DIR)
else:
    print("Unknown action " + ACTION +
          ", please provide either generateObjectLists or buildAnimations as an action")

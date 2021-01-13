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
import numpy as np

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

def parse_json_vector3(json_vec):
    vec = Vector((float(json_vec["x"]), float(json_vec["y"]), float(json_vec["z"])))  # switch y and z
    return vec

def trianglelist_to_facelist(triangle_list):
    face_list = []
    if (not(triangle_list)):
        return face_list
    for i in range(int(len(triangle_list)/3)):
        face_list.append(
            [triangle_list[i*3+0], triangle_list[i*3+1], triangle_list[i*3+2]])
    return face_list

def load_material_json(path):
    with open(str(path), 'r', encoding='utf-8') as file:
        datastore = json.load(file)
    return datastore

def create_blendermaterial_from_visualmaterial(visualmaterial_hash, exports_root_path, ambient_color):

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
        if tex is None and texture_name is not "":

            texture_path = exports_root_path / "Resources" / "Textures" / (texture_name+".png")

            img = bpy.data.images.load(str(texture_path.absolute()), check_existing=True)

            mat.use_nodes = True
            mat.blend_method = 'CLIP'

            blend_transparency = True if (texture["flags"] & 0x8) else False

            if blend_transparency:
                mat.blend_method = 'BLEND'
            #if visualmaterial["IsLight"] is True: TODO: fix this
                #mat.blend_method = 'ADD'
            
            vismat_diffuse_coef = parse_json_vector3(visualmaterial["diffuseCoef"])
            vismat_ambient_coef = parse_json_vector3(visualmaterial["ambientCoef"])
            color_rgba = ((vismat_diffuse_coef.x * ambient_color.x) + vismat_ambient_coef.x, (vismat_diffuse_coef.y * ambient_color.y) + vismat_ambient_coef.y, (vismat_diffuse_coef.z * ambient_color.z) + vismat_ambient_coef.z, 1.0)
            
            nodes = mat.node_tree.nodes
            
            nodes.clear()

            node_output = nodes.new('ShaderNodeOutputMaterial')
            node_output.location = (1200, 0)

            node_color = nodes.new('ShaderNodeMixRGB')
            node_color.blend_type = 'MULTIPLY'
            node_color.inputs[0].default_value = 1.0 # factor
            node_color.inputs[2].default_value = color_rgba
            node_color.location = (200, 200)

            node_diffuse = nodes.new('ShaderNodeBsdfPrincipled')
            if (mat.blend_method == 'CLIP'):
                node_diffuse.inputs[5].default_value = 0.1 # specular
                node_diffuse.inputs[7].default_value = 0.85 # roughness
            else:
                node_diffuse.inputs[5].default_value = 0.0 # specular
            node_diffuse.location = (300, 400)

            node_image = nodes.new('ShaderNodeTexImage')
            node_image.image = img
            node_image.location = (-100, 0)

            node_invert = nodes.new('ShaderNodeInvert')
            node_invert.location = (300, -400)

            node_brightcontrast = nodes.new('ShaderNodeBrightContrast')
            node_brightcontrast.location = (400, -400)

            node_geometry = nodes.new('ShaderNodeNewGeometry')
            node_geometry.location = (400, -700)

            node_transparent_bsdf = nodes.new('ShaderNodeBsdfTransparent')
            node_transparent_bsdf.location = (300, -200)

            node_mix_shader = nodes.new('ShaderNodeMixShader')
            node_mix_shader.location = (900, 0)

            links = mat.node_tree.links

            # link texture to diffuse node, then diffuse node to output
            links.new(node_image.outputs[0], node_color.inputs[1]) # image color to multiply node
            #links.new(node_image.outputs[0], node_diffuse.inputs[19]) # image color to normal input of principled node
            links.new(node_image.outputs[1], node_invert.inputs[1])
            links.new(node_color.outputs[0], node_diffuse.inputs[0])
            links.new(node_diffuse.outputs[0], node_mix_shader.inputs[1])
            links.new(node_transparent_bsdf.outputs[0], node_mix_shader.inputs[2])

            links.new(node_invert.outputs[0], node_brightcontrast.inputs[0])

            if mat.blend_method == 'CLIP':
                links.new(node_geometry.outputs[6], node_brightcontrast.inputs[1]) # backfacing

            links.new(node_brightcontrast.outputs[0], node_mix_shader.inputs[0])

            links.new(node_mix_shader.outputs[0], node_output.inputs[0])

    return mat

def func_generate_map_blend(exports_root, level_name, output_path):

    exports_root_path = Path(exports_root)
    level_name = level_name  # family .json file
    blend_path = Path(output_path) / (level_name + ".blend")

    level_path = exports_root_path / "Levels" / (level_name+".json")

    with open(str(level_path), 'r') as level_file:
        level_data = json.load(level_file)

        entry_iter = -1

        ambient_lights = {}
             
        for light_name in level_data["LightData"]["Lights"]:
            if (light_name.startswith("$type")):
                continue
            
            light_dict = level_data["LightData"]["Lights"][light_name]
            light_info = light_dict["LightInfo"]
            light_position = parse_json_vector3(light_dict["position"])
            light_rotation = parse_json_vector3(light_dict["rotation"])
            light_scale = parse_json_vector3(light_dict["scale"])

            light_type = light_info["type"]

            if (light_type == 0 or light_type == 6):
                continue

            light_blenddata = None

            color = parse_json_vector3(light_info["color"])
            color_alpha = light_info["color"]["w"]

            # ignore black and alpha lights
            if ((color.x <= 0.01 and color.y <= 0.01 and color.z <= 0.01) or color_alpha<=0.01):
                continue

            if (light_type == 2 or light_type == 8): # sphere
                light_blenddata = bpy.data.lights.new(name="light_"+str(light_name), type='POINT')
                light_blenddata.specular_factor = 0.5
                light_blenddata.shadow_soft_size = light_info["far"] * 2
                light_blenddata.energy = light_info["far"] * 600
                #light_blenddata.shadow_buffer_soft = 25
            elif (light_type == 4): # ambient
                ambient_lights[light_name] = color
                print("Found ambient color: "+light_name+" = "+str(color))
                continue
            elif (light_type == 1): # directional
                light_blenddata = bpy.data.lights.new(name="light_"+str(light_name), type='SUN')
                light_blenddata.shadow_soft_size = 1000
                light_blenddata.energy = 1
                light_blenddata.specular_factor = 0
                #light_blenddata.shadow_buffer_soft = 25
            else:
                continue

            if (light_blenddata is None):
                continue

            light_blenddata.color = parse_json_vector3(light_info["color"]) # no alpha lights for now

            light_object = bpy.data.objects.new("lightObj_"+str(light_name), light_blenddata)
            light_object.location = light_position
            light_object.rotation_euler = light_rotation
            bpy.context.scene.collection.objects.link(light_object)
        
        for sector_name in level_data["WorldData"]["Sectors"]:
            if (sector_name == "$type"):
                continue

            sector_object = bpy.data.objects.new("sector_"+str(sector_name), None)
            bpy.context.scene.collection.objects.link(sector_object)

            sector_dict = level_data["WorldData"]["Sectors"][sector_name]

            geom_iter = 0

            # check ambient lights
            ambient_lights_for_sector = []
            for key,value in ambient_lights.items():
                if key in sector_dict["LightReferences"]:
                    ambient_lights_for_sector.append(value)

            ambient_color_average = Vector((1,1,1))

            if (ambient_lights_for_sector):
                ambient_color_average = Vector(tuple(np.array(ambient_lights_for_sector).sum(0)))
            print("average: "+str(ambient_color_average))

            for geom_name in sector_dict["Geometry"]:
                if geom_name == "$type":
                    continue
                
                geom_dict = sector_dict["Geometry"][geom_name]
                visuals = geom_dict["Visuals"]
                vertices = parse_json_vector3_array(visuals["vertices"])
                normals = parse_json_vector3_array(visuals["normals"])

                subblocks = visuals["elements"]

                subblock_objects = []

                subblock_iter = 0

                for subblock in subblocks:

                    if subblock["$type"] == "OpenSpaceImplementation.Visual.GeometricObjectElementTriangles":
                        uvs = parse_json_vector2_array(subblock["uvs"])

                        triangles = subblock["triangles"]
                        mapping_uvs_spe = subblock["mapping_uvs"]
                        subblock_normals = subblock["normals"]
                        faces = trianglelist_to_facelist(triangles)

                        # make blender material from visual material
                        visualmaterial_hash = subblock["visualMaterial"]["Hash"]

                        mat = create_blendermaterial_from_visualmaterial(visualmaterial_hash, exports_root_path, ambient_color_average)

                        # let blender build the mesh
                        mesh = bpy.data.meshes.new(
                            name="mesh_subblock_"+str(subblock_iter))
                        mesh.from_pydata(vertices, [], faces)

                        # set normals
                        for vertex in mesh.vertices:
                            vertex.normal = normals[vertex.index]

                        subblock_object = bpy.data.objects.new(
                            "subblock_"+str(subblock_iter), mesh)
                        
                        subblock_object.parent = sector_object
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

                    elif subblock["$type"] == "OpenSpaceImplementation.Visual.GeometricObjectElementSprites":

                        sprites = subblock["sprites"]
                        sprite_first = sprites[0]

                        # make blender material from visual material
                        visualmaterial_hash = sprite_first["visualMaterial"]["Hash"]

                        mat = create_blendermaterial_from_visualmaterial(visualmaterial_hash, exports_root_path, ambient_color_average)

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
                    meshes = set(o.data for o in context.selected_objects if o.type == 'MESH')

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
                    subblock_objects[0].name = "object_"+str(geom_iter)

                geom_iter+=1
       

        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path.absolute()), relative_remap=True)
            

        """ for val_objectlist in level_data["objectLists"]:

            objectlist_path = level_path.parent / \
                ("ObjectList_" + val_objectlist + ".json")
            with open(str(objectlist_path), 'r', encoding='utf-8') as olf:
                objectlist_data = json.load(olf)

                objectlist_path = Path(output_path) / level_name / ("Family_" + level_name + "_" + val_objectlist + ".blend")

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
                    objectlist_path.absolute()), relative_remap=True) """


# Delete the current scene.
delete_scene_objects()

ARGV = sys.argv

ARGV = ARGV[ARGV.index("--") + 1:]  # get all args after "--"

EXPORTS_ROOT = ARGV[0]
LEVEL_NAME = ARGV[1]  # family .json file
OUTPUT_PATH = ARGV[2]  # .blend file that will be output

func_generate_map_blend(EXPORTS_ROOT, LEVEL_NAME, OUTPUT_PATH)

import bpy
from bpy.types import Operator
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector, Matrix, Quaternion, Euler
import math
from pathlib import Path
import json
import sys
import bmesh

def delete_scene_objects(scene=None):
    """Delete a scene and all its objects."""
    #
    # Sort out the scene object.
    if scene is None:
        # Not specified: it's the current scene.
        scene = bpy.context.screen.scene
    else:
        if isinstance(scene, str):
            # Specified by name: get the scene object.
            scene = bpy.data.scenes[scene]
        # Otherwise, assume it's a scene object already.
    #
    # Remove objects.
    for object_ in scene.objects:
        bpy.data.objects.remove(object_, True)
    #

def ParseJsonVector2Array(jsonVectorArray):
    returnList = []
    for jsonVec in jsonVectorArray:
        vec = Vector((float(jsonVec["x"]),float(jsonVec["y"])))
        returnList.append(vec)
    return returnList

def ParseJsonVector3Array(jsonVectorArray):
    returnList = []
    for jsonVec in jsonVectorArray:
        vec = Vector((float(jsonVec["x"]),float(jsonVec["z"]),float(jsonVec["y"]))) # switch y and z
        returnList.append(vec)
    return returnList

def TriangleListToFaceList(trianglelist):
    faceList = []
    for i in range(int(len(trianglelist)/3)):
        faceList.append([trianglelist[i*3+0], trianglelist[i*3+1], trianglelist[i*3+2]])
    return faceList

def TriangleListToFaceList(trianglelist):
    faceList = []
    for i in range(int(len(trianglelist)/3)):
        faceList.append([trianglelist[i*3+0], trianglelist[i*3+1], trianglelist[i*3+2]])
    return faceList

def loadMaterialJson(path):
    with open(str(path), 'r', encoding='utf-8') as f:
        datastore = json.load(f)
    return datastore

# Delete the current scene.
delete_scene_objects()

argv = sys.argv;
argv = argv[argv.index("--") + 1:]  # get all args after "--"
function = argv[0]

def func_generateobjectlistsblend(exportsRoot, familyName, outputPath):

    exportsRootPath = Path(exportsRoot)
    familyName = familyName # family .json file
    outputPath = outputPath # .blend file that will be output

    familyPath = exportsRootPath / "Families" / familyName / ("Family_"+familyName+".json")

    with open(str(familyPath), 'r') as f:
        datastore = json.load(f)

        entry_iter = -1

        for val_objectlist in datastore["objectLists"]:

            objectListPath = familyPath.parent / ("ObjectList_" + val_objectlist + ".json")
            with open(str(objectListPath), 'r', encoding='utf-8') as olf:
                objectListDataStore = json.load(olf)

                for val in objectListDataStore:
                    entry_iter += 1
                    if (val["po"] is None):
                        continue
                    visualset = val["po"]["visualSet"][0]
                    obj = visualset["obj"]
                    vertices = ParseJsonVector3Array(obj["vertices"])
                    normals = ParseJsonVector3Array(obj["normals"])
        
                    subblocks = obj["subblocks"]
                    subblock_iter = 0

                    #entryObject = bpy.data.objects.new("object_"+str(entry_iter), None)
                    #bpy.context.scene.objects.link(entryObject)
                    #entryObject.location = (int(((entry_iter+1)%10)*5), (int((entry_iter+1)/10)*5), 0)

                    subblockObjects = []

                    for subblock in subblocks:

                        if subblock["$type"] == "OpenSpaceImplementation.Visual.MeshElement":
                            uvs = ParseJsonVector2Array(subblock["uvs"])

                            gameMaterialHash = subblock["gameMaterial"]["Hash"]
                            visualMaterialHash = subblock["visualMaterial"]["Hash"]

                            visualMaterial = loadMaterialJson(exportsRootPath / "Materials" / ("VisualMaterial_"+visualMaterialHash+".json"))
                            texture = visualMaterial["textures"][0]["texture"]
                            textureName = ""
                            if texture is not None:
                                textureName = texture["name"]

                            triangles = subblock["disconnected_triangles_spe"]
                            mapping_uvs_spe = subblock["mapping_uvs_spe"]
                            subblock_normals = subblock["normals_spe"]
                            faces = TriangleListToFaceList(triangles)

                            mat = bpy.data.materials.get("vismat_"+visualMaterialHash)
                            if mat is None:
                                mat = bpy.data.materials.new(name="vismat_"+visualMaterialHash)
                                mat.specular_intensity = 0
                                tex = bpy.data.textures.get("texture_"+visualMaterialHash)
                                if tex is None:
                                    tex = bpy.data.textures.new("texture_"+visualMaterialHash, "IMAGE")

                                    texturePath = exportsRootPath / "Resources"/ "Textures"/(textureName+".png")

                                    img = bpy.data.images.load(str(texturePath.absolute()), True)
                                    tex.image = img
                                    slot = mat.texture_slots.add()
                                    slot.texture = tex

                            # let blender build the mesh
                            mesh = bpy.data.meshes.new(name="mesh_subblock_"+str(subblock_iter))
                            mesh.from_pydata(vertices, [], faces)

                            # set normals
                            for vertex in mesh.vertices:
                                vertex.normal = normals[vertex.index]

                            subblockObject = bpy.data.objects.new("subblock_"+str(subblock_iter), mesh)
                            subblockObject.data.materials.append(mat)
                        
                            #bm = bmesh.new()
                            #bm.from_mesh(mesh)

                            for face in subblockObject.data.polygons:
                                for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                                    uv_layer = mesh.uv_layers.active
                                    if (uv_layer is None):
                                        uv_layer = mesh.uv_textures.new("uvs")
                                        uv_layer.active = True

                                    uv_coords = subblockObject.data.uv_layers.active.data[loop_idx].uv
                                    triangleStart = int(face.index*3)

                                    slice = triangles[triangleStart:triangleStart+3]

                                    vertexIndexInTriangleList = triangleStart + slice.index(vert_idx); # select triangle in the triangle list and check index of the vertex in the list

                                    uv_coords.x = uvs[mapping_uvs_spe[0][vertexIndexInTriangleList]].x
                                    uv_coords.y = uvs[mapping_uvs_spe[0][vertexIndexInTriangleList]].y
     

                            #subblockObject.parent = entryObject
                            bpy.context.scene.objects.link(subblockObject)
                            subblockObjects.append(subblockObject)

                        elif subblock["$type"] == "OpenSpaceImplementation.Visual.SpriteElement":

                            sprites = subblock["sprites"]
                            firstSprite = sprites[0];

                            visualMaterialHash = firstSprite["visualMaterial"]["Hash"]

                            visualMaterial = loadMaterialJson(exportsRootPath / "Materials" / ("VisualMaterial_"+visualMaterialHash+".json"))
                            texture = visualMaterial["textures"][0]["texture"]
                            textureName = ""
                            if texture is not None:
                                textureName = texture["name"]

                            mat = bpy.data.materials.get("vismat_"+visualMaterialHash)
                            if mat is None:
                                mat = bpy.data.materials.new(name="vismat_"+visualMaterialHash)
                                tex = bpy.data.textures.get("texture_"+visualMaterialHash)
                                if tex is None:
                                    tex = bpy.data.textures.new("texture_"+visualMaterialHash, "IMAGE")

                                    texturePath = exportsRootPath / "Resources"/ "Textures"/(textureName+".png")

                                    img = bpy.data.images.load(str(texturePath.absolute()), True)
                                    tex.image = img
                                    slot = mat.texture_slots.add()
                                    slot.texture = tex

                            mesh = bpy.data.meshes.new(name="sprite_subblock_"+str(subblock_iter))

                            spriteSize = firstSprite["info_scale"];
                            spriteSizeX = firstSprite["info_scale"]["x"];
                            spriteSizeY = firstSprite["info_scale"]["y"];

                            plane_vertices = [
                                (-spriteSizeX,0,-spriteSizeY),
                                (spriteSizeX,0,-spriteSizeY),
                                (spriteSizeX,0,spriteSizeY),
                                (-spriteSizeX,0,spriteSizeY)
                            ];
                            plane_faces = [(0,1,2,3)];
                            mesh.from_pydata(plane_vertices, [], plane_faces);

                            plane_uvs = [
                                (0,0),
                                (1,0),
                                (1,1),
                                (0,1)
                            ];

                            subblockObject = bpy.data.objects.new("subblock_"+str(subblock_iter), mesh)
                            subblockObject.data.materials.append(mat)

                            face = subblockObject.data.polygons[0]
                            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                                uv_layer = mesh.uv_layers.active
                                if (uv_layer is None):
                                    uv_layer = mesh.uv_textures.new("uvs")
                                    uv_layer.active = True

                                uv_coords = subblockObject.data.uv_layers.active.data[loop_idx].uv
                                
                                uv_coords.x = plane_uvs[vert_idx][0]
                                uv_coords.y = plane_uvs[vert_idx][1]

                            bpy.context.scene.objects.link(subblockObject)
                            subblockObjects.append(subblockObject) 

                            print("Plane")
                            
                        subblock_iter+=1

                        if len(subblockObjects) == 0:
                            continue

                        # Join objects together
                        bpy.ops.object.select_all(action='DESELECT')
                        for sbo in subblockObjects:
                            sbo.select = True
                        bpy.context.scene.objects.active = subblockObjects[0]
                        bpy.ops.object.join()
                        
                        context = bpy.context

                        # Remove doubles
                        bpy.ops.object.select_all(action='DESELECT')

                        for sbo in subblockObjects:
                            sbo.select = True
                        distance = 0.0001
                        meshes = set(o.data for o in context.selected_objects
                                            if o.type == 'MESH')

                        bm = bmesh.new()

                        for m in meshes:
                            bm.from_mesh(m)
                            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=distance)
                            bm.to_mesh(m)
                            m.update()
                            bm.clear()

                        bm.free()

                        mesh = context.object.data
                        for f in mesh.polygons:
                            f.use_smooth = True

                        # Deselect again
                        bpy.ops.object.select_all(action='DESELECT')

                    if len(subblockObjects) == 0:
                        print("no object_"+str(entry_iter))
                        continue
                    subblockObjects[0].name = "object_"+str(entry_iter)
                    subblockObjects[0].location = (int(((entry_iter+1)%10)*5), (int((entry_iter+1)/10)*5), 0)

                    print("object_"+str(entry_iter))
                
                op = Path(outputPath) / ("Family_" + familyName + "_" + val_objectlist + ".blend")
                bpy.ops.wm.save_as_mainfile(filepath=str(op))


def func_buildanimations(exportsRoot, familyName, blendFileDir):

    exportsRootPath = Path(argv[1])
    familyName = argv[2] # family .json file
    blendPath = Path(blendFileDir) # directory of .blend object lists 

    familyPath = exportsRootPath / "Families" / familyName / ("Family_"+familyName+".json")

    with open(str(familyPath), 'r') as f:
        datastore = json.load(f)

        entry_iter = -1

        for val_objectlist in datastore["objectLists"]:

            objectListPath = familyPath.parent / ("ObjectList_" + val_objectlist + ".json")
            with open(str(objectListPath), 'r', encoding='utf-8') as olf:
                objectListDataStore = json.load(olf)
                
                states = datastore["states"]
                stateCount = len(states)

                objectsToKeep = []

                for state in states:
                    stateIndex = state["index"]
                    statePath = familyPath.parent / ("State_" + str(stateIndex) + ".json")

                    print("State "+str(stateIndex)+"/"+str(stateCount))

                    with open(str(statePath)) as sf:
                        stateData = json.load(sf)
                        print("animation length: "+str(stateData["animationLength"]))

                        delete_scene_objects()

                        blendFilePath = Path(blendPath) / ("Family_"+familyName+"_"+val_objectlist+".blend")

                        bpy.ops.wm.open_mainfile(filepath=str(blendFilePath))
                        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

                        animLength = stateData["animationLength"]
                        bpy.context.scene.frame_end = animLength

                        bpy.ops.object.select_all(action='DESELECT')

                        stateObjs = {}

                        for instance in stateData["instances"]:

                            objectName = ("object_"+str(instance["familyObjectIndex"]))

                            if (not(objectName in bpy.data.objects)):
                                print("Didn't find "+objectName)
                                continue
                            famObj = bpy.data.objects[objectName]

                            famObj.select = True
                            copiedFamObj =  famObj.copy()
                            bpy.context.scene.objects.link(copiedFamObj)
                            objectsToKeep.append(copiedFamObj)

                            if instance["channelId"] not in stateObjs:
                                stateObjs[instance["channelId"]] = {}

                            #copiedFamObj = bpy.context.active_object

                            #Set the scale to 1
                            copiedFamObj.scale = Vector( (1, 1, 1) )
                            #Set the location at rest (edit) pose bone position
                            copiedFamObj.location = Vector ( (0,0,0) )

                            stateObjs[instance["channelId"]][instance["familyObjectIndex"]] = copiedFamObj

                            for frame in range(0,animLength):
                                copiedFamObj.hide = not(bool(instance["visibilities"][frame]))
                                copiedFamObj.hide_render = not(bool(instance["visibilities"][frame]))
                                copiedFamObj.keyframe_insert(data_path="hide" ,frame=frame)

                        # Create Armature for state
                        armature = bpy.data.armatures.new("armature")
                        armatureObject = bpy.data.objects.new(('Armature_'+str(stateIndex)), armature)
                        bpy.context.scene.objects.link(armatureObject)
                        objectsToKeep.append(armatureObject)

                        # Set edit mode
                        bpy.context.scene.objects.active = armatureObject
                        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
                        edit_bones = armatureObject.data.edit_bones

                        for channelID in stateData["channels"].keys():
                            
                            # Edit mode to create bones
                            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

                            if (channelID == "$type"):
                                continue

                            if (int(channelID) not in stateObjs):
                                continue

                            channel = stateData["channels"][channelID]
                            b = edit_bones.new('Channel_'+str(channelID))
                            # a new bone will have zero length and not be kept
                            # move the head/tail to keep the bone

                            bx = float(channel["positions"][0]["x"])
                            by = float(channel["positions"][0]["y"])
                            bz = float(channel["positions"][0]["z"])

                            b.head = (0, 0.0001, 0)
                            b.tail = (0, 0, 0)

                            # Object mode to parent objects to bones
                            bpy.ops.object.mode_set(mode='OBJECT')

                            for stateObj in stateObjs[int(channelID)].values():

                                stateObj.parent = armatureObject
                                stateObj.parent_type = 'BONE'
                                stateObj.parent_bone = b.name
                                stateObj.location = (0,0,0)

                        # exit edit mode to save bones so they can be used in pose mode
                        bpy.ops.object.mode_set(mode='OBJECT')

                        for channelID in stateData["channels"].keys():
                            
                            if (channelID == "$type"):
                                continue
    
                            for frame in range(0,animLength):

                                # enter pose mode
                                bpy.ops.object.mode_set(mode='POSE')

                                channel = stateData["channels"][channelID]
                                channelName = 'Channel_'+str(channelID)

                                if (channelName not in armatureObject.pose.bones):
                                    continue

                                b = armatureObject.pose.bones[channelName]
                                # a new bone will have zero length and not be kept
                                # move the head/tail to keep the bone

                                bx = float(channel["positions"][frame]["x"])
                                by = float(channel["positions"][frame]["y"])
                                bz = float(channel["positions"][frame]["z"])

                                #-y,-z-x,w

                                rx = float(channel["rotations"][frame]["x"])
                                ry = float(channel["rotations"][frame]["y"]) 
                                rz = float(channel["rotations"][frame]["z"])
                                rw = float(channel["rotations"][frame]["w"])

                                sx = float(channel["scales"][frame]["x"])
                                sy = float(channel["scales"][frame]["y"])
                                sz = float(channel["scales"][frame]["z"])

                                b.location = (bx,bz,by)

                                rot = Quaternion((-rw, rx, rz, ry))

                                b.rotation_quaternion = rot
                                b.scale = (sx, sz, sy)
                                
                                # Object Mode for keyframe insertion
                                bpy.ops.object.mode_set(mode='OBJECT')
                            
                                #b.keyframe_insert(data_path="hide" ,frame=frame)
                                #b.keyframe_insert(data_path="hide_render" ,frame=frame)
                                b.keyframe_insert(data_path="location" ,frame=frame)
                                b.keyframe_insert(data_path="rotation_quaternion" ,frame=frame)
                                b.keyframe_insert(data_path="scale" ,frame=frame)


                    scene = bpy.context.screen.scene
                    
                    # Remove objects.
                    for object_ in scene.objects:
                        if (object_ not in objectsToKeep):
                            bpy.data.objects.remove(object_, True)

                    op = blendPath / (familyName + "_" + val_objectlist + ("_State"+str(stateIndex))+".blend")
                    bpy.ops.wm.save_as_mainfile(filepath=str(op))

if function == 'generateObjectLists':
    exportsRoot = argv[1]
    familyName = argv[2] # family .json file
    outputPath = argv[3] # .blend file that will be output

    func_generateobjectlistsblend(exportsRoot, familyName, outputPath)
elif function == 'buildAnimations':

    exportsRoot = argv[1]
    familyName = argv[2] # family .json file
    blendFileDir = argv[3] # directory of .blend object lists 

    func_buildanimations(exportsRoot, familyName, blendFileDir)
else:
    print("Unknown function "+function+", please provide either generateObjectLists or buildAnimations as a function")
import bpy
from bpy.types import Operator
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector
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

def func_generateobjectlistsblend():

    exportsRootPath = Path(argv[1])
    familyName = argv[2] # family .json file
    outputPath = argv[3] # .blend file that will be output

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

                        subblock_iter+=1

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

                        print("meshes")
                        print(meshes)

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

                    subblockObjects[0].name = "object_"+str(entry_iter)
                    subblockObjects[0].location = (int(((entry_iter+1)%10)*5), (int((entry_iter+1)/10)*5), 0)
                
                op = Path(outputPath) / ("Family_" + familyName + "_" + val_objectlist + ".blend")
                bpy.ops.wm.save_as_mainfile(filepath=str(op))


def func_buildanimations():

    exportsRootPath = Path(argv[1])
    familyName = argv[2] # family .json file
    blendPath = Path(argv[3]) # directory of .blend object lists 

    familyPath = exportsRootPath / "Families" / familyName / ("Family_"+familyName+".json")

    with open(str(familyPath), 'r') as f:
        datastore = json.load(f)

        entry_iter = -1

        for val_objectlist in datastore["objectLists"]:

            objectListPath = familyPath.parent / ("ObjectList_" + val_objectlist + ".json")
            with open(str(objectListPath), 'r', encoding='utf-8') as olf:
                objectListDataStore = json.load(olf)
                
                states = datastore["states"]

                for state in states:
                    stateIndex = state["index"]
                    statePath = familyPath.parent / ("State_" + str(stateIndex) + ".json")

                    print(str(stateIndex)+" "+str(statePath))

                    with open(str(statePath)) as sf:
                        stateData = json.load(sf)
                        print("animation length: "+str(stateData["animationLength"]))

                        delete_scene_objects()

                        blendFilePath = Path(blendPath) / ("Family_"+familyName+"_"+val_objectlist+".blend")

                        bpy.ops.wm.open_mainfile(filepath=str(blendFilePath))
                        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

                        animLength = stateData["animationLength"]

                        bpy.ops.object.select_all(action='DESELECT')

                        stateObjs = {}

                        for instance in stateData["instances"]:

                            famObj = bpy.data.objects[("object_"+str(instance["familyObjectIndex"]))]
                            famObj.select = True
                            bpy.ops.object.duplicate(linked=True)

                            if instance["channelId"] not in stateObjs:
                                stateObjs[instance["channelId"]] = {}

                            stateObjs[instance["channelId"]][instance["familyObjectIndex"]] = bpy.context.object

                        # Create Armature for state
                        armature = bpy.data.armatures.new("armature")
                        armatureObject = bpy.data.objects.new(('Armature_'+str(stateIndex)), armature)
                        bpy.context.scene.objects.link(armatureObject)

                        # Set edit mode
                        bpy.context.scene.objects.active = armatureObject
                        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
                        edit_bones = armatureObject.data.edit_bones
                        
                        for channelID in stateData["channels"].keys():
                            
                            if (channelID == "$type"):
                                continue

                            channel = stateData["channels"][channelID]
                            b = edit_bones.new('Channel_'+str(channelID))
                            # a new bone will have zero length and not be kept
                            # move the head/tail to keep the bone

                            bx = float(channel["positions"][0]["x"])
                            by = float(channel["positions"][0]["y"])
                            bz = float(channel["positions"][0]["z"])

                            print(channelID)
                            print(str((bx, by, bz)))

                            b.head = (bx, by, bz)
                            b.tail = (bx, by, bz + 0.1)

                        # exit edit mode to save bones so they can be used in pose mode
                        bpy.ops.object.mode_set(mode='OBJECT')


                    op = blendPath / (familyName + "_" + val_objectlist + ("_State"+str(stateIndex))+".blend")
                    bpy.ops.wm.save_as_mainfile(filepath=str(op))

                        #for frame in range(0, animLength):


                    #with open(str(statePath), 'r', encoding='utf-8') as sf:
                        #bpy.context.scene.objects

                #op = Path(outputPath) / (p.stem + "_" + val_objectlist + ".blend")
                #bpy.ops.wm.save_as_mainfile(filepath=str(op))

if function == 'generateObjectLists':
    func_generateobjectlistsblend()
elif function == 'buildAnimations':
    func_buildanimations()
else:
    print("Unknown function "+function+", please provide either generateObjectLists or buildAnimations as a function")
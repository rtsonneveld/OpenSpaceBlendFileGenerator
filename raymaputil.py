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
    print("triangelist length: "+str(len(trianglelist)))
    for i in range(int(len(trianglelist)/3)):
        faceList.append([trianglelist[i*3+0], trianglelist[i*3+1], trianglelist[i*3+2]])
    return faceList

def TriangleListToFaceList(trianglelist):
    faceList = []
    print("triangelist length: "+str(len(trianglelist)))
    for i in range(int(len(trianglelist)/3)):
        faceList.append([trianglelist[i*3+0], trianglelist[i*3+1], trianglelist[i*3+2]])
    return faceList
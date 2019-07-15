import bpy
from bpy.types import Operator
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector
from pathlib import Path
import json
import sys
import bmesh

from raymaputil import *

# Delete the current scene.
delete_scene_objects()

argv = sys.argv;
argv = argv[argv.index("--") + 1:]  # get all args after "--"
inputPath = argv[0] # family .json file, needs the object list .blend in the same directory (generate with 
outputPath = argv[1] # directory to output animations to

def loadMaterialJson(filename):
    with open(str(Path("Materials") / filename), 'r', encoding='utf-8') as f:
        datastore = json.load(f)
    return datastore

with open(inputPath, 'r') as f:
    datastore = json.load(f)

    entry_iter = -1

    p = Path(inputPath)

    for val_objectlist in datastore["objectLists"]:

        objectListPath = p.parent / ("ObjectList_" + val_objectlist + ".json")
        with open(str(objectListPath), 'r', encoding='utf-8') as olf:
            objectListDataStore = json.load(olf)

            for val in objectListDataStore:
                entry_iter += 1
                if (val["po"] is None):
                    continue
                
                states = obj["states"]

                for state in states:
                    stateIndex = state["index"]
                    statePath = p.parent / ("State" + stateIndex + ".json")
                    with open(str(statePath), 'r', encoding='utf-8') as sf:
                        bpy.context.scene.objects
                

                op = Path(outputPath) / (p.stem + "_" + val_objectlist + ".blend")
                bpy.ops.wm.save_as_mainfile(filepath=str(op))

#mesh = bpy.data.meshes.new(name="Brick")
#mesh.from_pydata(verts, edges, faces)
#test = bpy.data.objects.new("Test", mesh)
#bpy.context.scene.objects.link(test)
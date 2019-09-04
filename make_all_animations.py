import sys
import os
from pathlib import Path

EXPORTS_ROOT = sys.argv[1]
OUTPUTDIR = EXPORTS_ROOT+"\\BlendFiles\\Families"
FAMILY_PATH = str(Path(EXPORTS_ROOT)/"Families")
print(FAMILY_PATH)

for root, dirs, filenames in os.walk(FAMILY_PATH):
    count = 1
    total = len(dirs)
    for family in dirs:
        print("Exporting Family "+family+" ("+str(count)+"/"+str(total)+")")

        os.system("blender --background --python generate_objectlist_blend.py -- generateObjectLists \"" +
                  EXPORTS_ROOT+"\" "+family+" \""+OUTPUTDIR+"\"")
        os.system("blender --background --python make_all_animations.py -- buildAnimations \"" +
                  EXPORTS_ROOT+"\" "+family+" \""+OUTPUTDIR+"\"")

        count += 1
    break

import sys
import os
from pathlib import Path

exportsRoot = sys.argv[1]
outputDir = exportsRoot+"\\BlendFiles\\Families"
familyPath = str(Path(exportsRoot)/"Families")
print(familyPath)

for root,dirs,filenames in os.walk(familyPath):
    count = 1
    total = len(dirs)
    for family in dirs:
        print("Exporting Family "+family+" ("+str(count)+"/"+str(total)+")");

        os.system("blender --background --python GenerateObjectListBlend.py -- generateObjectLists \""+exportsRoot+"\" "+family+" \""+outputDir+"\"")
        os.system("blender --background --python GenerateObjectListBlend.py -- buildAnimations \""+exportsRoot+"\" "+family+" \""+outputDir+"\"")

        count+=1
    break
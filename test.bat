@echo off
set /p family="Enter Family Name: "
blender --background --python GenerateObjectListBlend.py -- generateObjectLists "D:\Dev\Raymap\exports" %family% "exports\BlendFiles\Families"
blender --background --python GenerateObjectListBlend.py -- buildAnimations "D:\Dev\Raymap\exports" %family% "exports\BlendFiles\Families"
pause
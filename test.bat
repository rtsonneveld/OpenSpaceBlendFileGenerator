@echo off
set /p family="Enter Family Name: "
blender --background --python generate_objectlist_blend.py -- generateObjectLists "D:\Dev\Raymap\exports" %family% "D:\Dev\Raymap\exports\BlendFiles\Families"
blender --background --python generate_objectlist_blend.py -- buildAnimations "D:\Dev\Raymap\exports" %family% "D:\Dev\Raymap\exports\BlendFiles\Families"
pause
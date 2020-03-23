@echo off
set /p map="Enter Map Name: "
blender --background --python generate_maps_blend.py -- "D:\Dev\Raymap\exports" %map% "D:\Dev\Raymap\exports\BlendFiles\Levels"
pause
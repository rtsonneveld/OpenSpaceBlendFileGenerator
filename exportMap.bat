@echo off
set /p map="Enter Map Name: "
blender --background --python generate_maps_blend.py -- C:\Data\RaymapData\EXPORT\ %map% C:\Data\RaymapData\EXPORT\BlendFiles\Levels
pause
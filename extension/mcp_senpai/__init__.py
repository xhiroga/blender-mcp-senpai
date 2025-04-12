import bpy

def register():
    print("Hello from extension!", f"{bpy.app.version_string}")
    
def unregister():
    print("Goodbye from extension!")

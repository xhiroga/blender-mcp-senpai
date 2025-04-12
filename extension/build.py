import os
import subprocess
import bpy


def main():
    blender_exe= os.environ.get("BLENDER_EXE") or bpy.app.binary_path
    subprocess.run(
        [blender_exe, "--command", "extension", "build", "--source-dir", "mcp_senpai", "--output-dir", "."],
    )


if __name__ == "__main__":
    main()

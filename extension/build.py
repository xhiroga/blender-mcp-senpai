import os
import subprocess
import tomllib
from dataclasses import dataclass

import bpy
import tomlkit

PLATFORMS = ["windows-x64", "linux-x64", "macos-arm64", "macos-x64"]
ZIP_TARGET_DIR = "mcp_senpai"
OUTPUT_DIR = "output"


@dataclass
class Platform:
    pypi_suffix: str
    metadata: str


windows_x64 = Platform(pypi_suffix="win_amd64", metadata="windows-x64")
linux_x64 = Platform(pypi_suffix="manylinux2014_x86_64", metadata="linux-x64")
macos_arm = Platform(pypi_suffix="macosx_12_0_arm64", metadata="macos-arm64")
macos_intel = Platform(pypi_suffix="macosx_10_16_x86_64", metadata="macos-x64")

platforms = [windows_x64, linux_x64, macos_arm, macos_intel]


def dependencies() -> list[str]:
    with open("pyproject.toml", mode="rb") as f:
        pyproject = tomllib.load(f)
        return [dep.split(">=")[0] for dep in pyproject["project"]["dependencies"]]


def download_whls(
    requirements: list[str],
    python_version: str,
    platform: Platform,
):
    subprocess.run(
        [
            "pip",
            "download",
            *requirements,
            "-d",
            f"{ZIP_TARGET_DIR}/wheels",
            "--only-binary=:all:",
            f"--python-version={python_version}",
            f"--platform={platform.pypi_suffix}",
        ],
    )


def generate_blender_manifest():
    with open("blender_manifest_template.toml", mode="r") as f:
        manifest = tomlkit.load(f)

    manifest["platforms"] = [platform.metadata for platform in platforms]

    manifest["wheels"] = [
        f"./wheels/{f}"
        for f in os.listdir(f"{ZIP_TARGET_DIR}/wheels")
        if f.endswith(".whl")
    ]

    with open(f"{ZIP_TARGET_DIR}/blender_manifest.toml", mode="w") as f:
        tomlkit.dump(manifest, f)


def build():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # On WSL, bpy.app.binary_path is empty.
    blender_exe = os.environ.get("BLENDER_EXE") or bpy.app.binary_path
    subprocess.run(
        [
            blender_exe,
            "--factory-startup",
            "--command",
            "extension",
            "build",
            "--split-platforms",
            "--source-dir",
            ZIP_TARGET_DIR,
            "--output-dir",
            OUTPUT_DIR,
        ],
    )


def index_json():
    blender_exe = os.environ.get("BLENDER_EXE") or bpy.app.binary_path
    subprocess.run(
        [
            blender_exe,
            "--factory-startup",
            "--command",
            "extension",
            "server-generate",
            "--repo-dir",
            OUTPUT_DIR,
        ],
    )

def main():
    for platform in platforms:
        download_whls(dependencies(), "3.11", platform)

    generate_blender_manifest()

    build()

    index_json()


if __name__ == "__main__":
    main()

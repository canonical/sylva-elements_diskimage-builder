"""
Diskimage-builder is still using pkg_resources, we only need to implement this function to make it happy.
This file's directory is Added to PYTHONPATH when calling dib on modern python version.
"""

import importlib_resources


def resource_filename(modname: str, filename: str) -> str:
    return str(importlib_resources.files(modname) / filename)

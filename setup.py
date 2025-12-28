#!/usr/bin/env python3
"""
Setup script for Ashoka RAG system.
"""

from setuptools import setup, find_packages

setup(
    name="ashoka",
    version="0.1.0",
    description="Ashoka RAG system for governance proposal generation",
    py_modules=["ashoka_cli"],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "ashoka=ashoka_cli:main",
        ],
    },
)

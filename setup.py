#!/usr/bin/env python3
"""
Setup script for Ashoka RAG system.
"""

from setuptools import setup, find_packages

setup(
    name="ashoka",
    version="0.1.0",
    description="Ashoka RAG system for governance proposal generation",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "chromadb>=0.4.0",
        "sentence-transformers>=2.2.0",
        "scikit-learn>=1.3.0",
        "numpy>=1.24.0",
        "flask>=2.3.0",
    ],
)

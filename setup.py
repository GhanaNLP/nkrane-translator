"""
Setup script for Terminex
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="terminex",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Terminology-aware translation system using Google Translate with controlled glossaries",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/terminex",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Localization",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
    install_requires=[
        "googletrans==4.0.0rc1",
        "pandas>=1.3.0",
    ],
    include_package_data=True,
)

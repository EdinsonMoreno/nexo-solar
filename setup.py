"""Setup script for Nexo Solar package."""

from setuptools import setup, find_packages

setup(
    name="nexo-solar",
    version="1.0.0",
    description="Nexo Solar - Solar radiation monitoring and control system",
    url="https://github.com/EdinsonMoreno/nexo-solar",
    author="Edinson Andres Moreno Cepeda",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.10",
    install_requires=[
        "pyqt6>=6.0.0",
        "pyqt6-webengine>=6.0.0",
        "pyqt6-charts>=6.0.0",
        "requests>=2.25.0",
        "tqdm>=4.0.0",
        "pymodbus>=3.9.2",
        "pyyaml>=6.0",
        "jsonschema>=4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "hypothesis>=6.0",
            "pylint>=2.0",
            "flake8>=5.0",
            "black>=22.0",
            "mypy>=1.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)

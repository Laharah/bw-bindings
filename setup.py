import pathlib
from setuptools import setup

HERE = pathlib.Path(__file__).parent

README = (HERE / "README.md").read_text()

setup(
    name="bw_bindings",
    version="0.0.1",
    description="A pythonic bindings for the bitwarden CLI",
    long_description=README,
    long_description_content_type="text/markdown",
    url="",
    author="laharah",
    author_email="laharah22+bwb@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Security",
        "Topic :: Software Development :: User Interfaces",
        "Operating System :: POSIX",
    ],
    install_requires=[
        "pynentry >= 0.1.4",
    ],
    py_modules=["bw_bindings"],
)

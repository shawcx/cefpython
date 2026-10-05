# Copyright (c) 2017 CEF Python, see the Authors file.
# All rights reserved. Licensed under BSD 3-clause license.
# Project website: https://github.com/cztomczak/cefpython

"""
cefpython3 package setup.py file.

Usage:
    setup.py install
    setup.py bdist_wheel [--universal]

Options:
    install      Install package
    bdist_wheel  Generate wheel package. Use the --universal flag when
                 you have built cefpython modules for multiple Python
                 versions.
"""

# NOTE: Template variables like {{VERSION}} are replaced with actual
#       values when make_installer.py tool generates this package
#       installer.

import copy
import os
import platform
import re
import subprocess
import sys
import sysconfig

from setuptools import setup
from setuptools.command.install import install
from setuptools.dist import Distribution


# Need to know which files are executables to set appropriate execute
# permissions during post_install_hook. On Windows .exe postfix will
# be added to these automatically.
EXECUTABLES_NOEXT = [
    "cefclient",
    "cefsimple",
    "ceftests",
    "subprocess",
]


class custom_install(install):
    def __init__(self, *args, **kwargs):
        install.__init__(self, *args, **kwargs)

    def run(self):
        install.run(self)
        post_install_hook()


# Provide a custom install command
print("[setup.py] Overload install command to enable execution of"
      " post install hook")
cmdclass = {"install": custom_install}

# Fix platform tag in wheel package
if "bdist_wheel" in sys.argv:
    print("[setup.py] Overload bdist_wheel command to fix platform tag")
    try:
        # setuptools v70.1+
        from setuptools.command.bdist_wheel import bdist_wheel
    except ImportError:
        from wheel.bdist_wheel import bdist_wheel

    def get_manylinux_glibc_version():
        """Return the highest GLIBC symbol version (major, minor)
        required by the binaries in the package directory."""
        package_dir = os.path.join(os.path.dirname(os.path.abspath(
                __file__)), "cefpython3")
        version = (2, 17)
        for root, _, files in os.walk(package_dir):
            for name in files:
                path = os.path.join(root, name)
                with open(path, "rb") as fp:
                    if fp.read(4) != b"\x7fELF":
                        continue
                    data = fp.read()
                for match in re.finditer(rb"GLIBC_(\d+)\.(\d+)", data):
                    version = max(version, (int(match.group(1)),
                                            int(match.group(2))))
        return version

    class custom_bdist_wheel(bdist_wheel):
        def get_tag(self):
            tag = bdist_wheel.get_tag(self)
            platform_tag = sysconfig.get_platform()
            platform_tag = platform_tag.replace("-", "_")
            if platform.system() == "Linux":
                assert "linux" in platform_tag
                # "linux_x86_64" replace with eg. "manylinux_2_34_x86_64"
                # depending on the glibc version used to build binaries.
                glibc = get_manylinux_glibc_version()
                platform_tag = platform_tag.replace(
                        "linux", "manylinux_{0}_{1}".format(*glibc))
            elif platform.system() == "Darwin":
                # For explanation of Mac platform tags, see:
                # http://lepture.com/en/2014/python-on-a-hard-wheel
                platform_tag = ("macosx_10_6_intel"
                                ".macosx_10_9_intel.macosx_10_9_x86_64"
                                ".macosx_10_10_intel.macosx_10_10_x86_64")
            tag = (tag[0], tag[1], platform_tag)
            return tag

    # Overwrite bdist_wheel command
    cmdclass["bdist_wheel"] = custom_bdist_wheel


def main():
    setup(
        distclass=Distribution,
        cmdclass=cmdclass,
        name="cefpython3",  # No spaces here, so that it works with deb pkg
        version="{{VERSION}}",
        description="GUI toolkit for embedding a Chromium widget"
                    " in desktop applications",
        long_description="CEF Python is an open source project founded"
                         " by Czarek Tomczak in 2012 to provide python"
                         " bindings for the Chromium Embedded Framework."
                         " Examples of embedding CEF browser are available"
                         " for many popular GUI toolkits including:"
                         " wxPython, PyQt, PySide, Kivy, Panda3D, PyGTK,"
                         " PyGObject, PyGame/PyOpenGL and PyWin32.\n\n"
                         "There are many use cases for CEF. You can embed"
                         " a web browser control based on Chromium with"
                         " great HTML 5 support. You can use it to create"
                         " a HTML 5 based GUI in an application, this can"
                         " act as a replacement for standard GUI toolkits"
                         " like wxWidgets, Qt or GTK. You can render web"
                         " content off-screen in application that use custom"
                         " drawing frameworks. You can use it for automated"
                         " testing of existing applications. You can use it"
                         " for web scraping or as a web crawler, or other"
                         " kind of internet bots.\n\n"
                         "Project website:\n"
                         "https://github.com/cztomczak/cefpython",
        license="BSD-3-Clause",
        author="Czarek Tomczak",
        author_email="czarek.tomczak@gmail.com",
        url="https://github.com/cztomczak/cefpython",
        download_url="https://github.com/cztomczak/cefpython/releases",
        platforms=["{{SYSCONFIG_PLATFORM}}"],
        python_requires=">=3.12",
        packages=["cefpython3"],
        package_data=get_package_data(),
        classifiers=[
            "Development Status :: 6 - Mature",
            "Intended Audience :: Developers",
            "Natural Language :: English",
            "Operating System :: MacOS :: MacOS X",
            "Operating System :: Microsoft :: Windows",
            "Operating System :: POSIX :: Linux",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3 :: Only",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
            "Programming Language :: Python :: 3.14",
            "Topic :: Desktop Environment",
            "Topic :: Internet",
            "Topic :: Internet :: WWW/HTTP",
            "Topic :: Internet :: WWW/HTTP :: Browsers",
            "Topic :: Multimedia",
            "Topic :: Software Development :: User Interfaces",
        ],
    )
    if "install" in sys.argv:
        print("[setup.py] OK installed")
    elif "bdist_wheel" in sys.argv:
        print("[setup.py] OK created wheel package in dist/ directory")
    else:
        print("[setup.py] Unknown command line arguments")


def get_package_data():
    package_data = {"cefpython3": get_package_files()}
    return package_data


def get_package_files(relative_dir=".", recursive=False):
    """Finds files recursively in the cefpython3/ local directory.
    Includes only files and their paths are relative to the cefpython3/
    local directory. Empty directories are not included."""
    old_dir = None
    if not recursive:
        old_dir = os.getcwd()
        setup_dir = os.path.abspath(os.path.dirname(__file__))
        local_pkg_dir = os.path.join(setup_dir, "cefpython3")
        os.chdir(local_pkg_dir)
    files = os.listdir(relative_dir)
    ret = list()
    for fpath in files:
        fpath = os.path.join(relative_dir, fpath)
        if os.path.isdir(fpath):
            ret.extend(get_package_files(relative_dir=fpath, recursive=True))
        else:
            ret.append(fpath)
    if not recursive:
        os.chdir(old_dir)
    return ret


def get_executables():
    data = copy.copy(EXECUTABLES_NOEXT)
    if platform.system() == "Windows":
        for key, executable in enumerate(data):
            data[key] += ".exe"
    return data


def post_install_hook():
    """Post install hook to chmod files on Linux and Mac."""

    # Nothing extra required to do on Windows
    if platform.system() == "Windows":
        print("[setup.py] post_install_hook is ignored on Windows")
        return

    # If this a wheel package generation then do not execute the hook
    if "bdist_wheel" in sys.argv:
        print("[setup.py] Ignoring post_install_hook as this is bdist_wheel")
        return

    print("[setup.py] Execute post_install_hook")

    # Find the installed package directory. Do not import from
    # the local cefpython3/ directory.
    print("[setup.py] Overload sys.path to facilitate finding correct"
          " directory for the installed package")
    del sys.path[0]
    sys.path.append("")
    import cefpython3
    installed_package_dir = os.path.dirname(cefpython3.__file__)

    # Make sure that the imported package wasn't the local cefptyhon3/
    # directory.
    print("[setup.py] Installed package directory: {dir}"
          .format(dir=installed_package_dir))
    assert not installed_package_dir.startswith(
            os.path.dirname(os.path.abspath(__file__)))

    # Set permissions on executables
    print("[setup.py] Set execute permissions on executables")
    for executable in get_executables():
        executable = os.path.join(installed_package_dir, executable)
        if not os.path.exists(executable):
            continue
        command = "chmod +x {executable}".format(executable=executable)
        print("[setup.py] {command}".format(command=command))
        subprocess.call(command, shell=True)

    # Set write permissions on log files
    print("[setup.py] Set write permissions on log files")
    package_data = get_package_data()
    for pkgfile in package_data:
        if not pkgfile.endswith(".log"):
            continue
        logfile = os.path.join(installed_package_dir, pkgfile)
        command = "chmod 666 {logfile}".format(logfile=logfile)
        print("[setup.py] {command}".format(command=command))
        subprocess.call(command, shell=True)


if __name__ == "__main__":
    main()

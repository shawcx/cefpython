# Copyright (c) 2026 CEF Python, see the Authors file.
# All rights reserved. Licensed under BSD 3-clause license.
# Project website: https://github.com/cztomczak/cefpython

"""
Create a Debian package (.deb) of the cefpython3 module for the
system Python 3. Linux only.

Usage:
    make_deb.py VERSION [--revision REV] [--maintainer MAINTAINER]

Options:
    VERSION                    Version number eg. 154.0
    --revision REV             Debian revision [default: 1]
    --maintainer MAINTAINER    Package maintainer, eg. "Name <email>".
                               Defaults to DEBFULLNAME/DEBEMAIL env
                               variables or git user.name/user.email.

Run build.py first, so that cefpython modules are built for each
Python version that should be included. The package installs to
/usr/lib/python3/dist-packages/cefpython3/ and examples to
/usr/share/doc/python3-cefpython3/examples/. The .deb file is
created in the build/ directory.
"""

from common import *

import datetime
import email.utils
import gzip
import hashlib
import shutil
import subprocess
import sys
import tempfile

import docopt

PACKAGE_NAME = "python3-cefpython3"
ARCH = {"64bit": "amd64", "32bit": "i386"}
INSTALL_DIR = "usr/lib/python3/dist-packages/cefpython3"
DOC_DIR = "usr/share/doc/" + PACKAGE_NAME
DESCRIPTION = """\
Python bindings for the Chromium Embedded Framework (CEF)
 CEF Python embeds a Chromium based web browser in Python applications.
 It can be used as an HTML5 based GUI, to embed a browser widget in
 Tkinter, GTK, Qt or wxPython applications, to render web content
 off-screen, for automated testing of web applications and for
 web scraping.
 .
 This package includes CEF binaries (libcef.so) and the cefpython
 module for each Python version it was built with."""

# Files from the setup installer package dir not shipped in the .deb
EXCLUDE_NAMES = set(CEF_SAMPLE_APPS) | {
    name + "_files" for name in CEF_SAMPLE_APPS} | {
    "examples", "debug.log", "__pycache__"}


def main():
    args = docopt.docopt(__doc__)
    if not LINUX:
        print("[make_deb.py] ERROR: Debian packages can be built on"
              " Linux only")
        sys.exit(1)
    version = args["VERSION"]
    revision = args["--revision"]
    maintainer = args["--maintainer"] or get_maintainer()
    deb_version = "{0}-{1}".format(version, revision)
    arch = ARCH[ARCH_STR]

    setup_dir = make_setup_installer(version)
    pkg_dir = os.path.join(setup_dir, "cefpython3")

    staging_dir = os.path.join(BUILD_DIR, "deb", "{0}_{1}_{2}".format(
            PACKAGE_NAME, deb_version, arch))
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)
    install_dir = os.path.join(staging_dir, INSTALL_DIR)
    doc_dir = os.path.join(staging_dir, DOC_DIR)

    print("[make_deb.py] Copy package files to {0}".format(INSTALL_DIR))
    shutil.copytree(pkg_dir, install_dir,
                    ignore=lambda _, names: [n for n in names
                                             if n in EXCLUDE_NAMES])
    print("[make_deb.py] Copy examples to {0}/examples".format(DOC_DIR))
    shutil.copytree(os.path.join(pkg_dir, "examples"),
                    os.path.join(doc_dir, "examples"),
                    ignore=shutil.ignore_patterns("debug.log",
                                                  "__pycache__"))
    shutil.copy(os.path.join(ROOT_DIR, "License"),
                os.path.join(doc_dir, "copyright"))
    write_changelog(doc_dir, deb_version, maintainer)
    strip_binaries(install_dir)
    fix_permissions(staging_dir)

    modules = sorted(f for f in os.listdir(install_dir)
                     if f.startswith("cefpython_py") and f.endswith(".so"))
    print("[make_deb.py] Python modules: {0}".format(", ".join(modules)))
    write_control_files(staging_dir, install_dir, deb_version, arch,
                        maintainer)

    deb_file = os.path.join(BUILD_DIR, os.path.basename(staging_dir)
                            + ".deb")
    print("[make_deb.py] Build {0}".format(os.path.basename(deb_file)))
    subprocess.check_call(["dpkg-deb", "--root-owner-group", "-Zxz",
                           "--build", staging_dir, deb_file])
    print("[make_deb.py] Done. Install it with:"
          " sudo apt install {0}".format(deb_file))


def get_maintainer():
    name = os.environ.get("DEBFULLNAME")
    mail = os.environ.get("DEBEMAIL")
    if not name or not mail:
        def git_config(key):
            try:
                return subprocess.check_output(
                        ["git", "config", key], cwd=ROOT_DIR).decode().strip()
            except (OSError, subprocess.CalledProcessError):
                return ""
        name = name or git_config("user.name")
        mail = mail or git_config("user.email")
    if not name or not mail:
        print("[make_deb.py] ERROR: Set --maintainer or DEBFULLNAME and"
              " DEBEMAIL env variables")
        sys.exit(1)
    return "{0} <{1}>".format(name, mail)


def make_setup_installer(version):
    """Run make_installer.py to collect CEF binaries, cefpython
    modules and examples into build/cefpython3_VERSION_linux64/."""
    print("[make_deb.py] Run make_installer.py")
    subprocess.check_call([sys.executable,
                           os.path.join(TOOLS_DIR, "make_installer.py"),
                           version])
    setup_dir = os.path.join(BUILD_DIR, get_setup_installer_basename(
            version, OS_POSTFIX2))
    assert os.path.isdir(setup_dir), setup_dir
    return setup_dir


def get_elf_files(directory):
    elf_files = []
    for root, _, files in os.walk(directory):
        for name in files:
            path = os.path.join(root, name)
            with open(path, "rb") as fp:
                if fp.read(4) == b"\x7fELF":
                    elf_files.append(path)
    return elf_files


def strip_binaries(install_dir):
    """Strip debug symbols like dh_strip does. libcef.so in CEF
    binary distributions is not stripped (1.4 GB)."""
    for path in get_elf_files(install_dir):
        size = os.path.getsize(path)
        subprocess.check_call(["strip", "--strip-unneeded", path])
        print("[make_deb.py] Strip {0}: {1} MB -> {2} MB".format(
                os.path.basename(path), size // 2**20,
                os.path.getsize(path) // 2**20))


def fix_permissions(staging_dir):
    """Directories and executables 0755, other files 0644. Shared
    libraries are 0644 as required by Debian policy."""
    os.chmod(staging_dir, 0o755)
    for root, dirs, files in os.walk(staging_dir):
        for name in dirs:
            os.chmod(os.path.join(root, name), 0o755)
        for name in files:
            path = os.path.join(root, name)
            mode = 0o644
            if not name.endswith(".so") and ".so." not in name:
                with open(path, "rb") as fp:
                    if fp.read(4) == b"\x7fELF":
                        mode = 0o755
            os.chmod(path, mode)


def write_changelog(doc_dir, deb_version, maintainer):
    date = email.utils.format_datetime(
            datetime.datetime.now(datetime.timezone.utc))
    contents = ("{package} ({version}) unstable; urgency=medium\n\n"
                "  * Package built with tools/make_deb.py.\n\n"
                " -- {maintainer}  {date}\n"
                .format(package=PACKAGE_NAME, version=deb_version,
                        maintainer=maintainer, date=date))
    changelog = os.path.join(doc_dir, "changelog.Debian.gz")
    with gzip.GzipFile(changelog, "wb", mtime=0) as fp:
        fp.write(contents.encode("utf-8"))
    os.chmod(changelog, 0o644)


def get_shlibs_depends(staging_dir, install_dir):
    """Run dpkg-shlibdeps on the ELF files to get dependencies on
    system libraries. Libraries bundled with CEF are skipped."""
    elf_files = get_elf_files(install_dir)
    # dpkg-shlibdeps requires a debian/control file in working dir
    work_dir = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(work_dir, "debian"))
        with open(os.path.join(work_dir, "debian", "control"), "w") as fp:
            fp.write("Source: {0}\n\nPackage: {0}\nArchitecture: any\n"
                     .format(PACKAGE_NAME))
        output = subprocess.check_output(
                ["dpkg-shlibdeps", "-O", "--ignore-missing-info",
                 "-l" + install_dir]
                + ["-e" + path for path in elf_files],
                cwd=work_dir, stderr=subprocess.DEVNULL).decode()
    finally:
        shutil.rmtree(work_dir)
    for line in output.splitlines():
        if line.startswith("shlibs:Depends="):
            depends = line[len("shlibs:Depends="):].strip()
            return ", ".join(fix_vendor_package(dep.strip())
                             for dep in depends.split(","))
    return ""


def fix_vendor_package(dependency):
    """dpkg-shlibdeps names the package that provides a library on
    the build machine. AMD's driver repository replaces eg. libgbm1
    with libgbm1-amdgpu, so depend on either of them."""
    name = dependency.split()[0]
    if name.endswith("-amdgpu"):
        base = name[:-len("-amdgpu")]
        return "{0} | {1}".format(base, name)
    return dependency


def write_control_files(staging_dir, install_dir, deb_version, arch,
                        maintainer):
    debian_dir = os.path.join(staging_dir, "DEBIAN")
    os.makedirs(debian_dir)

    depends = ["python3 (>= 3.12)"]
    shlibs = get_shlibs_depends(staging_dir, install_dir)
    if shlibs:
        depends.append(shlibs)

    installed_size = 0
    md5sums = []
    for root, _, files in os.walk(staging_dir):
        for name in files:
            path = os.path.join(root, name)
            if path.startswith(debian_dir):
                continue
            installed_size += os.path.getsize(path)
            with open(path, "rb") as fp:
                digest = hashlib.md5(fp.read()).hexdigest()
            md5sums.append("{0}  {1}".format(
                    digest, os.path.relpath(path, staging_dir)))

    control = ("Package: {package}\n"
               "Version: {version}\n"
               "Architecture: {arch}\n"
               "Maintainer: {maintainer}\n"
               "Installed-Size: {size}\n"
               "Depends: {depends}\n"
               "Section: python\n"
               "Priority: optional\n"
               "Homepage: https://github.com/cztomczak/cefpython\n"
               "Description: {description}\n"
               .format(package=PACKAGE_NAME, version=deb_version, arch=arch,
                       maintainer=maintainer,
                       size=(installed_size + 1023) // 1024,
                       depends=", ".join(depends), description=DESCRIPTION))
    write_file(os.path.join(debian_dir, "control"), control, 0o644)
    write_file(os.path.join(debian_dir, "md5sums"),
               "\n".join(sorted(md5sums, key=lambda l: l[34:])) + "\n", 0o644)

    # Byte-compiled files are created at runtime by Python and are
    # not tracked by dpkg, remove them so that directories are
    # removed cleanly.
    prerm = ("#!/bin/sh\n"
             "set -e\n"
             "rm -rf /{0}/__pycache__\n".format(INSTALL_DIR))
    write_file(os.path.join(debian_dir, "prerm"), prerm, 0o755)


def write_file(path, contents, mode):
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(contents)
    os.chmod(path, mode)


if __name__ == "__main__":
    main()

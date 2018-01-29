import os
import sys
import stat
from os.path import abspath
import fnmatch
import collections
import errno

try:
    import zlib
    del zlib
    _ZLIB_SUPPORTED = True
except ImportError:
    _ZLIB_SUPPORTED = False

try:
    import bz2
    del bz2
    _BZ2_SUPPORTED = True
except ImportError:
    _BZ2_SUPPORTED = False

try:
    from pwd import getpwnam
except ImportError:
    getpwnam = None

try:
    from grp import getgrnam
except ImportError:
    getgrnam = None


def _make_tarball(base_name, base_dir, compress="gzip", verbose=0, dry_run=0,
                  owner=None, group=None, logger=None):
    """Create a (possibly compressed) tar file from all the files under
    'base_dir'.

    'compress' must be "gzip" (the default), "bzip2", or None.

    'owner' and 'group' can be used to define an owner and a group for the
    archive that is being built. If not provided, the current owner and group
    will be used.

    The output tar file will be named 'base_name' +  ".tar", possibly plus
    the appropriate compression extension (".gz", or ".bz2").

    Returns the output filename.
    """
    if compress is None:
        tar_compression = ''
    elif _ZLIB_SUPPORTED and compress == 'gzip':
        tar_compression = 'gz'
    elif _BZ2_SUPPORTED and compress == 'bzip2':
        tar_compression = 'bz2'
    else:
        raise ValueError("bad value for 'compress', or compression format not "
                         "supported : {0}".format(compress))

    compress_ext = '.' + tar_compression if compress else ''
    archive_name = base_name + '.tar' + compress_ext
    archive_dir = os.path.dirname(archive_name)

    if archive_dir and not os.path.exists(archive_dir):
        if logger is not None:
            logger.info("creating %s", archive_dir)
        if not dry_run:
            os.makedirs(archive_dir)


    # creating the tarball
    import tarfile  # late import so Python build itself doesn't break

    if logger is not None:
        logger.info('Creating tar archive')

    uid = _get_uid(owner)
    gid = _get_gid(group)

    def _set_uid_gid(tarinfo):
        if gid is not None:
            tarinfo.gid = gid
            tarinfo.gname = group
        if uid is not None:
            tarinfo.uid = uid
            tarinfo.uname = owner
        return tarinfo

    if not dry_run:
        tar = tarfile.open(archive_name, 'w|%s' % tar_compression)
        try:
            tar.add(base_dir, filter=_set_uid_gid)
        finally:
            tar.close()

    return archive_name

def _call_external_zip(base_dir, zip_filename, verbose=False, dry_run=False):
    # XXX see if we want to keep an external call here
    if verbose:
        zipoptions = "-r"
    else:
        zipoptions = "-rq"
    from distutils.errors import DistutilsExecError
    from distutils.spawn import spawn
    try:
        spawn(["zip", zipoptions, zip_filename, base_dir], dry_run=dry_run)
    except DistutilsExecError:
        # XXX really should distinguish between "couldn't find
        # external 'zip' command" and "zip failed".
        raise ExecError, \
            ("unable to create zip file '%s': "
            "could neither import the 'zipfile' module nor "
            "find a standalone zip utility") % zip_filename

def _make_zipfile(base_name, base_dir, verbose=0, dry_run=0, logger=None):
    """Create a zip file from all the files under 'base_dir'.

    The output zip file will be named 'base_name' + ".zip".  Uses either the
    "zipfile" Python module (if available) or the InfoZIP "zip" utility
    (if installed and found on the default search path).  If neither tool is
    available, raises ExecError.  Returns the name of the output zip
    file.
    """
    zip_filename = base_name + ".zip"
    archive_dir = os.path.dirname(base_name)

    if archive_dir and not os.path.exists(archive_dir):
        if logger is not None:
            logger.info("creating %s", archive_dir)
        if not dry_run:
            os.makedirs(archive_dir)

    # If zipfile module is not available, try spawning an external 'zip'
    # command.
    try:
        import zlib
        import zipfile
    except ImportError:
        zipfile = None

    if zipfile is None:
        _call_external_zip(base_dir, zip_filename, verbose, dry_run)
    else:
        if logger is not None:
            logger.info("creating '%s' and adding '%s' to it",
                        zip_filename, base_dir)

        if not dry_run:
            with zipfile.ZipFile(zip_filename, "w",
                                 compression=zipfile.ZIP_DEFLATED,
                                 allowZip64=True) as zf:
                path = os.path.normpath(base_dir)
                if path != os.curdir:
                    zf.write(path, path)
                    if logger is not None:
                        logger.info("adding '%s'", path)
                for dirpath, dirnames, filenames in os.walk(base_dir):
                    for name in sorted(dirnames):
                        path = os.path.normpath(os.path.join(dirpath, name))
                        zf.write(path, path)
                        if logger is not None:
                            logger.info("adding '%s'", path)
                    for name in filenames:
                        path = os.path.normpath(os.path.join(dirpath, name))
                        if os.path.isfile(path):
                            zf.write(path, path)
                            if logger is not None:
                                logger.info("adding '%s'", path)

    return zip_filename


_ARCHIVE_FORMATS = {
    'tar':   (_make_tarball, [('compress', None)], "uncompressed tar file"),
    'zip':   (_make_zipfile, [], "ZIP file")
}

def make_archive(base_name, format, root_dir=None, base_dir=None, verbose=0,
                 dry_run=0, owner=None, group=None, logger=None):
    """Create an archive file (eg. zip or tar).

    'base_name' is the name of the file to create, minus any format-specific
    extension; 'format' is the archive format: one of "zip", "tar", "gztar",
    or "bztar".  Or any other registered format.

    'root_dir' is a directory that will be the root directory of the
    archive; ie. we typically chdir into 'root_dir' before creating the
    archive.  'base_dir' is the directory where we start archiving from;
    ie. 'base_dir' will be the common prefix of all files and
    directories in the archive.  'root_dir' and 'base_dir' both default
    to the current directory.  Returns the name of the archive file.

    'owner' and 'group' are used when creating a tar archive. By default,
    uses the current owner and group.
    """
    save_cwd = os.getcwd()
    if root_dir is not None:
        if logger is not None:
            logger.debug("changing into '%s'", root_dir)
        base_name = os.path.abspath(base_name)
        if not dry_run:
            os.chdir(root_dir)

    if base_dir is None:
        base_dir = os.curdir

    kwargs = {'dry_run': dry_run, 'logger': logger}

    try:
        format_info = _ARCHIVE_FORMATS[format]
    except KeyError:
        raise ValueError, "unknown archive format '%s'" % format

    func = format_info[0]
    for arg, val in format_info[1]:
        kwargs[arg] = val

    if format != 'zip':
        kwargs['owner'] = owner
        kwargs['group'] = group

    try:
        filename = func(base_name, base_dir, **kwargs)
    finally:
        if root_dir is not None:
            if logger is not None:
                logger.debug("changing back to '%s'", save_cwd)
            os.chdir(save_cwd)

    return filename
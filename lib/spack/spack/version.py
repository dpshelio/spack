import os
import re

import utils
import spack.error as serr


class VersionParseError(serr.SpackError):
    """Raised when the version module can't parse something."""
    def __init__(self, msg, spec):
        super(VersionParseError, self).__init__(msg)
        self.spec = spec


class UndetectableVersionError(VersionParseError):
    """Raised when we can't parse a version from a string."""
    def __init__(self, spec):
        super(UndetectableVersionError, self).__init__(
            "Couldn't detect version in: " + spec, spec)


class UndetectableNameError(VersionParseError):
    """Raised when we can't parse a package name from a string."""
    def __init__(self, spec):
        super(UndetectableNameError, self).__init__(
            "Couldn't parse package name in: " + spec)


class Version(object):
    """Class to represent versions"""
    def __init__(self, version_string):
        self.version_string = version_string
        self.version = canonical(version_string)

    def __cmp__(self, other):
        return cmp(self.version, other.version)

    @property
    def major(self):
        return self.component(0)

    @property
    def minor(self):
        return self.component(1)

    @property
    def patch(self):
        return self.component(2)

    def component(self, i):
        """Returns the ith version component"""
        if len(self.version) > i:
            return self.version[i]
        else:
            return None

    def up_to(self, index):
        """Return a version string up to the specified component, exclusive.
           e.g., if this is 10.8.2, self.up_to(2) will return '10.8'.
        """
        return '.'.join(str(x) for x in self[:index])

    def __getitem__(self, idx):
        return tuple(self.version[idx])

    def __repr__(self):
        return self.version_string

    def __str__(self):
        return self.version_string


def canonical(v):
    """Get a "canonical" version of a version string, as a tuple."""
    def intify(part):
        try:
            return int(part)
        except:
            return part

    return tuple(intify(v) for v in re.split(r'[_.-]+', v))


def parse_version_string_with_indices(spec):
    """Try to extract a version string from a filename or URL.  This is taken
       largely from Homebrew's Version class."""

    if os.path.isdir(spec):
        stem = os.path.basename(spec)
    elif re.search(r'((?:sourceforge.net|sf.net)/.*)/download$', spec):
        stem = utils.stem(os.path.dirname(spec))
    else:
        stem = utils.stem(spec)

    version_types = [
        # GitHub tarballs, e.g. v1.2.3
        (r'github.com/.+/(?:zip|tar)ball/v?((\d+\.)+\d+)$', spec),

        # e.g. https://github.com/sam-github/libnet/tarball/libnet-1.1.4
        (r'github.com/.+/(?:zip|tar)ball/.*-((\d+\.)+\d+)$', spec),

        # e.g. https://github.com/isaacs/npm/tarball/v0.2.5-1
        (r'github.com/.+/(?:zip|tar)ball/v?((\d+\.)+\d+-(\d+))$', spec),

        # e.g. https://github.com/petdance/ack/tarball/1.93_02
        (r'github.com/.+/(?:zip|tar)ball/v?((\d+\.)+\d+_(\d+))$', spec),

        # e.g. https://github.com/erlang/otp/tarball/OTP_R15B01 (erlang style)
        (r'[-_](R\d+[AB]\d*(-\d+)?)', spec),

        # e.g. boost_1_39_0
        (r'((\d+_)+\d+)$', stem),

        # e.g. foobar-4.5.1-1
        # e.g. ruby-1.9.1-p243
        (r'-((\d+\.)*\d\.\d+-(p|rc|RC)?\d+)(?:[-._](?:bin|dist|stable|src|sources))?$', stem),

        # e.g. lame-398-1
        (r'-((\d)+-\d)', stem),

        # e.g. foobar-4.5.1
        (r'-((\d+\.)*\d+)$', stem),

        # e.g. foobar-4.5.1b
        (r'-((\d+\.)*\d+([a-z]|rc|RC)\d*)$', stem),

        # e.g. foobar-4.5.0-beta1, or foobar-4.50-beta
        (r'-((\d+\.)*\d+-beta(\d+)?)$', stem),

        # e.g. foobar4.5.1
        (r'((\d+\.)*\d+)$', stem),

        # e.g. foobar-4.5.0-bin
        (r'-((\d+\.)+\d+[a-z]?)[-._](bin|dist|stable|src|sources?)$', stem),

        # e.g. dash_0.5.5.1.orig.tar.gz (Debian style)
        (r'_((\d+\.)+\d+[a-z]?)[.]orig$', stem),

        # e.g. http://www.openssl.org/source/openssl-0.9.8s.tar.gz
        (r'-([^-]+)', stem),

        # e.g. astyle_1.23_macosx.tar.gz
        (r'_([^_]+)', stem),

        # e.g. http://mirrors.jenkins-ci.org/war/1.486/jenkins.war
        (r'\/(\d\.\d+)\/', spec),

        # e.g. http://www.ijg.org/files/jpegsrc.v8d.tar.gz
        (r'\.v(\d+[a-z]?)', stem)]

    for vtype in version_types:
        regex, match_string = vtype[:2]
        match = re.search(regex, match_string)
        if match and match.group(1) is not None:
            return match.group(1), match.start(1), match.end(1)

    raise UndetectableVersionError(spec)


def parse_version(spec):
    """Given a URL or archive name, extract a versino from it and return
       a version object.
    """
    ver, start, end = parse_version_string_with_indices(spec)
    return Version(ver)


def create_version_format(spec):
    """Given a URL or archive name, find the version and create a format string
       that will allow another version to be substituted.
    """
    ver, start, end = parse_version_string_with_indices(spec)
    return spec[:start] + '%s' + spec[end:]


def replace_version(spec, new_version):
    version = create_version_format(spec)


def parse_name(spec, ver=None):
    if ver is None:
        ver = parse_version(spec)

    ntypes = (r'/sourceforge/([^/]+)/',
              r'/([^/]+)/(tarball|zipball)/',
              r'/([^/]+)[_.-](bin|dist|stable|src|sources)[_.-]%s' % ver,
              r'/([^/]+)[_.-]v?%s' % ver,
              r'/([^/]+)%s' % ver,
              r'^([^/]+)[_.-]v?%s' % ver,
              r'^([^/]+)%s' % ver)

    for nt in ntypes:
        match = re.search(nt, spec)
        if match:
            return match.group(1)
    raise UndetectableNameError(spec)

def parse(spec):
    ver = parse_version(spec)
    name = parse_name(spec, ver)
    return (name, ver)

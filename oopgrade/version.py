import semver


class Version(object):
    """Version class using semantic version parsing

    :param version: version string
    """

    def __init__(self, version):
        self.version = version

    @property
    def info(self):
        """Get the information parsing the version.

        :returns: a dict with the keys: major, minor, patch, prerelease and build
        """
        return semver.parse(self.version)

    def bump_major(self):
        """Bump a major version: X from X.Y.Z
        """
        self.version = semver.bump_major(self.version)

    def bump_minor(self):
        """Bump a minor version: Y from X.Y.Z
        """
        self.version = semver.bump_minor(self.version)

    def bump_patch(self):
        """Bump a patch version: Z from X.Y.Z
        """
        self.version = semver.bump_patch(self.version)

    def __gt__(self, other):
        if isinstance(other, basestring):
            other = Version(other)
        return semver.match(self.version, '>{}'.format(other.version))

    def __ge__(self, other):
        if isinstance(other, basestring):
            other = Version(other)
        return semver.match(self.version, '>={}'.format(other.version))

    def __lt__(self, other):
        if isinstance(other, basestring):
            other = Version(other)
        return semver.match(self.version, '<{}'.format(other.version))

    def __le__(self, other):
        if isinstance(other, basestring):
            other = Version(other)
        return semver.match(self.version, '<={}'.format(other.version))

    def __eq__(self, other):
        if isinstance(other, basestring):
            other = Version(other)
        return semver.match(self.version, '=={}'.format(other.version))

    def __unicode__(self):
        return u'v{}'.format(self.version)

    def __str__(self):
        return 'v{}'.format(self.version)

    def __repr__(self):
        return 'v{}'.format(self.version)

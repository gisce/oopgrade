from oopgrade.version import Version
from expects import *

with description("a Versions class"):
    with context("When comparing"):
        with it("must to known if it's greater from other version"):
            v1 = Version('4.2.4')
            v2 = Version('3.2.1')
            expect(v1).to(be_above(v2))

        with it("must to know if it's greater or equal from other version"):
            v1 = Version('4.2.4')
            v2 = Version('4.2.4')
            expect(v1).to(be_above_or_equal(v2))

        with it("must to know if it's lower than from other version"):
            v1 = Version('4.2.4')
            v2 = Version('3.2.1')
            expect(v2).to(be_below(v1))

        with it("must to know if it's lower or equal than from other version"):
            v1 = Version('4.2.4')
            v2 = Version('4.2.4')
            expect(v2).to(be_below_or_equal(v1))

        with it("must to know if it's equal to other version"):
            v1 = Version('4.2.4')
            v2 = Version('4.2.4')
            expect(v1).to(equal(v2))

    with it('must to bump a major version'):
        v1 = Version('0.1.1')
        v1.bump_major()
        expect(v1).to(equal(Version('1.0.0')))

    with it('must to bump a minor version'):
        v1 = Version('0.1.1')
        v1.bump_minor()
        expect(v1).to(equal(Version('0.2.0')))

    with it('must to bump a patch version'):
        v1 = Version('0.1.1')
        v1.bump_patch()
        expect(v1).to(equal(Version('0.1.2')))

    with it('must to parse and return info as dict'):
        v1 = Version('1.2.3-beta.1+build.4')
        expect(v1.info).to(have_keys(
            major=1,
            minor=2,
            patch=3,
            prerelease='beta.1',
            build='build.4'
        ))

    with it('must be sorted in a list of versions'):
        versions = [Version('2.1.1'), Version('1.0.3'), Version('3.2.4')]
        sorted_version = sorted(versions)
        expect(sorted_version).to(contain_exactly(
            Version('1.0.3'), Version('2.1.1'), Version('3.2.4')
        ))

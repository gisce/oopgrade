# coding=utf-8
from expects import expect, equal, contain
from mamba import description, context, it

from oopgrade.utils import clean_requirements_lines

with description('clean_requirements_lines') as self:
    with context('amb duplicats i markers'):
        with it('manté només els requeriments més restrictius i conserva els markers'):
            input_lines = [
                "rq==1.12;python_version>\"2.7.18\"",
                "rq==1.16.2;python_version>\"2.7.18\"",
                "rq==1.3.0;python_version<=\"2.7.18\"",
                "python-slugify<=5.0.0",
                "python-slugify>=2.0.0,<=5.0.0",
                "pymongo==3.13.0;python_version<=\"2.7.18\"",
                "pymongo<=3.13.0",
                "redis<3.6;python_version<=\"2.7.18\"",
                "redis>=5.1.1;python_version>\"2.7.18\""
            ]

            result = clean_requirements_lines(input_lines)

            expect(result).to(contain(
                'rq==1.16.2 ; python_version>"2.7.18"',
                'rq==1.3.0 ; python_version<="2.7.18"',
                'python-slugify>=2.0.0,<=5.0.0',
                'pymongo==3.13.0 ; python_version<="2.7.18"',
                'pymongo<=3.13.0',
                'redis>=5.1.1 ; python_version>"2.7.18"',
                'redis<3.6 ; python_version<="2.7.18"'
            ))

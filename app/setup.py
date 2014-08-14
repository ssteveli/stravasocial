from setuptools import setup

setup(
    name='stravasocial',
    version='1.0',
    packages=['api','loader','stravadao', 'util'],
    url='',
    license='',
    author='ssteveli',
    author_email='scott@stevelinck.com',
    description='',
    install_requires=[
        'pyconfig',
        'beaker',
        'stravalib',
        'flask',
        'gearman',
        'pymongo'
    ]
)

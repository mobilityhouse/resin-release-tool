from setuptools import setup, find_packages

setup(
    name='resin-release-tool',
    setup_requires=['setuptools>=17.1'],
    packages=find_packages(),
    entry_points={
        'console_scripts': ['resin-release-tool=resin_release_tool.cli:main']
    },
    include_package_data=True,
    install_requires=['resin-sdk==5.0', 'click==6.7'],
    version='0.1.0'
)

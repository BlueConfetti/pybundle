from setuptools import setup, find_packages

setup(
    name='pybundle',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'tiktoken',
    ],
    entry_points={
        'console_scripts': [
            'pybundle=bundler.bundler:main',
        ],
    },
    author='BlueConfetti',
    description='A Python utility to isolate function dependencies within projects.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/BlueConfetti/pybundle',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)

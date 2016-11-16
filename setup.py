from setuptools import setup

setup(
    name='restless-haystack',
    version=open('VERSION', 'r').read(),
    packages=['restless_haystack'],
    install_requires=['Django', 'django-haystack', 'restless'],
    url='https://github.com/CraveFood/restless-haystack',
    license='MIT',
    author='Bruno Marques',
    author_email='bruno@bmarques.net',
    description='Integration of the Restless and Haystack libraries for Django',
    long_description=open('README.md', 'r').read(),
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
)

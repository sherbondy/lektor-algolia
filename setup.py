from setuptools import setup

setup(
    name='lektor-algolia',
    description='Lektor plugin to support generating an Algolia search index from your data',
    version='0.0.4',
    author=u'Ethan Sherbondy',
    author_email='sherbondye@gmail.com',
    url='https://github.com/sherbondy/lektor-algolia',
    license='MIT',
    py_modules=['lektor_algolia'],
    entry_points={
        'lektor.plugins': [
            'algolia = lektor_algolia:AlgoliaPlugin',
        ]
    },
    install_requires=[
        'Lektor',
        'algoliasearch>=1.7.1',
    ]
)

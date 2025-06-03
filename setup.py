from setuptools import setup

setup(
    name="pyecotaxa",
    version="0.1.0",
    description="Python client for EcoTaxa",
    author="EcoTaxa Team",
    author_email="ecotaxa@obs-vlfr.fr",
    url="https://github.com/ecotaxa/pyecotaxa",
    package_dir={"": "src"},
    packages=["pyecotaxa"],
    install_requires=[
        "pandas",
        "requests",
        "requests-toolbelt",
        "semantic-version",
        "tqdm",
        "urllib3",
        "werkzeug",
        "atomicwrites",
    ],
    python_requires=">=3.9",
)

import setuptools
from pathlib import Path

NAME = "aeroguard"
VERSION = "0.1.0"
DESCRIPTION = (
    "Aeroguard: unsupervised anomaly detection for aviation flight telemetry, "
    "built on top of scikit-learn."
)
README = Path(__file__).parent / "README.md"

setuptools.setup(
    name=NAME,
    version=VERSION,
    author="Ankit",
    description=DESCRIPTION,
    long_description=README.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/x2ankit/Aeroguard",
    license="MIT",
    packages=setuptools.find_packages(),
    install_requires=[
        "numpy>=2.1,<2.2",
        "pandas>=2.2,<2.3",
        "pyarrow>=17,<19",
        "scikit-learn>=1.5,<1.6",
        "matplotlib>=3.9,<3.11",
        "tqdm",
        "streamlit>=1.35,<2",
        "plotly>=5.22,<6",
    ],
    keywords=["anomaly detection", "aviation", "flight data", "unsupervised learning"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Intended Audience :: Science/Research",
    ],
    python_requires=">=3.10",
    include_package_data=True,
)
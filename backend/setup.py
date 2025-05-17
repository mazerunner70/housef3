from setuptools import setup, find_packages

setup(
    name="housef3-backend",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[],  # Keep this empty since boto3 is provided by Lambda
    extras_require={
        "local": [
            "boto3>=1.26.0",
            "botocore>=1.29.0",
        ],
        "dev": [
            "mypy>=1.0.0",
            "types-boto3>=1.0.0",
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.0.0",
            "flake8>=6.0.0"
        ]
    }
) 
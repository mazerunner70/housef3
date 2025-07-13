from setuptools import setup, find_packages

setup(
    name="housef3-scripts",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "boto3>=1.26.0",
        "pydantic>=2.0.0",
        "python-dateutil>=2.8.2",
    ],
    python_requires=">=3.8",
) 
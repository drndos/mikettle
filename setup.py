"""Python package description."""
from setuptools import setup, find_packages

setup(
    name='mikettle',
    version='0.0.1',
    description='This library properly authenticates with Xiaomi Mi Kettle and allows to read status and control the kettle via Bluetooth.',
    url='https://github.com/drndos/mikettle',
    author='drndos',
    author_email='drndos@drndos.sk',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
    packages=find_packages(),
    install_requires=['bluepy==1.3.0'],
    keywords='temperature kettle smart home sensor bluetooth low-energy ble',
    zip_safe=False,
    extras_require={'testing': ['pytest']}
)

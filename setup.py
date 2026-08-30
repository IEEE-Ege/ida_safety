from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'ida_safety'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'),
         glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='IEEE Ege Mavi İnci Yazılım Ekibi',
    maintainer_email='ieeegesb@gmail.com',
    description='FDIR: düğüm canlılık + batarya izleme, /system/health ve safe_mode.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'fdir_node = ida_safety.fdir_node:main',
        ],
    },
)

from setuptools import setup

setup(
    name='lp-api-kernel',
    version='1.0.1',
    author='Infrabel Linux Team',
    author_email='linux@infrabel.be',
    packages=[
        'lp_api_kernel',
        'lp_api_kernel.cache',
        'lp_api_kernel.external',
        'lp_api_kernel.internal'
    ],
    install_requires=[
        'requests',
        'flask',
        'urllib3',
        'redis'
    ],
    url='https://git.msnet.railb.be/linux-infrastructure/lp-api-kernel',
    license='Apache',
    description='Basic API\'s for the Linux Portal.'
)

AZURE_ENABLED = True
AWS_ENABLED = False
AWS_REGION = 'eu-west-1'

LOGGER = 'log'

# Windows VM credentials
ADMIN_USERNAME = 'my-admin'
ADMIN_PASSWORD = 'fjewiur7612!!cHHgaAAAcx'  # CHANGE THIS!

# vm name prefix. This is part of the default VM name: <prefix-vm-date> e.g. `ab-vm-163835`
VM_NAME_PREFIX = 'cm'

MAIN_WINDOW_NAME = 'Cloud Manager'
MAIN_WINDOW_SIZE = {'width': 900, 'height': 600}

WINDOW_NAME = 'Azure'
WINDOW_SIZE = {'width': 884, 'height': 561}

VM_SIZES = {
    'small': 'Standard_B1s',
    'medium': 'Standard_B2s',
    'large': 'Standard_B4ms'
}

IMAGES = {
    'win2019datacenter': {'label': 'Windows 2019', 'os': 'Windows'},
    'UbuntuLTS': {'label': 'Ubuntu 18.04', 'os': 'Linux'},
    'CentOS': {'label': 'CentOS 7.5', 'os': 'Linux'}
}

# Azure config

# Windows VM credentials
ADMIN_USERNAME = 'cloud-admin'
ADMIN_PASSWORD = 'soMeCompLexPassrd9!'

SUBSCRIPTIONS = ['your-main-sub', 'optional-sub']  # CHANGE THIS!
RESOURCE_GROUP = 'your-vm-resource-group-name'    # CHANGE THIS!
###

# NOTE: If you are using multiple subscriptions these names must be found from all subscriptions!
NETWORK = 'your-network-name'  # CHANGE THIS!
SUBNET = 'your-subnet-name'   # CHANGE THIS!
NETWORK_RESOURCE_GROUP = 'your-network-resource-group-name'  # CHANGE THIS!
###

# vm name prefix. This is part of the default VM name: <prefix-vm-date> e.g. `ab-vm-163835`
VM_NAME_PREFIX = 'ab'

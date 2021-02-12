from datetime import datetime
from itertools import chain
from json import loads
from os import system
import subprocess

from dearpygui import core, simple

from config import *

MAIN_WINDOW_NAME = 'Cloud Manager'
MAIN_WINDOW_SIZE = {'width': 450, 'height': 300}

WINDOW_NAME = 'Azure'
WINDOW_SIZE = {'width': 434, 'height': 261}

LOGGER = 'log'

core.set_main_window_title(MAIN_WINDOW_NAME)
core.set_main_window_size(**MAIN_WINDOW_SIZE)
core.set_main_window_resizable(False)


def get_data():
    return {
        'vm_name': core.get_value('vm_name'),
        'subscription': get_current_subscription(),
        'resource_group': core.get_value('resource_group'),
        'network': core.get_value('network'),
        'subnet': core.get_value('subnet'),
        'data_disks': core.get_value('data_disks')
    }


def get_data_vm():
    return {
        'vm_name': core.get_value('vm_combo'),
        'subscription': get_current_subscription_vms(),
        'resource_group': core.get_value('resource_group_vms'),
    }


def generate_vm_name():
    t = datetime.now()
    return f'{VM_NAME_PREFIX}-vm-{t.hour}{t.minute}{t.second}'


def generate_vm_tag(vm_name):
    return f'vm={vm_name}'


def print_resources(resources):
    print(f'Deleting resources:')
    for resource in resources:
        print(resource)


def run_cmd(cmd, as_json=True):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process.wait()
    output, err = process.communicate()

    if process.returncode != 0:
        print(f'ERROR while running command: {err}')
        return

    # Deserialize json str to a Python object
    if not as_json:
        return [line.decode().strip() for line in output.splitlines() if line.decode().strip()]

    return loads(output)


def get_net_sub(subnet_id):
    ar = subnet_id.split('/')
    subnet = ar[-1]
    network = ar[-3]
    return network, subnet

# ------- Azure -------


def create_az_vm(vm_name, subscription, resource_group, network, subnet, data_disks=0):
    core.log_info(logger=LOGGER, message=f'Creating VM {vm_name}...')

    image = 'win2019datacenter'
    tag = generate_vm_tag(vm_name)
    subnet_id = get_az_subnet_id(subscription, network, subnet)

    if not subnet_id:
        core.log_error(
            logger=LOGGER, message=f'ERROR Subnet {subnet} not found from vnet {network}')
        return

    az_command = f'az vm create -n {vm_name} -g {resource_group} --image {image} --admin-username {ADMIN_USERNAME} --admin-password {ADMIN_PASSWORD} --subscription {subscription} --public-ip-address "" --nsg "" --tags {tag} --subnet {subnet_id}'

    if data_disks:
        data_disk_sizes = ['1' for i in range(data_disks)]
        disks_param = f' --data-disk-sizes-gb {" ".join(data_disk_sizes)}'
        az_command += disks_param

    cmd = system(az_command)
    if cmd != 0:
        core.log_error(logger=LOGGER, message=f'VM {vm_name} Creation ERROR')
        return

    core.log(logger=LOGGER, message=f'VM {vm_name} successfully created!')


def delete_az_vm(vm_name, subscription, resource_group):

    core.log_info(logger=LOGGER, message=f'Deleting VM {vm_name}...')

    resource_ids = get_az_resource_ids(vm_name, subscription, resource_group)
    resource_ids_str = ' '.join(resource_ids)

    az_command = f'az resource delete --ids {resource_ids_str} --subscription {subscription}'

    print_resources(resource_ids)
    cmd = system(az_command)
    if cmd != 0:
        core.log_error(logger=LOGGER, message=f'VM {vm_name} Delete ERROR')
        return

    core.log(logger=LOGGER, message=f'VM {vm_name} successfully deleted!')


def get_az_subnet_ids(subscription):
    cmd = f'az network vnet list --query "[].subnets[].id" --subscription {subscription}'
    return run_cmd(cmd)


def get_az_resource_ids(vm_name, subscription, resource_group):
    cmd = f'az vm show -g {resource_group} -n {vm_name} --query "[id, networkProfile.networkInterfaces[].id, storageProfile.osDisk.managedDisk.id, storageProfile.dataDisks[].managedDisk.id]" --subscription {subscription} -o tsv'
    return run_cmd(cmd, as_json=False)


def get_az_vms():
    subscription = get_current_subscription_vms()
    cmd = f'az vm list -d --query "[].{{name: name, state: powerState, rg: resourceGroup, size: hardwareProfile.vmSize, publicIps: publicIps, os: storageProfile.imageReference.offer}}" --subscription {subscription}'
    return run_cmd(cmd)


def get_az_vms_from_rg():
    subscription = get_current_subscription_vms()
    resource_group = core.get_value('resource_group_vms')
    if not resource_group:
        return []
    cmd = f'az vm list -g {resource_group} --query "[].name" --subscription {subscription}'
    return run_cmd(cmd)


def get_az_resource_group(subscription):
    cmd = f'az group list --query "[].name" --subscription {subscription}'
    return run_cmd(cmd)


# ------- DATA -------

def get_net_data():
    print('Initializing Azure network data...')
    net_data = {}
    for sub in SUBSCRIPTIONS:
        net_data[sub] = {}
        subnet_ids = get_az_subnet_ids(sub)
        print('Done for subscription', sub)
        for subnet_id in subnet_ids:
            network, subnet = get_net_sub(subnet_id)
            if network not in net_data[sub]:
                net_data[sub][network] = {}
            net_data[sub][network][subnet] = subnet_id

    return net_data


def get_rg_data():
    print('Initializing Azure resource group data...')
    return {sub: get_az_resource_group(sub) for sub in SUBSCRIPTIONS}


def get_net_data_network(subscription):
    net_data = list(core.get_data('net_data')[subscription].keys())
    return net_data


def get_net_data_subnet(subscription, network):
    return list(core.get_data('net_data')[subscription][network].keys())


def get_rgs(subscription):
    return core.get_data('rg_data')[subscription]


def get_az_subnet_id(subscription, network, subnet):
    return core.get_data('net_data')[subscription][network][subnet]

# ------- UI -------


def refresh(sender, data):
    set_state(False)

    rgs = get_rgs(get_current_subscription_vms())

    core.configure_item('resource_group_vms', items=rgs)
    if sender == 'subscription_vms' or not core.get_value('resource_group_vms'):
        core.set_value('resource_group_vms', rgs[0])

    vms = get_az_vms_from_rg()
    core.configure_item('vm_combo', items=vms)
    vm_val = vms[0] if vms else ''
    core.set_value('vm_combo', vm_val)

    set_state(True)


def refresh_rg(sender, data):
    set_state(False)
    subscription = get_current_subscription()

    rgs = get_rgs(subscription)
    core.configure_item('resource_group', items=rgs)
    core.set_value('resource_group', rgs[0])

    # network
    networks = get_net_data_network(subscription)

    subnets = get_net_data_subnet(subscription, networks[0])
    core.configure_item('network', items=networks)
    core.set_value('network', networks[0])

    core.configure_item('subnet', items=subnets)
    core.set_value('subnet', subnets[0])

    set_state(True)


def create_vm_submit(sender, data):
    set_state(False)
    create_az_vm(**data)
    refresh()
    core.set_value('vm_name', generate_vm_name())


def delete_vm_submit(sender, data):
    set_state(False)
    delete_az_vm(**data)
    refresh()


def enable_submit(sender, data):
    val = core.get_value(sender)
    if not val:
        core.configure_item('Submit', enabled=False)
    else:
        core.configure_item('Submit', enabled=True)


def enable_delete(sender, data):
    val = core.get_value(sender)
    if not val:
        core.configure_item('Delete', enabled=False)
    else:
        core.configure_item('Delete', enabled=True)


def set_state(state=True):
    # Provision tab
    core.configure_item('subscription', enabled=state)
    core.configure_item('resource_group', enabled=state)
    core.configure_item('network', enabled=state)
    core.configure_item('subnet', enabled=state)
    core.configure_item('vm_name', enabled=state)
    core.configure_item('data_disks', enabled=state)
    core.configure_item('Submit', enabled=state)

    # VM tab
    core.configure_item('subscription_vms', enabled=state)
    core.configure_item('resource_group_vms', enabled=state)
    core.configure_item('vm_combo', enabled=state)
    if state == False:
        core.configure_item('Delete', enabled=state)


def refresh_subnet(sender, data):
    network = core.get_value(sender)
    subscription = get_current_subscription()
    subnets = get_net_data_subnet(subscription, network)

    core.configure_item('subnet', items=subnets)
    core.set_value('subnet', subnets[0])


def get_current_subscription():
    return SUBSCRIPTIONS[core.get_value('subscription')]


def get_current_subscription_vms():
    return SUBSCRIPTIONS[core.get_value('subscription_vms')]


# ------- Main -------

def colorize_button(name, color='red'):
    colors = {
        'red': [255, 0, 0, 255],
        'green': [0, 255, 0, 150],
        'blue': [0, 0, 255, 255],
    }
    core.set_item_color(name, core.mvGuiCol_Button, color=colors[color])


def create_tab():
    with simple.tab('create_tab', label='Create VM'):

        core.add_radio_button(
            'subscription',
            items=SUBSCRIPTIONS,
            callback=refresh_rg
        )

        core.add_combo(
            'resource_group',
            items=get_rgs(get_current_subscription()),
            label='Resource Group'
        )

        core.add_combo(
            'network',
            label='Network',
            callback=refresh_subnet,
            items=get_net_data_network(get_current_subscription())
        )

        core.add_combo(
            'subnet',
            label='Subnet'
        )

        core.add_input_text(
            'vm_name',
            label='VM Name',
            callback=enable_submit,
            no_spaces=True,
            default_value=generate_vm_name()
        )

        core.add_slider_int(
            'data_disks',
            max_value=3,
            label='Data Disks'
        )

        core.add_button(
            'Submit',
            callback=create_vm_submit,
            callback_data=get_data,
            enabled=True
        )
        colorize_button('Submit', 'green')


def vms_tab():
    with simple.tab('vms_tab', label='VMs'):

        core.add_radio_button(
            'subscription_vms',
            items=SUBSCRIPTIONS,
            callback=refresh
        )

        core.add_combo(
            'resource_group_vms',
            items=get_rgs(get_current_subscription_vms()),
            label='Resource Group',
            callback=refresh
        )

        core.add_combo(
            name='vm_combo',
            label='VM',
            callback=enable_delete
        )

        core.add_button(
            name='Delete',
            callback=delete_vm_submit,
            callback_data=get_data_vm,
            enabled=False
        )
        colorize_button('Delete', 'red')


def log_tab():
    with simple.tab('log_tab', label='Log'):
        core.add_logger(
            LOGGER,
            autosize_x=True,
            autosize_y=True,
            filter=False,
            clear_button=False,
            copy_button=False,
            auto_scroll=True,
            auto_scroll_button=False,
            log_level=0
        )


def main():
    with simple.window(WINDOW_NAME, **WINDOW_SIZE, no_move=True, no_close=True, no_collapse=False, x_pos=0, y_pos=0, no_resize=True):
        core.add_data('rg_data', data=get_rg_data())
        core.add_data('net_data', data=get_net_data())

        with simple.tab_bar('tab_bar'):
            create_tab()
            vms_tab()
            log_tab()

    core.start_dearpygui()


if __name__ == '__main__':
    main()

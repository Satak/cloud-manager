from datetime import datetime
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
        'subscription': SUBSCRIPTIONS[core.get_value('subscription')],
        'data_disks': core.get_value('data_disks')
    }


def get_data_delete():
    return {
        'vm_name': core.get_value('vm_combo'),
        'subscription': SUBSCRIPTIONS[core.get_value('subscription_vms')],
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


def run_win_cmd(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return [line.decode().strip() for line in process.stdout if line.decode().strip()]

# ------- Azure -------


def create_vm(vm_name, subscription, data_disks=0):
    core.log_info(logger=LOGGER, message=f'Creating VM {vm_name}...')

    image = 'win2019datacenter'
    tag = generate_vm_tag(vm_name)
    subnet_id = get_az_subnet_id(subscription)
    print(f'subnet id: {subnet_id}')
    if not subnet_id:
        return

    az_command = f'az vm create -n {vm_name} -g {RESOURCE_GROUP} --image {image} --admin-username {ADMIN_USERNAME} --admin-password {ADMIN_PASSWORD} --subscription {subscription} --public-ip-address "" --nsg "" --tags {tag} --subnet {subnet_id}'

    if data_disks:
        data_disk_sizes = ['1' for i in range(data_disks)]
        disks_param = f' --data-disk-sizes-gb {" ".join(data_disk_sizes)}'
        az_command += disks_param

    cmd = system(az_command)
    if cmd != 0:
        core.log_error(logger=LOGGER, message=f'VM {vm_name} Creation ERROR')
        return

    core.log(logger=LOGGER, message=f'VM {vm_name} successfully created!')


def delete_vm(vm_name, subscription):

    core.log_info(logger=LOGGER, message=f'Deleting VM {vm_name}...')

    resource_ids = get_az_resource_ids(vm_name, subscription)
    resource_ids_str = ' '.join(resource_ids)

    az_command = f'az resource delete --ids {resource_ids_str} --subscription {subscription}'

    print_resources(resource_ids)
    cmd = system(az_command)
    if cmd != 0:
        core.log_error(logger=LOGGER, message=f'VM {vm_name} Delete ERROR')
        return

    core.log(logger=LOGGER, message=f'VM {vm_name} successfully deleted!')


def get_az_resource_ids(vm_name, subscription):
    cmd = f'az vm show -g {RESOURCE_GROUP} -n {vm_name} --query "[id, networkProfile.networkInterfaces[].id, storageProfile.osDisk.managedDisk.id, storageProfile.dataDisks[].managedDisk.id]" --subscription {subscription} -o tsv'
    return run_win_cmd(cmd)


def get_az_subnet_id(subscription):
    cmd = f'az network vnet subnet show -g {NETWORK_RESOURCE_GROUP} -n {SUBNET} --vnet-name {NETWORK} --query "id" --subscription {subscription} -o tsv'
    return run_win_cmd(cmd)[0]


def get_vms():
    subscription = SUBSCRIPTIONS[core.get_value('subscription_vms')]
    cmd = f'az vm list -g {RESOURCE_GROUP} --query "[].name" --subscription {subscription} -o tsv'
    return run_win_cmd(cmd)


# ------- UI -------

def create_vm_submit(sender, data):
    set_state(False)
    create_vm(**data)
    refresh_vms()
    core.set_value('vm_name', generate_vm_name())


def delete_vm_submit(sender, data):
    set_state(False)
    delete_vm(**data)
    refresh_vms()


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


def refresh_vms():
    set_state(False)
    core.configure_item('vm_combo', items=get_vms())
    core.set_value('vm_combo', '')
    set_state(True)


def set_state(state=True):
    # Provision tab
    core.configure_item('subscription', enabled=state)
    core.configure_item('vm_name', enabled=state)
    core.configure_item('data_disks', enabled=state)
    core.configure_item('Submit', enabled=state)

    # VM tab
    core.configure_item('subscription_vms', enabled=state)
    core.configure_item('Refresh', enabled=state)
    core.configure_item('vm_combo', enabled=state)
    if state == False:
        core.configure_item('Delete', enabled=state)

# ------- Main -------


def main():
    with simple.window(WINDOW_NAME, **WINDOW_SIZE, no_move=True, no_close=True, no_collapse=False, x_pos=0, y_pos=0, no_resize=True):
        with simple.tab_bar('tab_bar'):
            with simple.tab('create_tab', label='Create VM'):
                core.add_radio_button('subscription', items=SUBSCRIPTIONS)
                core.add_input_text('vm_name', label='VM Name', callback=enable_submit,
                                    no_spaces=True, default_value=generate_vm_name())
                core.add_slider_int('data_disks', max_value=3, label='Data Disks')
                core.add_button('Submit', callback=create_vm_submit,
                                callback_data=get_data, enabled=True)

            with simple.tab('vms_tab', label='VMs'):
                core.add_radio_button('subscription_vms', items=SUBSCRIPTIONS, callback=refresh_vms)
                core.add_button(name='Refresh', callback=refresh_vms)

                core.add_combo(name='vm_combo', items=get_vms(), label='VM', callback=enable_delete)

                core.add_button(name='Delete', callback=delete_vm_submit,
                                callback_data=get_data_delete, enabled=False)
                core.set_item_color('Delete', core.mvGuiCol_Button, color=[255, 0, 0, 255])

            with simple.tab('log_tab', label='Log'):
                core.add_logger(LOGGER, autosize_x=True, autosize_y=True, filter=False,
                                clear_button=False, copy_button=False, auto_scroll=True, auto_scroll_button=False, log_level=0)

    core.start_dearpygui()


if __name__ == '__main__':
    main()

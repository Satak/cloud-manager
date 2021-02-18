from json import dumps

from dearpygui import core, simple
import pyperclip

from configs import MAIN_WINDOW_NAME, MAIN_WINDOW_SIZE, WINDOW_NAME, WINDOW_SIZE, SUBSCRIPTIONS, LOGGER

from azure_functions import get_az_resource_group, get_az_subnet_ids, create_az_vm, get_az_vms, az_vm_action, az_vm_resize, az_vm_delete, get_az_vm_details
from misc_utils import get_net_sub, get_vm_sizes, generate_vm_name
from models import VirtualMachine


VMS_TABLE_NAME = "Az VMs"

core.set_main_window_title(MAIN_WINDOW_NAME)
core.set_main_window_size(**MAIN_WINDOW_SIZE)
core.set_main_window_resizable(False)


def get_current_subscription():
    return SUBSCRIPTIONS[core.get_value('subscription')]


def get_current_subscription_vms():
    return SUBSCRIPTIONS[core.get_value('subscription_vms')]


def get_provision_data():
    return {
        'vm_name': core.get_value('vm_name'),
        'subscription': get_current_subscription(),
        'resource_group': core.get_value('resource_group'),
        'network': core.get_value('network'),
        'subnet': core.get_value('subnet'),
        'data_disks': core.get_value('data_disks')
    }


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
    net_data = core.get_data('net_data')[subscription]

    if not network or not subnet or network not in net_data or subnet not in net_data[network][subnet]:
        print('subnet id not found from net data')
        return

    return core.get_data('net_data')[subscription][network][subnet]


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

    subnet_id = get_az_subnet_id(data['subscription'], data['network'], data['subnet'])

    vm_props = {
        'vm_name': data['vm_name'],
        'subscription': data['subscription'],
        'resource_group': data['resource_group'],
        'subnet_id': subnet_id,
        'data_disks': data['data_disks']
    }

    create_az_vm(**vm_props)
    # reset vm name field
    core.set_value('vm_name', generate_vm_name())
    set_state(True)


def enable_submit(sender, data):
    val = core.get_value(sender)
    if not val:
        core.configure_item('Submit', enabled=False)
    else:
        core.configure_item('Submit', enabled=True)


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
    core.configure_item('Refresh VMs', enabled=state)
    core.configure_item('subscription_vms', enabled=state)


def set_state_popup(state):
    core.configure_item('Cancel', enabled=state)
    core.configure_item('Copy VM ID', enabled=state)
    core.configure_item('Copy VM Details', enabled=state)
    core.configure_item('Start', enabled=state)
    core.configure_item('Stop', enabled=state)
    core.configure_item('Restart', enabled=state)
    core.configure_item('Deallocate', enabled=state)
    core.configure_item('Resize Small', enabled=state)
    core.configure_item('Resize Large', enabled=state)
    core.configure_item('Delete', enabled=state)


def refresh_subnet(sender, data):
    network = core.get_value(sender)
    subscription = get_current_subscription()
    subnets = get_net_data_subnet(subscription, network)

    core.configure_item('subnet', items=subnets)
    core.set_value('subnet', subnets[0])


def get_selected_vms(table_name, selections):
    name_column_index = 0
    resource_group_column_index = 2

    vms_selected = {}
    for selection in selections:
        row = selection[0]
        vm_name = core.get_table_item(table_name, row, name_column_index)
        resource_group = core.get_table_item(table_name, row, resource_group_column_index)
        key = f'{resource_group}-{vm_name}'
        if key not in vms_selected:
            vms_selected[key] = {'name': vm_name, 'resource_group': resource_group}

    return vms_selected


def find_vm_ids(vm_obj, vms_data):
    return next((vm.id for vm in vms_data if vm.name == vm_obj['name'] and vm.rg == vm_obj['resource_group']), None)


def get_vm_ids(table_name):
    selections = core.get_table_selections(table_name)

    if not selections:
        core.close_popup('VM Action')
        print('Nothing selected...')
        return

    selected_vms = get_selected_vms(table_name, selections)
    vms_data = core.get_data('vms_data')

    return [find_vm_ids(vm_obj, vms_data) for vm_obj in selected_vms.values()]


def vm_action(action, table_name):

    vm_ids = get_vm_ids(table_name)
    if not vm_ids:
        return

    set_state_popup(False)
    action_map = {
        'start': lambda: az_vm_action(action, vm_ids),
        'stop': lambda: az_vm_action(action, vm_ids),
        'restart': lambda: az_vm_action(action, vm_ids),
        'deallocate': lambda: az_vm_action(action, vm_ids),
        'delete': lambda: az_vm_delete(vm_ids),
        'resize_small': lambda: az_vm_resize('Standard_B1s', vm_ids),
        'resize_large': lambda: az_vm_resize('Standard_B2s', vm_ids),
    }
    if vm_ids:
        action_map[action]()

        vms = [vm_id.split('/')[-1] for vm_id in vm_ids]
        ok_msg = f'VM action {action} success for vms: {vms}'
        core.log(logger=LOGGER, message=ok_msg)
        print(ok_msg)
    else:
        err_msg = f'ERROR: vm_ids not found for VM action {action}'
        core.log_error(logger=LOGGER, message=err_msg)
        print(err_msg)

    set_state_popup(True)
    core.close_popup('VM Action')
    refresh_vms()


def refresh_vms():
    set_state(state=False)
    core.clear_table(VMS_TABLE_NAME)
    vms = get_az_vms(get_current_subscription_vms())
    core.add_data('vms_data', vms)

    for vm in core.get_data('vms_data'):
        core.add_row(VMS_TABLE_NAME, vm.get_values())

    set_state(state=True)


def colorize_button(name, color='red'):
    colors = {
        'red': [255, 0, 0, 255],
        'green': [0, 255, 0, 150],
        'blue': [0, 0, 255, 255],
    }
    core.set_item_color(name, core.mvGuiCol_Button, color=colors[color])


def copy_vm_id(table_name):
    vm_ids = get_vm_ids(table_name)
    if not vm_ids:
        print('vm_ids not found...')
        core.close_popup('VM Action')
        return

    pyperclip.copy(' '.join(vm_ids))

    print('VM IDs copied', vm_ids)
    core.close_popup('VM Action')


def copy_vm_details(table_name):
    vm_ids = get_vm_ids(table_name)
    if not vm_ids:
        print('vm_ids not found...')
        core.close_popup('VM Action')
        return

    vm_details = get_az_vm_details(vm_ids)

    if not vm_details:
        print('vm_details not found...')
        core.close_popup('VM Action')
        return

    pyperclip.copy(dumps(vm_details, indent=2))

    print('VM details copied', vm_ids)
    core.close_popup('VM Action')

# ------------- TABS -------------


def provision_tab():
    with simple.tab('provision_tab', label='Create VM'):

        core.add_radio_button(
            'subscription',
            items=SUBSCRIPTIONS,
            callback=refresh_rg
        )

        rgs = get_rgs(get_current_subscription())
        core.add_combo(
            'resource_group',
            items=rgs,
            label='Resource Group'
        )
        if rgs:
            core.set_value('resource_group', rgs[0])

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
            callback_data=get_provision_data,
            enabled=True
        )
        colorize_button('Submit', 'green')


def vms_tab():

    with simple.tab('vms_tab', label='VMs'):

        core.add_radio_button(
            'subscription_vms',
            items=SUBSCRIPTIONS,
            callback=refresh_vms
        )

        core.add_button(
            'Refresh VMs',
            callback=refresh_vms
        )

        core.add_data('vms_data', data=get_az_vms(get_current_subscription_vms()))

        core.add_table(VMS_TABLE_NAME, headers=VirtualMachine.get_headers(), width=884)

        for vm in core.get_data('vms_data'):
            core.add_row(VMS_TABLE_NAME, vm.get_values())

        with simple.popup(VMS_TABLE_NAME, 'VM Action', mousebutton=core.mvMouseButton_Right, modal=True):
            core.add_button('Cancel', callback=lambda: core.close_popup('VM Action'))
            core.add_button('Copy VM ID', callback=lambda:  copy_vm_id(VMS_TABLE_NAME))
            core.add_button('Copy VM Details', callback=lambda:  copy_vm_details(VMS_TABLE_NAME))

            core.add_separator()
            core.add_spacing(count=1)

            core.add_button('Start', callback=lambda: vm_action('start', VMS_TABLE_NAME))
            core.add_button('Stop', callback=lambda: vm_action('stop', VMS_TABLE_NAME))
            core.add_button('Restart', callback=lambda: vm_action('restart', VMS_TABLE_NAME))
            core.add_button('Deallocate', callback=lambda: vm_action('deallocate', VMS_TABLE_NAME))

            core.add_separator()
            core.add_spacing(count=1)

            core.add_button('Resize Small', callback=lambda: vm_action(
                'resize_small', VMS_TABLE_NAME))
            core.add_button('Resize Large', callback=lambda: vm_action(
                'resize_large', VMS_TABLE_NAME))

            core.add_separator()
            core.add_spacing(count=4)

            core.add_button('Delete', callback=lambda: vm_action('delete', VMS_TABLE_NAME))
            colorize_button('Delete')


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


# ------------- MAIN -------------

def main():
    with simple.window(WINDOW_NAME, **WINDOW_SIZE, no_move=True, no_close=True, no_collapse=False, x_pos=0, y_pos=0, no_resize=True):
        core.add_data('vm_size_data', data=get_vm_sizes())
        core.add_data('rg_data', data=get_rg_data())
        core.add_data('net_data', data=get_net_data())

        with simple.tab_bar('tab_bar'):
            provision_tab()
            vms_tab()
            log_tab()

    core.start_dearpygui()


if __name__ == '__main__':
    main()

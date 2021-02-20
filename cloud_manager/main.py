from json import dumps
import string

from dearpygui import core, simple
import pyperclip

from models import VirtualMachine

from configs import (
    MAIN_WINDOW_NAME,
    MAIN_WINDOW_SIZE,
    WINDOW_NAME,
    WINDOW_SIZE,
    LOGGER,
    VM_SIZES,
    IMAGES,
    ADMIN_USERNAME,
    ADMIN_PASSWORD
)

from azure_functions import (
    get_az_resource_group,
    get_az_subnet_ids,
    create_az_vm,
    get_az_vms,
    az_vm_action,
    az_vm_resize,
    az_vm_delete,
    get_az_vm_details,
    get_az_ip_config_name,
    create_az_public_ip,
    associate_az_public_ip,
    dissociate_az_public_ip,
    get_az_public_ip_address_id,
    delete_az_resources,
    get_az_nsg,
    get_az_subscriptions
)

from misc_utils import (
    get_net_sub,
    get_vm_sizes,
    generate_vm_name,
    generate_vm_tag
)

from data_functions import (
    get_current_subscription,
    get_current_subscription_vms,
    get_provision_data,
    get_net_data_network,
    get_data_resource_group,
    get_data_nsg_names,
    get_data_nsg_id,
    get_data_subnet_id,
    enable_submit,
    set_state,
    set_state_popup,
    colorize_button,
    refresh_subnet,
    refresh_provision_items
)

VMS_TABLE_NAME = "Az VMs"

core.set_main_window_title(MAIN_WINDOW_NAME)
core.set_main_window_size(**MAIN_WINDOW_SIZE)
core.set_main_window_resizable(False)


def get_nsg_data():
    print('Initializing Azure nsg data...')
    return {sub: get_az_nsg(sub) for sub in core.get_data('subscriptions')}


def get_net_data():
    print('Initializing Azure network data...')
    net_data = {}
    for sub in core.get_data('subscriptions'):
        net_data[sub] = {}
        subnet_ids = get_az_subnet_ids(sub)
        if not subnet_ids:
            continue
        print('Done for subscription', sub)
        for subnet_id in subnet_ids:
            network, subnet = get_net_sub(subnet_id)
            if network not in net_data[sub]:
                net_data[sub][network] = {}
            net_data[sub][network][subnet] = subnet_id

    return net_data


def get_rg_data():
    print('Initializing Azure resource group data...')
    return {sub: get_az_resource_group(sub) for sub in core.get_data('subscriptions')}


def create_vm_action(sender, data):
    set_state(False)

    subscription = data['subscription']
    subnet_id = get_data_subnet_id(subscription, data['network'], data['subnet'])
    size = next(
        (size for size_name, size in VM_SIZES.items() if data['size'].lower() == size_name.lower()), 'Standard_B1ms')
    nsg = get_data_nsg_id(subscription, data['nsg'])
    tags = generate_vm_tag(data["vm_name"])

    vm_props = {
        'vm_name': data['vm_name'],
        'subscription': subscription,
        'resource_group': data['resource_group'],
        'subnet_id': subnet_id,
        'image': data['image'],
        'size': size,
        'admin_username': ADMIN_USERNAME,
        'admin_password': ADMIN_PASSWORD,
        'nsg': nsg,
        'tags': tags,
        'public_ip': data['public_ip'],
        'data_disks': data['data_disks']
    }

    core.log_info(logger=LOGGER, message=f'Creating VM {data["vm_name"]}...')
    create_az_vm(**vm_props)
    core.log(logger=LOGGER, message=f'VM {data["vm_name"]} successfully created!')

    # reset vm name field
    core.set_value('vm_name', generate_vm_name())
    set_state(True)


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


def find_vms(vm_obj, vms_data, data_type='id'):
    if data_type == 'id':
        return next((vm.id for vm in vms_data if vm.name == vm_obj['name'] and vm.rg == vm_obj['resource_group']), None)

    if data_type == 'dict':
        return next((vm.__dict__ for vm in vms_data if vm.name == vm_obj['name'] and vm.rg == vm_obj['resource_group']), None)

    if data_type == 'object':
        return next((vm for vm in vms_data if vm.name == vm_obj['name'] and vm.rg == vm_obj['resource_group']), None)


def get_vm_ids(table_name, data_type='id'):
    selections = core.get_table_selections(table_name)

    if not selections:
        core.close_popup('VM Action')
        print('Nothing selected...')
        return

    selected_vms = get_selected_vms(table_name, selections)
    vms_data = core.get_data('vms_data')

    return [find_vms(vm_obj, vms_data, data_type) for vm_obj in selected_vms.values()]


def associate_public_ip(table_name):
    set_state_popup(False)
    vm_objects = get_vm_ids(table_name, data_type='object')
    if not vm_objects:
        print('vm_objects not found...')
        set_state_popup(True)
        core.close_popup('VM Action')
        return
    subscription = get_current_subscription_vms(core.get_data('subscriptions'))

    for vm in vm_objects:
        print(f'[{vm.name}] Associate public IP action started')

        # single NIC support only!
        nic_name = vm.nics[0].split('/')[-1]
        public_ip_name = f'{vm.name}-{vm.rg}-publicIp'

        ip_config_name = get_az_ip_config_name(
            nic_name=nic_name,
            resource_group=vm.rg,
            subscription=subscription
        )

        print(f'[{vm.name}] IP Config Name found: {ip_config_name} from NIC: {nic_name}, creating Public IP: {public_ip_name}...')

        create_az_public_ip(
            name=public_ip_name,
            resource_group=vm.rg,
            subscription=subscription
        )

        print(f'[{vm.name}] Public IP created: {public_ip_name}')

        print(f'[{vm.name}] Associating Public IP to NIC: {nic_name}...')
        associate_az_public_ip(
            ip_config_name=ip_config_name,
            nic_name=nic_name,
            public_ip_name=public_ip_name,
            resource_group=vm.rg,
            subscription=subscription
        )

        ok_msg = f'[{vm.name}] Associate public IP OK: {public_ip_name}'
        print(ok_msg)
        core.log(logger=LOGGER, message=ok_msg)

    set_state_popup(True)
    core.close_popup('VM Action')


def dissociate_public_ip(table_name):
    set_state_popup(False)
    vm_objects = get_vm_ids(table_name, data_type='object')
    if not vm_objects:
        print('vm_objects not found...')
        set_state_popup(True)
        core.close_popup('VM Action')
        return
    subscription = get_current_subscription_vms(core.get_data('subscriptions'))

    for vm in vm_objects:
        print(f'[{vm.name}] Dissociating public IP action started')

        # single NIC support only!
        nic_name = vm.nics[0].split('/')[-1]

        ip_config_name = get_az_ip_config_name(
            nic_name=nic_name,
            resource_group=vm.rg,
            subscription=subscription
        )

        print(f'[{vm.name}] IP Config Name found: {ip_config_name} from NIC: {nic_name}')

        public_ip_id = get_az_public_ip_address_id(
            ip_config_name=ip_config_name,
            nic_name=nic_name,
            resource_group=vm.rg,
            subscription=subscription
        )

        if public_ip_id:
            public_ip_name = public_ip_id.split('/')[-1]
            print(f'[{vm.name}] Public IP found: {public_ip_name}')

            print(f'[{vm.name}] Dissociating Public IP from NIC: {nic_name}...')

            dissociate_az_public_ip(
                ip_config_name=ip_config_name,
                nic_name=nic_name,
                resource_group=vm.rg,
                subscription=subscription
            )

            print(f'[{vm.name}] Dissociating public IP OK, deleting public IP: {public_ip_name}...')

            delete_az_resources([public_ip_id])

            print(f'[{vm.name}] Public IP deleted: {public_ip_id}')
            ok_msg = f'[{vm.name}] Dissociate/delete public IP OK: {public_ip_name}'
            core.log(logger=LOGGER, message=ok_msg)

        else:
            err_msg = f'[{vm.name}] Public IP not found from NIC: {nic_name}'
            print(err_msg)
            core.log_error(logger=LOGGER, message=err_msg)

    set_state_popup(True)
    core.close_popup('VM Action')


def vm_action(action, table_name):

    vm_ids = get_vm_ids(table_name)
    if not vm_ids:
        return

    set_state_popup(False)
    size_name_data = core.get_value('new_vm_size')
    new_size = next(
        (size for size_name, size in VM_SIZES.items() if size_name_data.lower() == size_name.lower()), None)

    action_map = {
        'start': lambda: az_vm_action(action, vm_ids),
        'stop': lambda: az_vm_action(action, vm_ids),
        'restart': lambda: az_vm_action(action, vm_ids),
        'deallocate': lambda: az_vm_action(action, vm_ids),
        'resize': lambda: az_vm_resize(new_size, vm_ids),
        'delete': lambda: az_vm_delete(vm_ids),
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
    vms = get_az_vms(get_current_subscription_vms(core.get_data('subscriptions')))
    core.add_data('vms_data', vms)

    for vm in core.get_data('vms_data'):
        core.add_row(VMS_TABLE_NAME, vm.get_values())

    set_state(state=True)


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
    set_state_popup(False)
    vm_ids = get_vm_ids(table_name)
    if not vm_ids:
        print('vm_ids not found...')
        set_state_popup(True)
        core.close_popup('VM Action')
        return

    vm_details = get_az_vm_details(vm_ids)

    if not vm_details:
        print('vm_details not found...')
        set_state_popup(True)
        core.close_popup('VM Action')
        return

    pyperclip.copy(dumps(vm_details, indent=2))

    print('VM details copied', vm_ids)
    set_state_popup(True)
    core.close_popup('VM Action')


def copy_vm_info(table_name):
    set_state_popup(False)
    vm_objects = get_vm_ids(table_name, data_type='dict')
    if not vm_objects:
        print('vm_objects not found...')
        set_state_popup(True)
        core.close_popup('VM Action')
        return

    pyperclip.copy(dumps(vm_objects, indent=2))

    print('VM basic info copied')
    set_state_popup(True)
    core.close_popup('VM Action')

# ------------- TABS -------------


def provision_tab():
    with simple.tab('provision_tab', label='Create VM'):

        core.add_radio_button(
            'subscription',
            items=core.get_data('subscriptions'),
            callback=refresh_provision_items
        )

        core.add_spacing(count=2)
        core.add_separator()
        core.add_spacing(count=2)

        rgs = get_data_resource_group(get_current_subscription(core.get_data('subscriptions')))
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
            items=get_net_data_network(get_current_subscription(core.get_data('subscriptions')))
        )

        core.add_combo(
            'subnet',
            label='Subnet'
        )

        nsg = get_data_nsg_names(get_current_subscription(core.get_data('subscriptions')))
        core.add_combo(
            'nsg_group',
            items=nsg,
            label='Network Security Group'
        )
        if nsg:
            core.set_value('nsg_group', nsg[0])

        core.add_radio_button(
            'public_ip',
            items=['No Public IP', 'Public IP']
        )

        core.add_spacing(count=2)
        core.add_separator()
        core.add_spacing(count=2)

        core.add_input_text(
            'vm_name',
            label='VM Name',
            callback=enable_submit,
            no_spaces=True,
            default_value=generate_vm_name()
        )

        images = list(core.get_data('images').keys())
        core.add_combo(
            'image',
            label='Image',
            items=images
        )
        core.set_value('image', images[0])

        core.add_slider_int(
            'data_disks',
            max_value=3,
            label='Data Disks'
        )

        size_items = [string.capwords(size) for size in VM_SIZES.keys()]
        core.add_combo(
            'vm_size',
            label='Size',
            items=size_items
        )
        core.set_value('vm_size', size_items[0])

        core.add_spacing(count=2)
        core.add_separator()
        core.add_spacing(count=2)

        core.add_button(
            'Submit',
            callback=create_vm_action,
            callback_data=get_provision_data,
            enabled=True
        )
        colorize_button('Submit', 'green')


def vms_tab():

    with simple.tab('vms_tab', label='VMs'):

        core.add_radio_button(
            'subscription_vms',
            items=core.get_data('subscriptions'),
            callback=refresh_vms
        )

        core.add_button(
            'Refresh VMs',
            callback=refresh_vms
        )

        core.add_data('vms_data', data=get_az_vms(
            get_current_subscription_vms(core.get_data('subscriptions'))))

        core.add_table(VMS_TABLE_NAME, headers=VirtualMachine.get_headers(),
                       width=WINDOW_SIZE['width'], height=500)

        for vm in core.get_data('vms_data'):
            core.add_row(VMS_TABLE_NAME, vm.get_values())

        with simple.popup(VMS_TABLE_NAME, 'VM Action', mousebutton=core.mvMouseButton_Right, modal=True):
            core.add_button('Cancel', callback=lambda: core.close_popup('VM Action'))
            core.add_button('Copy VM ID', callback=lambda:  copy_vm_id(VMS_TABLE_NAME))
            core.add_button('Copy VM Details', callback=lambda:  copy_vm_details(VMS_TABLE_NAME))
            core.add_button('Copy VM Info', callback=lambda:  copy_vm_info(VMS_TABLE_NAME))

            core.add_separator()
            core.add_spacing(count=1)

            core.add_button('Start', callback=lambda: vm_action('start', VMS_TABLE_NAME))
            core.add_button('Stop', callback=lambda: vm_action('stop', VMS_TABLE_NAME))
            core.add_button('Restart', callback=lambda: vm_action('restart', VMS_TABLE_NAME))
            core.add_button('Deallocate', callback=lambda: vm_action('deallocate', VMS_TABLE_NAME))

            core.add_separator()
            core.add_spacing(count=1)

            core.add_button('Associate Public IP',
                            callback=lambda: associate_public_ip(VMS_TABLE_NAME))

            core.add_button('Dissociate Public IP',
                            callback=lambda: dissociate_public_ip(VMS_TABLE_NAME))

            core.add_separator()
            core.add_spacing(count=1)

            size_items = [string.capwords(size) for size in VM_SIZES.keys()]
            core.add_combo(
                'new_vm_size',
                label='Size',
                items=size_items
            )
            core.set_value('new_vm_size', size_items[0])
            core.add_button('Resize', callback=lambda: vm_action(
                'resize', VMS_TABLE_NAME))

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
        core.add_data('subscriptions', data=get_az_subscriptions())
        core.add_data('vm_size_data', data=get_vm_sizes())
        core.add_data('images', data=IMAGES)
        core.add_data('rg_data', data=get_rg_data())
        core.add_data('net_data', data=get_net_data())
        core.add_data('nsg_data', data=get_nsg_data())

        with simple.tab_bar('tab_bar'):
            provision_tab()
            vms_tab()
            log_tab()

    core.start_dearpygui()


if __name__ == '__main__':
    main()

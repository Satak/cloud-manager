from json import dumps
import string

import itertools

from dearpygui import core, simple
import pyperclip
from pprint import pprint

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
    get_az_subscriptions,
    attach_az_disk,
    get_az_vm_data_disk_ids,
    detach_az_disk,
    delete_az_disk,
    execute_az_script,
    get_az_nsg_ids
)

from misc_utils import (
    get_net_sub,
    get_vm_sizes,
    generate_vm_name,
    generate_vm_tag,
    run_add_cmdkey,
    run_rdp_cmd,
    get_scripts,
    get_script_path
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


def apply_theme():
    theme = core.get_value('Themes')
    core.set_theme(theme)


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


def get_selected_vms_by_rows(table_name, rows):
    name_column_index = 0
    resource_group_column_index = 2

    vms_selected = []
    for row in rows:
        vm_name = core.get_table_item(table_name, row, name_column_index)
        resource_group = core.get_table_item(table_name, row, resource_group_column_index)
        vms_selected.append({'name': vm_name, 'resource_group': resource_group})

    return vms_selected


def find_vm(vm_obj, vms_data):
    return next((vm for vm in vms_data if vm.name == vm_obj['name'] and vm.rg == vm_obj['resource_group']), None)


def get_selected_vms(table_name):
    selections = core.get_table_selections(table_name)
    rows = [s[0] for s in selections]

    selected_vms = get_selected_vms_by_rows(table_name, rows)
    vms_data = core.get_data('vms_data')

    return [find_vm(vm_obj, vms_data) for vm_obj in selected_vms]


def associate_public_ip():
    set_state_popup(False)
    vm_objects = core.get_data('selected_vms_data')
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


def dissociate_public_ip():
    set_state_popup(False)
    vm_objects = core.get_data('selected_vms_data')
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


def attach_disk_action(disk_ids):
    for disk_id in disk_ids:
        data_disk_ids = get_az_vm_data_disk_ids([disk_id])
        num = len(data_disk_ids) + 1
        vm_name = disk_id.split('/')[-1]
        props = {
            'vm_name': vm_name,
            'disk_name': f'{vm_name}-data-disk-{num}',
            'resource_group': disk_id.split('/')[4],
            'subscription': get_current_subscription_vms(core.get_data('subscriptions'))
        }

        attach_az_disk(**props)


def detach_disk_action(delete_disk=False):
    print('VM Action: Detach')
    disk_name = core.get_value('vm_data_disks')
    data_disk_ids = core.get_data('data_disk_ids')
    selected_vms = core.get_data('selected_vms_data')
    subscription = get_current_subscription_vms(core.get_data('subscriptions'))

    data_disk_id = next(
        (disk_id for disk_id in data_disk_ids if disk_id.split('/')[-1] == disk_name), None)

    if not data_disk_id:
        print('[Detach action] Error: No data_disk_id found')
        return

    vm = next((vm for vm in selected_vms if data_disk_id in vm.data_disks), None)

    if not vm:
        print('[Detach action] Error: No VM found')
        return

    props = {
        'vm_name': vm.name,
        'disk_name': disk_name,
        'resource_group': vm.rg,
        'subscription': subscription
    }

    # pprint(props, indent=2)
    detach_az_disk(**props)

    print(f'[{vm.name}] Detach disk [{disk_name}] OK')

    if delete_disk:
        print(f'Deleting disk {data_disk_id}')
        delete_az_disk([data_disk_id])


def vm_action(action):
    set_state_popup(False)
    vm_objects = core.get_data('selected_vms_data')
    vm_ids = [vm.id for vm in vm_objects]

    delete_disk = core.get_value('delete_disk')
    size_name_data = core.get_value('new_vm_size')
    new_size = next(
        (size for size_name, size in VM_SIZES.items() if size_name_data.lower() == size_name.lower()), None)

    action_map = {
        'start': lambda: az_vm_action(action, vm_ids),
        'stop': lambda: az_vm_action(action, vm_ids),
        'restart': lambda: az_vm_action(action, vm_ids),
        'deallocate': lambda: az_vm_action(action, vm_ids),
        'resize': lambda: az_vm_resize(new_size, vm_ids),
        'attach_disk': lambda: attach_disk_action(vm_ids),
        'detach_disk': lambda: detach_disk_action(delete_disk),
        'delete': lambda: az_vm_delete(vm_ids),
    }

    action_map[action]()

    # vms = [vm_id.split('/')[-1] for vm_id in vm_ids]
    # ok_msg = f'VM action {action} success for vms: {vms}'
    # core.log(logger=LOGGER, message=ok_msg)
    # print(ok_msg)

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

    core.configure_item('vm_data_disks', items=[])
    core.set_value('vm_data_disks', '')

    core.configure_item('selected_vms', items=[])
    core.configure_item('selected_vms', num_items=0)

    core.add_data('selected_vms_data', [])

    core.set_value('delete_disk', False)

    set_state_popup(False, include_cancel=False)


def copy_vm_id():
    vm_objects = core.get_data('selected_vms_data')
    vm_ids = [vm.id for vm in vm_objects]

    pyperclip.copy(' '.join(vm_ids))

    print('VM IDs copied', vm_ids)
    core.close_popup('VM Action')


def copy_vm_details():
    set_state_popup(False)
    vm_objects = core.get_data('selected_vms_data')
    vm_ids = [vm.id for vm in vm_objects]

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


def copy_vm_info():
    set_state_popup(False)
    vm_objects = core.get_data('selected_vms_data')
    vm_dicts = [vm.__dict__ for vm in vm_objects]

    pyperclip.copy(dumps(vm_dicts, indent=2))

    print('VM basic info copied')
    set_state_popup(True)
    core.close_popup('VM Action')


def get_nsg_info():
    set_state_popup(False)
    vm_objects = core.get_data('selected_vms_data')

    nic_ids = [vm.nics[0] for vm in vm_objects]

    nsg_data = get_az_nsg_ids(nic_ids)
    pyperclip.copy(dumps(nsg_data, indent=2))

    print('NSG info copied')
    set_state_popup(True)
    core.close_popup('VM Action')


def rdp_action():
    set_state_popup(False)
    vm_objects = core.get_data('selected_vms_data')

    for vm in vm_objects:
        if not vm.public_ips:
            print(f'[{vm.name}] No public IP found...')
            continue
        run_add_cmdkey(vm.public_ips, ADMIN_USERNAME, ADMIN_PASSWORD)
        run_rdp_cmd(vm.public_ips)

    set_state_popup(True)
    core.close_popup('VM Action')


def execute_script_action():
    set_state_popup(False)

    vm_objects = core.get_data('selected_vms_data')

    vm_ids = [vm.id for vm in vm_objects]
    vm_names = [vm.name for vm in vm_objects]
    script_to_execute = core.get_value('script-to-execute')

    if script_to_execute in ['create-local-admin.ps1', 'remove-local-user.ps1']:
        params = f'"Username={ADMIN_USERNAME}" "Password={ADMIN_PASSWORD}"'
    else:
        params = core.get_value('script_params')

    script_file_type = script_to_execute.split('.')[-1]

    command = 'RunPowerShellScript' if script_file_type == 'ps1' else 'RunShellScript'

    print('')
    print(f'[{script_to_execute}] Executing against: {vm_names}...')
    res = execute_az_script(vm_ids, get_script_path(script_to_execute), params, command)

    print(f'[{script_to_execute}] Script executed. Results:')

    if 'value' in res:
        for item in res['value']:
            print('')
            pprint(item, indent=2)
            print('')
            if 'message' in item and item['code'] == 'ComponentStatus/StdOut/succeeded':
                core.log(logger=LOGGER, message=item['message'])

    set_state_popup(True)
    core.close_popup('VM Action')


def data_disk_controller(vm_objects):
    data_disks = [vm.data_disks for vm in vm_objects] if vm_objects else []
    data_disk_ids = list(itertools.chain(*data_disks))

    data_disk_names = [disk_id.split('/')[-1] for disk_id in data_disk_ids]
    core.add_data('data_disk_ids', data=data_disk_ids)
    return data_disk_names


def action_popup_controller():
    vm_objects = get_selected_vms(VMS_TABLE_NAME)
    core.add_data('selected_vms_data', vm_objects)

    vms = [vm.name for vm in vm_objects] if vm_objects else []
    data_disk_names = data_disk_controller(vm_objects)

    core.configure_item('vm_data_disks', items=data_disk_names)
    core.set_value('vm_data_disks', '')
    core.configure_item('selected_vms', items=vms)
    core.configure_item('selected_vms', num_items=len(vms))

    set_state_popup(bool(vm_objects), include_cancel=False)


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

        size_items = [string.capwords(size) for size in VM_SIZES.keys()]
        core.add_combo(
            'vm_size',
            label='VM Size',
            items=size_items
        )
        core.set_value('vm_size', size_items[0])

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

        core.add_data('selected_data_disks', data={})

        core.add_data('vms_data', data=get_az_vms(
            get_current_subscription_vms(core.get_data('subscriptions'))))

        core.add_table(VMS_TABLE_NAME, headers=VirtualMachine.get_headers(),
                       width=WINDOW_SIZE['width'], height=500, callback=action_popup_controller)

        for vm in core.get_data('vms_data'):
            core.add_row(VMS_TABLE_NAME, vm.get_values())

        with simple.popup(VMS_TABLE_NAME, 'VM Action', mousebutton=core.mvMouseButton_Right, modal=True):
            core.add_listbox('selected_vms', enabled=False, items=[],
                             label='Selected VMs', default_value=-1, num_items=0)
            core.set_item_color('selected_vms', core.mvGuiCol_TextDisabled,
                                color=[0, 225, 129, 255])

            core.add_button('Cancel', callback=lambda: core.close_popup('VM Action'))

            core.add_separator()
            core.add_spacing(count=1)

            core.add_button('Copy VM ID', callback=copy_vm_id, enabled=False)
            core.add_button('Copy VM Details', callback=copy_vm_details, enabled=False)
            core.add_button('Copy VM Info', callback=copy_vm_info, enabled=False)
            core.add_button('Get NSG Info', callback=get_nsg_info, enabled=False)

            core.add_separator()
            core.add_spacing(count=1)

            core.add_combo(
                'script-to-execute',
                label='Script to Execute',
                items=get_scripts(),
                enabled=False
            )
            core.add_input_text(
                'script_params',
                label='Parameters',
                default_value='"Name=Value" "Item=Something"',
                enabled=False
            )
            core.add_button('Execute Script', callback=execute_script_action, enabled=False)
            core.add_button('RDP', callback=rdp_action, enabled=False)

            core.add_separator()
            core.add_spacing(count=1)

            core.add_button('Start', callback=lambda: vm_action('start'), enabled=False)
            core.add_button('Stop', callback=lambda: vm_action('stop'), enabled=False)
            core.add_button('Restart', callback=lambda: vm_action('restart'), enabled=False)
            core.add_button('Deallocate', callback=lambda: vm_action('deallocate'), enabled=False)

            core.add_separator()
            core.add_spacing(count=1)

            core.add_button('Attach Disk', callback=lambda: vm_action('attach_disk'), enabled=False)
            core.add_button('Detach Disk', callback=lambda: vm_action('detach_disk'), enabled=False)
            core.add_same_line()
            core.add_combo(
                'vm_data_disks',
                label='Data Disks',
                items=[],
                enabled=False
            )
            core.add_checkbox('delete_disk', label='Delete')

            core.add_separator()
            core.add_spacing(count=1)

            core.add_button('Associate Public IP', callback=associate_public_ip, enabled=False)

            core.add_button('Dissociate Public IP', callback=dissociate_public_ip, enabled=False)

            core.add_separator()
            core.add_spacing(count=1)

            size_items = [string.capwords(size) for size in VM_SIZES.keys()]
            core.add_combo(
                'new_vm_size',
                label='Size',
                items=size_items,
                enabled=False
            )
            core.set_value('new_vm_size', size_items[0])
            core.add_button('Resize', callback=lambda: vm_action('resize'), enabled=False)

            core.add_separator()
            core.add_spacing(count=4)

            core.add_button('Delete', callback=lambda: vm_action('delete'), enabled=False)
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
        with simple.menu_bar('Main Menu Bar'):
            with simple.menu('Settings'):
                themes = ['Dark', 'Light', 'Classic', 'Dark 2', 'Grey',
                          'Dark Grey', 'Cherry', 'Purple', 'Gold', 'Red']
                core.add_combo('Themes', items=themes, default_value='Dark', callback=apply_theme)

        core.add_data('subscriptions', data=get_az_subscriptions())
        core.add_data('vm_size_data', data=get_vm_sizes())
        core.add_data('images', data=IMAGES)
        core.add_data('rg_data', data=get_rg_data())
        core.add_data('net_data', data=get_net_data())
        core.add_data('nsg_data', data=get_nsg_data())
        core.add_data('selected_vms_data', data=[])

        with simple.tab_bar('tab_bar'):
            provision_tab()
            vms_tab()
            log_tab()

    core.start_dearpygui()


if __name__ == '__main__':
    print('Cloud manager starting up...')
    main()
    print('Cloud manager exited')

from dearpygui import core


def get_current_subscription(subscriptions):
    return subscriptions[core.get_value('subscription')]


def get_current_subscription_vms(subscriptions):
    return subscriptions[core.get_value('subscription_vms')]


def get_provision_data():
    return {
        'vm_name': core.get_value('vm_name'),
        'subscription': get_current_subscription(core.get_data('subscriptions')),
        'resource_group': core.get_value('resource_group'),
        'network': core.get_value('network'),
        'subnet': core.get_value('subnet'),
        'public_ip': core.get_value('public_ip'),
        'data_disks': core.get_value('data_disks'),
        'size': core.get_value('vm_size'),
        'image': core.get_value('image'),
        'nsg': core.get_value('nsg_group')
    }


def get_net_data_network(subscription):
    net_data = list(core.get_data('net_data')[subscription].keys())
    return net_data


def get_net_data_subnet(subscription, network):
    return list(core.get_data('net_data')[subscription][network].keys())


def get_data_resource_group(subscription):
    return core.get_data('rg_data')[subscription]


def get_nsg_name(nsg_id):
    return nsg_id.split('/')[-1]


def get_data_nsg_names(subscription):
    nsg_ids = core.get_data('nsg_data')[subscription]
    return [get_nsg_name(nsg_id) for nsg_id in nsg_ids]


def get_data_nsg_id(subscription, nsg_name):
    nsg_ids = core.get_data('nsg_data')[subscription]
    return next((nsg_id for nsg_id in nsg_ids if get_nsg_name(nsg_id) == nsg_name), None)


def get_data_subnet_id(subscription, network, subnet):
    net_data = core.get_data('net_data')[subscription]

    if not network or not subnet or network not in net_data or subnet not in net_data[network][subnet]:
        print('subnet id not found from net data')
        return

    return core.get_data('net_data')[subscription][network][subnet]


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
    core.configure_item('image', enabled=state)
    core.configure_item('data_disks', enabled=state)
    core.configure_item('nsg_group', enabled=state)
    core.configure_item('public_ip', enabled=state)
    core.configure_item('vm_size', enabled=state)
    core.configure_item('Submit', enabled=state)

    # VM tab
    core.configure_item('Refresh VMs', enabled=state)
    core.configure_item('subscription_vms', enabled=state)


def set_state_popup(state, include_cancel=True):
    if include_cancel:
        core.configure_item('Cancel', enabled=state)
    core.configure_item('Copy VM ID', enabled=state)
    core.configure_item('Copy VM Details', enabled=state)
    core.configure_item('Copy VM Info', enabled=state)
    core.configure_item('Get NSG Info', enabled=state)
    core.configure_item('script-to-execute', enabled=state)
    core.configure_item('script_params', enabled=state)
    core.configure_item('Execute Script', enabled=state)
    core.configure_item('RDP', enabled=state)
    core.configure_item('Start', enabled=state)
    core.configure_item('Stop', enabled=state)
    core.configure_item('Restart', enabled=state)
    core.configure_item('Deallocate', enabled=state)
    core.configure_item('Attach Disk', enabled=state)
    core.configure_item('vm_data_disks', enabled=state)
    core.configure_item('Detach Disk', enabled=state)
    core.configure_item('Associate Public IP', enabled=state)
    core.configure_item('Dissociate Public IP', enabled=state)
    core.configure_item('Resize', enabled=state)
    core.configure_item('new_vm_size', enabled=state)
    core.configure_item('Delete', enabled=state)


def refresh_subnet(sender, data):
    network = core.get_value(sender)
    subscription = get_current_subscription(core.get_data('subscriptions'))
    subnets = get_net_data_subnet(subscription, network)

    core.configure_item('subnet', items=subnets)
    core.set_value('subnet', subnets[0])


def colorize_button(name, color='red'):
    colors = {
        'red': [255, 0, 0, 255],
        'green': [0, 255, 0, 150],
        'blue': [0, 0, 255, 255],
    }
    core.set_item_color(name, core.mvGuiCol_Button, color=colors[color])


def refresh_provision_items(sender, data):
    set_state(False)
    subscription = get_current_subscription(core.get_data('subscriptions'))

    # resource group
    rgs = get_data_resource_group(subscription)
    core.configure_item('resource_group', items=rgs)
    core.set_value('resource_group', rgs[0])

    # network security group
    nsg = get_data_nsg_names(subscription)
    core.configure_item('nsg_group', items=nsg)
    core.set_value('nsg_group', nsg[0])

    # network
    networks = get_net_data_network(subscription)

    subnets = get_net_data_subnet(subscription, networks[0])
    core.configure_item('network', items=networks)
    core.set_value('network', networks[0])

    core.configure_item('subnet', items=subnets)
    core.set_value('subnet', subnets[0])

    set_state(True)

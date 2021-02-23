from dearpygui import core

from models import VirtualMachine
from misc_utils import run_cmd, print_resources


def get_az_subscriptions():
    cmd = 'az account list --query "[].name" -o tsv'
    all_subscriptions = run_cmd(cmd, as_json=False)
    return [sub for sub in all_subscriptions if get_az_resource_group(sub)]


def az_vm_resize(size, vm_ids):
    ids_str = ' '.join(vm_ids)
    cmd = f'az vm resize --ids {ids_str} --size {size} --no-wait'
    print('VM Resize Action:')
    print(cmd)
    run_cmd(cmd, as_json=False)


def detach_az_disk(vm_name, disk_name, resource_group, subscription):
    cmd = f'az vm disk detach --vm-name {vm_name} --name {disk_name} --resource-group {resource_group} --subscription "{subscription}"'
    print('Detach disk:')
    print(cmd)
    run_cmd(cmd, as_json=False)


def attach_az_disk(vm_name, disk_name, resource_group, subscription, size=1, sku='Standard_LRS'):
    cmd = f'az vm disk attach --name {disk_name} --new --vm-name {vm_name} --size-gb {size} --sku {sku} --resource-group {resource_group} --subscription "{subscription}"'

    print('Attach disk:')
    print(cmd)
    run_cmd(cmd, as_json=False)


def delete_az_resources(resource_ids):
    resource_ids_str = ' '.join(resource_ids)
    cmd = f'az resource delete --ids {resource_ids_str}'
    run_cmd(cmd)


def az_vm_delete(vm_ids):

    resource_ids = get_az_resource_ids(vm_ids)
    public_ip_ids = get_az_vm_public_ip_ids(vm_ids)
    resource_id_list = []

    if len(vm_ids) > 1:
        for vm_obj in resource_ids:
            resource_id_list.append(vm_obj['vmId'])
            resource_id_list.append(vm_obj['osDisk'])

            for nic_id in vm_obj['nics']:
                resource_id_list.append(nic_id)

            for data_disk_id in vm_obj['dataDisks']:
                resource_id_list.append(data_disk_id)

        if public_ip_ids:
            resource_id_list += public_ip_ids

        resource_ids_str = ' '.join(resource_id_list)
        print_resources(resource_id_list)
    else:
        if public_ip_ids:
            resource_ids += public_ip_ids
        resource_ids_str = ' '.join(resource_ids)
        print_resources(resource_ids)

    cmd = f'az resource delete --ids {resource_ids_str}'
    run_cmd(cmd, as_json=False)


def az_vm_action(action, vm_ids):
    ids_str = ' '.join(vm_ids)
    cmd = f'az vm {action} --ids {ids_str} --no-wait'

    print('VM Action:')
    print(cmd)
    run_cmd(cmd, as_json=False)


def create_az_vm(vm_name, subscription, resource_group, subnet_id, image, size, admin_username, admin_password, tags=None, nsg=None, public_ip=0, data_disks=0):

    vm_config = {
        'name': vm_name,
        'subscription': f'"{subscription}"',
        'resource-group': resource_group,
        'subnet': subnet_id,
        'image': image,
        'size': size,
        'admin-username': admin_username,
        'admin-password': admin_password,
        'nsg': nsg,
        'tags': tags,
    }

    if not nsg:
        vm_config['nsg'] = '""'

    if not public_ip:
        vm_config['public-ip-address'] = '""'

    az_command_params = ' '.join(f'--{key} {val}' for key, val in vm_config.items() if val)
    cmd = f'az vm create {az_command_params} --no-wait'

    if data_disks:
        data_disk_sizes = ['1' for _ in range(data_disks)]
        disks_param = f' --data-disk-sizes-gb {" ".join(data_disk_sizes)}'
        cmd += disks_param

    print('VM Create cmd:')
    print(cmd)

    run_cmd(cmd)


def get_az_subnet_ids(subscription):
    cmd = f'az network vnet list --query "[].subnets[].id" --subscription "{subscription}"'
    return run_cmd(cmd)


def get_az_vm_details(vm_ids):
    ids_str = ' '.join(vm_ids)
    cmd = f'az vm show -d --ids {ids_str}'
    return run_cmd(cmd)


def get_az_vm_data_disk_ids(vm_ids):
    ids_str = ' '.join(vm_ids)
    cmd = f'az vm show -d --ids {ids_str} --query "storageProfile.dataDisks[].managedDisk.id"'
    return run_cmd(cmd)


def get_az_vm_public_ip_ids(vm_ids):
    ids_str = ' '.join(vm_ids)
    cmd = f'az vm list-ip-addresses --ids {ids_str} --query "[].virtualMachine.network.publicIpAddresses[].id" -o tsv'
    return run_cmd(cmd, as_json=False)


def get_az_nsg_ids(vm_ids):
    ids_str = ' '.join(vm_ids)
    query = '{vmId: virtualMachine.id, nsgId: networkSecurityGroup.id, subnetId: ipConfigurations[].subnet.id}'

    if len(vm_ids) > 1:
        query = f'[].{query}'

    cmd = f'az network nic show --ids {ids_str} --query "{query}"'
    return run_cmd(cmd)


def get_az_resource_ids(vm_ids):
    ids_str = ' '.join(vm_ids)
    if len(vm_ids) > 1:
        cmd = f'az vm show -d --ids {ids_str} --query "[].{{vmId: id, nics: networkProfile.networkInterfaces[].id, osDisk: storageProfile.osDisk.managedDisk.id, dataDisks: storageProfile.dataDisks[].managedDisk.id}}"'
        return run_cmd(cmd)
    else:
        cmd = f'az vm show -d --ids {ids_str} --query "[id, networkProfile.networkInterfaces[].id, storageProfile.osDisk.managedDisk.id, storageProfile.dataDisks[].managedDisk.id]" -o tsv'
        return run_cmd(cmd, as_json=False)


def get_az_ip_config_name(nic_name, resource_group, subscription):
    cmd = f'az network nic ip-config list --nic-name {nic_name} --resource-group {resource_group} --subscription "{subscription}" --query "[].name" -o tsv'
    data = run_cmd(cmd, as_json=False)
    if not data or len(data) != 1:
        return
    return data[0]


def create_az_public_ip(name, resource_group, subscription):
    cmd = f'az network public-ip create --name {name} --allocation-method Static --resource-group {resource_group} --subscription "{subscription}"'
    run_cmd(cmd)


def associate_az_public_ip(ip_config_name, nic_name, public_ip_name, resource_group, subscription):
    cmd = f'az network nic ip-config update --name {ip_config_name} --nic-name {nic_name} --public-ip-address {public_ip_name} --resource-group {resource_group} --subscription "{subscription}"'
    run_cmd(cmd)


def get_az_public_ip_address_id(ip_config_name, nic_name, resource_group, subscription):
    cmd = f'az network nic ip-config show --name {ip_config_name} --nic-name {nic_name} --resource-group {resource_group} --query publicIpAddress.id --subscription "{subscription}" -o tsv'
    data = run_cmd(cmd, as_json=False)
    if not data or len(data) != 1:
        return
    return data[0]


def dissociate_az_public_ip(ip_config_name, nic_name, resource_group, subscription):
    cmd = f'az network nic ip-config update --name {ip_config_name} --nic-name {nic_name} --remove publicIpAddress --resource-group {resource_group} --subscription "{subscription}"'
    run_cmd(cmd)


def get_az_vms(subscription):
    '''Get Azure VMs from subscription'''

    query_props = {
        'id': 'id',
        'name': 'name',
        'state': 'powerState',
        'rg': 'resourceGroup',
        'size': 'hardwareProfile.vmSize',
        'publicIps': 'publicIps',
        'privateIps': 'privateIps',
        'os': 'storageProfile.imageReference.offer',
        'osVer': 'storageProfile.imageReference.sku',
        'nics': 'networkProfile.networkInterfaces[].id',
        'dataDisks': 'storageProfile.dataDisks[].managedDisk.id'
    }

    query = ', '.join(f'{key}: {val}' for key, val in query_props.items() if val)

    cmd = f'az vm list -d --query "[].{{{query}}}" --subscription "{subscription}"'
    vm_data = run_cmd(cmd)
    vm_sizes = core.get_data('vm_size_data')

    def object_maker(vm_obj):
        size_obj = vm_sizes[vm_obj['size']]

        return {
            'id': vm_obj['id'],
            'name': vm_obj['name'],
            'state': vm_obj['state'],
            'rg': vm_obj['rg'],
            'size': vm_obj['size'],
            'cpu': size_obj['cpu'],
            'mem': size_obj['mem'],
            'private_ips': vm_obj['privateIps'],
            'public_ips': vm_obj['publicIps'],
            'nics': vm_obj['nics'],
            'data_disks': vm_obj['dataDisks'],
            'os': f'{vm_obj["os"]} - {vm_obj["osVer"]}'
        }

    vm_data_final = map(object_maker, vm_data)
    return [VirtualMachine(**vm) for vm in vm_data_final]


def get_az_vms_from_rg(subscription, resource_group):
    cmd = f'az vm list -g {resource_group} --query "[].name" --subscription "{subscription}"'
    return run_cmd(cmd)


def get_az_resource_group(subscription):
    cmd = f'az group list --query "[].name" --subscription "{subscription}"'
    return run_cmd(cmd)


def get_az_nsg(subscription):
    cmd = f'az network nsg list --subscription "{subscription}" --query "[].id"'
    return run_cmd(cmd)


def execute_az_script(vm_ids, script_str, parameters, command):
    ids_str = ' '.join(vm_ids)
    cmd = f'az vm run-command invoke --command-id {command} --ids {ids_str} --scripts "{script_str}" --parameters {parameters}'
    return run_cmd(cmd)

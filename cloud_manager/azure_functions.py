from os import system

from dearpygui import core

from configs import LOGGER, ADMIN_USERNAME, ADMIN_PASSWORD
from models import VirtualMachine
from misc_utils import generate_vm_tag, run_cmd, print_resources


def az_vm_resize(size, vm_ids):
    ids_str = ' '.join(vm_ids)
    cmd = f'az vm resize --ids {ids_str} --size {size} --no-wait'
    print(cmd)
    run_cmd(cmd, as_json=False)


def delete_az_resources(resource_ids):
    resource_ids_str = ' '.join(resource_ids)
    cmd = f'az resource delete --ids {resource_ids_str}'
    run_cmd(cmd)


def az_vm_delete(vm_ids):

    resource_ids = get_az_resource_ids(vm_ids)
    resource_id_list = []

    if len(vm_ids) > 1:
        for vm_obj in resource_ids:
            resource_id_list.append(vm_obj['vmId'])
            resource_id_list.append(vm_obj['osDisk'])

            for nic_id in vm_obj['nics']:
                resource_id_list.append(nic_id)

            for data_disk_id in vm_obj['dataDisks']:
                resource_id_list.append(data_disk_id)

        resource_ids_str = ' '.join(resource_id_list)
        print_resources(resource_id_list)
    else:
        resource_ids_str = ' '.join(resource_ids)
        print_resources(resource_ids)

    cmd = f'az resource delete --ids {resource_ids_str}'
    run_cmd(cmd, as_json=False)


def az_vm_action(action, vm_ids):
    ids_str = ' '.join(vm_ids)
    cmd = f'az vm {action} --ids {ids_str} --no-wait'

    print(cmd)
    run_cmd(cmd, as_json=False)


def create_az_vm(vm_name, subscription, resource_group, subnet_id, image, size, nsg=None, public_ip=0, data_disks=0):
    core.log_info(logger=LOGGER, message=f'Creating VM {vm_name}...')

    vm_config = {
        'name': vm_name,
        'resource-group': resource_group,
        'image': image,
        'admin-username': ADMIN_USERNAME,
        'admin-password': ADMIN_PASSWORD,
        'subscription': f'"{subscription}"',
        'size': size,
        'nsg': nsg,
        'tags': generate_vm_tag(vm_name),
        'subnet': subnet_id,
    }

    if not nsg:
        vm_config['nsg'] = '""'

    if not public_ip:
        vm_config['public-ip-address'] = '""'

    az_command_params = ' '.join(f'--{key} {val}' for key, val in vm_config.items() if val)
    az_command = f'az vm create {az_command_params} --no-wait'

    if data_disks:
        data_disk_sizes = ['1' for _ in range(data_disks)]
        disks_param = f' --data-disk-sizes-gb {" ".join(data_disk_sizes)}'
        az_command += disks_param

    print('VM Create cmd:')
    print(az_command)

    cmd = system(az_command)
    if cmd != 0:
        core.log_error(logger=LOGGER, message=f'VM {vm_name} Creation ERROR')
        return

    core.log(logger=LOGGER, message=f'VM {vm_name} successfully created!')


def get_az_subnet_ids(subscription):
    cmd = f'az network vnet list --query "[].subnets[].id" --subscription "{subscription}"'
    return run_cmd(cmd)


def get_az_vm_details(vm_ids):
    ids_str = ' '.join(vm_ids)
    cmd = f'az vm show -d --ids {ids_str}'
    data = run_cmd(cmd)
    return data


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


def get_az_vms(subscription: str) -> list[VirtualMachine]:
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
            'ips': vm_obj['privateIps'] if not vm_obj['publicIps'] else [vm_obj['privateIps'], vm_obj['publicIps']],
            'nics': vm_obj['nics'],
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

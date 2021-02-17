import subprocess
from json import loads, load
from os import path
from datetime import datetime
from configs import VM_NAME_PREFIX


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


def get_cpu_mem(vm_sizes):
    return next({'cpu': size['numberOfCores'], 'mem': size['memoryInMb']/1024} for size in vm_sizes)


def generate_vm_name():
    t = datetime.now()
    return f'{VM_NAME_PREFIX}-vm-{t.hour}{t.minute}{t.second}'


def generate_vm_tag(vm_name):
    return f'vm={vm_name}'


def print_resources(resources):
    print(f'Deleting resources:')
    for resource in resources:
        print(resource)


def get_vm_sizes():
    # cmd = 'az vm list-sizes --location westeurope'
    script_path = path.dirname(path.abspath(__file__))

    with open(path.join(script_path, 'data', 'sizes.json')) as file:
        sizes = load(file)

    return {size['name']: {'cpu': size['numberOfCores'],
                           'mem': size['memoryInMb']//1024} for size in sizes}

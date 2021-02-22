import subprocess
from json import loads, load
from os import path
from datetime import datetime

from configs import VM_NAME_PREFIX


def run_cmd(cmd, as_json=True):
    with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        data = proc.stdout.read()
        err = proc.stderr.read()

        if not data and err:
            print('run_cmd Error: ', err.decode())
            return

        if not data:
            print('No data from run_cmd')
            return True

        try:
            if not as_json:
                return [line.decode().strip() for line in data.splitlines() if line.decode().strip()]

            return loads(data)
        except Exception as err:
            print(f'Some rare exception occurred on run_cmd: {err}')
            return


def run_add_cmdkey(server, username, password):
    cmd = f'cmdkey /generic:"{server}" /user:"{username}" /pass:"{password}"'
    run_cmd(cmd, as_json=False)
    print(f'[{server}] cmdkey done for RDP')


def run_rdp_cmd(server):
    cmd = f'mstsc /v:{server} /w:1920 /h:1080'
    print(f'[{server}] RDP session started')
    run_cmd(cmd, as_json=False)
    print(f'[{server}] RDP session ended')


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

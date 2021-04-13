from dataclasses import dataclass


@dataclass
class VirtualMachine:
    """Class for Virtual Machine."""
    id: str
    location: str
    name: str
    state: str
    rg: str
    size: str
    cpu: int
    mem: int
    private_ips: str
    public_ips: str
    nics: list[str]
    data_disks: list[str]
    os: str

    @property
    def ips(self):
        return [self.private_ips, self.public_ips] if self.public_ips else self.private_ips

    @property
    def simple_state(self):
        state_map = {
            'VM deallocated': 'Off',
            'VM running': 'On'
        }

        if self.state in state_map.keys():
            return state_map[self.state]
        return self.state

    def get_values(self):
        return [
            self.name,
            self.location,
            self.simple_state,
            self.rg,
            self.cpu,
            self.mem,
            len(self.data_disks),
            self.size,
            self.ips,
            self.os
        ]

    @staticmethod
    def get_headers():
        return [
            'Name',
            'Location',
            'State',
            'Resource Group',
            'CPU',
            'Memory GB',
            'Data Disks',
            'Size',
            'IP Address',
            'OS'
        ]


@dataclass
class EC2Instance:
    instance: any

    @staticmethod
    def get_headers():
        return [
            'Name',
            'State'
        ]

    def get_values(self):
        return [
            next(tag['Value'] for tag in self.instance.tags if tag['Key'] == 'Name'),
            self.instance.state['Name']
        ]

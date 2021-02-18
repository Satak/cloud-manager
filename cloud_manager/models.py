from dataclasses import dataclass


@dataclass
class VirtualMachine:
    """Class for Virtual Machine."""
    id: str
    name: str
    state: str
    rg: str
    size: str
    cpu: int
    mem: int
    ips: str
    nics: list[str]
    os: str

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
            self.simple_state,
            self.rg,
            self.cpu,
            self.mem,
            self.size,
            self.ips,
            self.os
        ]

    @staticmethod
    def get_headers():
        return [
            'Name',
            'State',
            'Resource Group',
            'CPU',
            'Memory GB',
            'Size',
            'IP Address',
            'OS'
        ]

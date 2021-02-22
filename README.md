# Cloud Manager

Small Python UI wrapper for Azure CLI. Windows only at this point! Create and manage virtual machines from single and intuitive UI 😎

## Prerequisites

You must install all these prerequisites and authenticate to Azure with az cli before this can work!

- Windows only (tested with **Windows 10**)
- Azure cloud subscription
- Install Python **3.9**
- Install Azure CLI (<https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows?tabs=azure-cli>)
  - run `az login` to authenticate to your Azure subscription
- Install `dearpygui` (Python library: <https://github.com/hoffstadt/DearPyGui>)
  - run `pip install dearpygui`
- Install `pyperclip` (Python library: <https://github.com/asweigart/pyperclip>)
  - run `pip install pyperclip`

## Start

To start the cloud manager just run the `main.py`

`python .\cloud_manager\main.py`

Launch takes around 20-30 seconds since it's collecting resource group and network data from Azure.

## Themes

You can select your preferred theme from the `Settings` menu.

## Supported management actions

- Copy VM ID to clipboard
- Copy VM Details (API fetch) to clipboard as JSON
- Copy VM Info (local info) to clipboard as JSON
- Execute Script
- RDP
- Start VM
- Stop VM
- Restart VM
- Deallocate VM
- Attach & Create Disk to VM
- Associate Public IP
- Dissociate Public IP
- Resize VM
- Delete VM

## Examples

![cloud manager main](./images/cloud_manager.PNG 'Cloud Manager Main')

![cloud manager vms](./images/cloud_manager_vms.PNG 'Cloud Manager VMs')
![cloud manager action](./images/cloud_manager_action.PNG 'Cloud Manager Action')

![cloud manager log](./images/cloud_manager_log.PNG 'Cloud Manager Log')

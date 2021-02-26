# Cloud Manager

Small Python UI wrapper for Azure CLI. Create and manage virtual machines from single and intuitive UI 😎

## Prerequisites

You must install all these prerequisites and authenticate to Azure with az cli before this can work!

- Windows only (tested with **Windows 10**)
- Azure cloud subscription
- Install Python (tested with 3.9)
- Install Azure CLI (<https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows?tabs=azure-cli>)
  - run `az login` to authenticate to your Azure subscription
- Install `dearpygui` (Python library: <https://github.com/hoffstadt/DearPyGui>)
  - run `pip install dearpygui`
- Install `pyperclip` (Python library: <https://github.com/asweigart/pyperclip>)
  - run `pip install pyperclip`

## Start

To start the cloud manager just run the `main.py`

`python .\cloud_manager\main.py`

Launch takes around 20-30 seconds since it's fetching resource group and network data from Azure and storing it to memory (no database used). VM view might also take a lot of time to refresh since the `az vm list` call can be slow if you have a lot of VMs.

## `configs.py`

You can add your own configs in the `configs.py` file for example:

- `ADMIN_USERNAME` (username for newly created VMs)
- `ADMIN_PASSWORD` (password for newly created VMs)
- `VM_NAME_PREFIX` (default vm name is `<VM_NAME_PREFIX>-vm-<timestamp>`)
- `VM_SIZES` (add your own VM sizes)
- `IMAGES` (add your own images)

## Themes

You can select your preferred theme from the `Settings` menu.

## VM actions

You can perform these actions in the VMs tab. Click any of the columns or rows in the VMs table and then those VMs are selected. You can do any amount of selections and then right click the table to open the actions menu against the selected VMs.

**Copy actions** gets data from selected VMs and sets it to clipboard so it can be pasted (for example notepad, `ctrl+v`) as JSON format.

### Supported VM actions

- `Copy VM ID` to clipboard
- `Copy VM Details` (API fetch) to clipboard as JSON
- `Get NSG Info` Copy VM Network Security Group Info to clipboard as JSON
- `Copy VM Info` (local info) to clipboard as JSON
- `Execute Script` (put your own scripts under `scripts` folder)
- `RDP` Open Remote Desktop connection
- `Start` VM
- `Stop` VM
- `Restart` VM
- `Deallocate` VM
- `Attach Disk` Attach & Create Disk to VM
- `Detach Disk` Detach Disk from VM (with or without delete)
- `Associate Public IP` Create and associate public IP to VM
- `Dissociate Public IP` Dissociate and delete public IP from VM
- `Resize` VM
- `Delete` VM

## Examples

![cloud manager main](./images/cloud_manager.PNG 'Cloud Manager Main')
![cloud manager vms](./images/cloud_manager_vms.PNG 'Cloud Manager VMs')
![cloud manager action](./images/cloud_manager_action.PNG 'Cloud Manager Action')
![cloud manager log](./images/cloud_manager_log.PNG 'Cloud Manager Log')

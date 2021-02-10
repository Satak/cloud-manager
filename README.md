# Cloud Manager

Small Python UI wrapper for Azure CLI. Windows only at this point! Create and delete virtual machines (Windows 2019 image) with one mouse click. Easy 😎

## Prerequisites

You must install all these prerequisites and authenticate to Azure with az cli before this can work!

- Windows only (tested with **Windows 10**)
- Azure cloud subscription
- Install Python (tested with **3.8**)
- Install Azure CLI (<https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows?tabs=azure-cli>)
  - run `az login` to authenticate to your Azure subscription
- Install `dearpygui` (Python library: <https://github.com/hoffstadt/DearPyGui>)
  - run `pip install dearpygui`

**Before first use, change settings in the `config.py` to fit your Azure environment settings!**

## Examples

![cloud manager main](./images/cloud_manager.PNG 'Cloud Manager Main')

![cloud manager log](./images/cloud_manager_log.PNG 'Cloud Manager Log')

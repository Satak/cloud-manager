param(
  [string]$Username,
  [string]$Password
)

New-LocalUser -AccountNeverExpires:$true -Password (ConvertTo-SecureString -AsPlainText -Force $Password) -Name $Username | Add-LocalGroupMember -Group administrators

Write-Output "Local user $Username created"

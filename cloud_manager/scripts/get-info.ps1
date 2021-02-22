param(
  [string]$Name
)

# Write-Output "Hello $Name"

Get-LocalUser | Select-Object -ExpandProperty Name

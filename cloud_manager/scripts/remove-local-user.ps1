param(
  [string]$Username
)

Remove-LocalUser -Name $Username

Write-Output "Local user $Username removed"

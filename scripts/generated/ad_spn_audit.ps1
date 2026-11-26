<#
.SYNOPSIS
    Read-only Active Directory audit for Kerberoastable accounts (SPN set).
.NOTES
    Generated via prompt AD3 (qwen2.5:3b) from ai-AD3-spn-ps1.md.
    Human L2 QA: trimmed repetitive checklist comments; verified cmdlet syntax via PowerShell AST parser.
#>
[CmdletBinding()]
param(
    [string]$Domain = "LAB.LOCAL"
)

Import-Module ActiveDirectory -ErrorAction Stop

$usersWithSPNs = Get-ADUser `
    -Filter { Enabled -eq $true -and ServicePrincipalName -ne $null } `
    -Server $Domain `
    -Properties ServicePrincipalName, MemberOf, PasswordLastSet `
    -ErrorAction Stop

foreach ($user in $usersWithSPNs) {
    [PSCustomObject]@{
        SamAccountName       = $user.SamAccountName
        DistinguishedName    = $user.DistinguishedName
        ServicePrincipalName = ($user.ServicePrincipalName -join "; ")
        PasswordLastSet      = $user.PasswordLastSet
    }
}

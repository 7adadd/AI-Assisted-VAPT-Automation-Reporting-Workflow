<#
.SYNOPSIS
    Read-only Active Directory audit for dangerous delegated ACL rights.
.NOTES
    Generated via prompt AD3 (qwen2.5:3b) from ai-AD3-acl-ps1.md.
    Human L2 QA fix: raw AI script only iterated group members instead of inspecting AD:\ ACLs
    (Get-Acl) for GenericAll/WriteDacl/WriteOwner/ExtendedRight; corrected to inspect real ACEs read-only.
#>
[CmdletBinding()]
param(
    [string]$SearchBase = "DC=lab,DC=local"
)

Import-Module ActiveDirectory -ErrorAction Stop

$dangerousRights = @("GenericAll", "WriteDacl", "WriteOwner", "ExtendedRight", "GenericWrite")
$targets = Get-ADObject -SearchBase $SearchBase -Filter * -ErrorAction Stop

foreach ($obj in $targets) {
    $aclPath = "AD:\$($obj.DistinguishedName)"
    $acl = Get-Acl -Path $aclPath -ErrorAction SilentlyContinue
    if (-not $acl) { continue }

    foreach ($ace in $acl.Access) {
        if ($ace.AccessControlType -ne "Allow") { continue }
        $rightStr = $ace.ActiveDirectoryRights.ToString()
        $matched = $dangerousRights | Where-Object { $rightStr -match $_ }
        if ($matched -and $ace.IdentityReference -notmatch "SYSTEM|Domain Admins|Enterprise Admins|Administrators") {
            [PSCustomObject]@{
                Target            = $obj.DistinguishedName
                IdentityReference = $ace.IdentityReference.ToString()
                Rights            = $rightStr
            }
        }
    }
}

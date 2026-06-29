param(
    [Parameter(Mandatory = $false)]
    [string]$Owner,

    [Parameter(Mandatory = $false)]
    [string]$Repo,

    [Parameter(Mandatory = $false)]
    [string[]]$Branches = @("main", "master"),

    [Parameter(Mandatory = $false)]
    [string]$RequiredStatusCheck = "Merge Readiness Gate"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-RepositoryInfo {
    param(
        [string]$InputOwner,
        [string]$InputRepo
    )

    if ($InputOwner -and $InputRepo) {
        return @{
            Owner = $InputOwner
            Repo = $InputRepo
        }
    }

    $origin = git remote get-url origin
    if (-not $origin) {
        throw "Could not resolve git origin remote. Provide -Owner and -Repo explicitly."
    }

    if ($origin -match "github.com[:/](?<owner>[^/]+)/(?<repo>[^/.]+)(\.git)?$") {
        return @{
            Owner = $Matches.owner
            Repo = $Matches.repo
        }
    }

    throw "Origin remote is not a GitHub repository URL. Provide -Owner and -Repo explicitly."
}

function Set-BranchProtection {
    param(
        [string]$TargetOwner,
        [string]$TargetRepo,
        [string]$TargetBranch,
        [string]$StatusCheck
    )

    $payload = @{
        required_status_checks = @{
            strict = $true
            contexts = @($StatusCheck)
        }
        enforce_admins = $true
        required_pull_request_reviews = @{
            dismiss_stale_reviews = $true
            require_code_owner_reviews = $false
            required_approving_review_count = 1
        }
        restrictions = $null
        required_conversation_resolution = $true
        allow_force_pushes = $false
        allow_deletions = $false
    } | ConvertTo-Json -Depth 10 -Compress

    $payload | gh api --method PUT --header "Accept: application/vnd.github+json" "/repos/$TargetOwner/$TargetRepo/branches/$TargetBranch/protection" --input - | Out-Null

    Write-Host "Configured protection for $TargetOwner/$TargetRepo branch '$TargetBranch'."
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is required. Install it from https://cli.github.com/."
}

gh auth status | Out-Null

$resolved = Resolve-RepositoryInfo -InputOwner $Owner -InputRepo $Repo

foreach ($branch in $Branches) {
    try {
        Set-BranchProtection -TargetOwner $resolved.Owner -TargetRepo $resolved.Repo -TargetBranch $branch -StatusCheck $RequiredStatusCheck
    }
    catch {
        Write-Warning "Failed to configure branch '$branch': $($_.Exception.Message)"
    }
}

Write-Host "Branch protection configuration completed."

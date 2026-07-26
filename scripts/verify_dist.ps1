param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
python (Join-Path $Root "scripts/verify_dist.py") --project $Root @Args
exit $LASTEXITCODE

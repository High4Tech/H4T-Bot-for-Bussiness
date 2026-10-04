param(
    [Parameter(Mandatory=$true)][string]$NeueMontrealZip,
    [Parameter(Mandatory=$true)][string]$HelveticaNeueZip
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$appRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$fontTarget = Join-Path $appRoot 'public/assets/fonts/private'
New-Item -ItemType Directory -Path $fontTarget -Force | Out-Null
$bundles = @(
    @{Path=$NeueMontrealZip; Names=@('ppneuemontreal-book.otf','ppneuemontreal-medium.otf','ppneuemontreal-bold.otf')},
    @{Path=$HelveticaNeueZip; Names=@('HelveticaNeueRoman.otf','HelveticaNeueMedium.otf','HelveticaNeueBold.otf')}
)
foreach ($bundle in $bundles) {
    $archive = [System.IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $bundle.Path).Path)
    try {
        foreach ($name in $bundle.Names) {
            $entry = $archive.Entries | Where-Object { $_.Name -ceq $name } | Select-Object -First 1
            if (-not $entry) { throw "Font missing from archive: $name" }
            # Only known font filenames are extracted. ZIP paths are never used as output paths.
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, (Join-Path $fontTarget $name), $true)
        }
    } finally { $archive.Dispose() }
}
Write-Output 'Six local font files installed. Font binaries remain excluded from Git.'

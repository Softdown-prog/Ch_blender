# Local resolution only. No Blender downloads or installation.
function Resolve-CHBlender {
    [CmdletBinding()]
    param([string]$ExplicitExecutable=$env:CH_BLENDER_EXE)
    $ErrorActionPreference='Stop'
    $legacy=Join-Path $env:USERPROFILE '.ch-blender\blender-4.2.3-legacy\blender.exe'
    $official=Join-Path $env:USERPROFILE '.ch-blender\blender-4.2.3-windows-x64\blender.exe'
    if (-not ('CHLegacyCpuFeatures' -as [type])) {
        Add-Type -TypeDefinition 'using System.Runtime.InteropServices; public static class CHLegacyCpuFeatures { [DllImport("kernel32.dll")] public static extern bool IsProcessorFeaturePresent(uint feature); }'
    }
    $modernCpu=[CHLegacyCpuFeatures]::IsProcessorFeaturePresent(38) # Windows SDK PF_SSE4_2_INSTRUCTIONS_AVAILABLE
    $candidates=@()
    if ($ExplicitExecutable) {
        if (-not (Test-Path -LiteralPath $ExplicitExecutable -PathType Leaf)) { throw "CH_BLENDER_EXE does not exist: $ExplicitExecutable" }
        $candidates += $ExplicitExecutable
    }
    $candidates += $legacy
    if ($modernCpu) {
        $candidates += $official
        $pathBlender=Get-Command blender.exe -ErrorAction SilentlyContinue
        if ($pathBlender) { $candidates += $pathBlender.Source }
        $candidates += "$env:ProgramFiles\Blender Foundation\Blender 4.2\blender.exe"
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        $exe=(Resolve-Path -LiteralPath $candidate).Path
        $start=New-Object System.Diagnostics.ProcessStartInfo
        $start.FileName=$exe
        $start.Arguments='--version'
        $start.UseShellExecute=$false
        $start.CreateNoWindow=$true
        $start.RedirectStandardOutput=$true
        $start.RedirectStandardError=$true
        $process=New-Object System.Diagnostics.Process
        $process.StartInfo=$start
        [void]$process.Start()
        $stdout=$process.StandardOutput.ReadToEndAsync()
        $stderr=$process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(30000)) {
            $process.Kill()
            throw "Blender --version timed out: $exe"
        }
        $version=$stdout.Result
        $errorText=$stderr.Result
        $exitCode=$process.ExitCode
        $process.Dispose()
        $line=($version -split '\r?\n' | Select-Object -First 1).Trim()
        if ($exitCode -ne 0 -or $line -notmatch '^Blender 4\.2\.3(?: LTS)?$') {
            if ($ExplicitExecutable -and $candidate -eq $ExplicitExecutable) { throw "CH_BLENDER_EXE must run Blender 4.2.3 LTS successfully: $line ($exitCode) $errorText" }
            Write-Warning "Rejected local Blender: $exe -> $line ($exitCode)"
            continue
        }
        $backend='official_4_2_3'
        $marker=Join-Path (Split-Path -Parent $exe) 'ch-legacy-build.json'
        if (Test-Path -LiteralPath $marker) {
            $identity=Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
            if ($identity.backend -ne 'legacy_cpu_4_2_3' -or $identity.upstreamTag -ne 'v4.2.3') { throw 'Invalid Blender Legacy marker' }
            $backend=$identity.backend
        }
        return [pscustomobject]@{Executable=$exe;VersionLine=$line;VersionText=$version;Backend=$backend;CpuHasSse42=$modernCpu}
    }
    throw "No working Blender 4.2.3 found locally. Build Legacy for this CPU at $legacy or set CH_BLENDER_EXE."
}
param([string]$BuildRoot='C:\CH-Blender-Build')
$ErrorActionPreference='Stop'
$build=Join-Path $BuildRoot 'cpu-probe'
cmake -S $PSScriptRoot -B $build -G 'Visual Studio 17 2022' -A x64 -T host=x64
if ($LASTEXITCODE -ne 0) { throw 'CPU configure failed' }
cmake --build $build --config Release
if ($LASTEXITCODE -ne 0) { throw 'CPU build failed' }
& (Join-Path $build 'Release/cpu_probe.exe')
if ($LASTEXITCODE -ne 0) { throw 'CPUID failed' }

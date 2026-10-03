param(
 [string]$BuildRoot = 'C:\CH-Blender-Build',
 [string]$InstallDir = "$env:USERPROFILE\.ch-blender\blender-4.2.3-legacy",
 [ValidateSet('Prepare','Dependencies','Blender','Validate','All')][string]$Stage = 'All',
 [int]$Jobs = 4
)
$ErrorActionPreference = 'Stop'
$Here = $PSScriptRoot
$Source = Join-Path $BuildRoot 'blender-4.2.3-source'
$Deps = Join-Path $BuildRoot 'deps'
$Harvest = (Join-Path $Deps 'output').Replace('\','/')
$Build = Join-Path $BuildRoot 'build-legacy'
$Logs = Join-Path $BuildRoot 'logs'
New-Item -ItemType Directory -Force -Path $BuildRoot,$Logs | Out-Null
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vsPath = (& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath)
if (-not $vsPath) { throw 'Visual Studio C++ x64 Build Tools required' }
$vcvars = Join-Path $vsPath 'VC\Auxiliary\Build\vcvarsall.bat'
$environment = & cmd.exe /d /c "call `"$vcvars`" x64 >nul && set"
if ($LASTEXITCODE -ne 0) { throw 'vcvarsall failed' }
foreach ($line in $environment) {
 if ($line -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1],$Matches[2],'Process') }
}
$env:PATH = (Join-Path $vsPath 'Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja') + ';' + $env:PATH
$TaskTemp = Join-Path $BuildRoot 'tmp'
New-Item -ItemType Directory -Force -Path $TaskTemp | Out-Null
$env:TEMP = $TaskTemp
$env:TMP = $TaskTemp
$env:PYTHONUTF8 = '1'
$env:_CL_ = '/Od /Ob0 /Oi-'
$env:PERL = Join-Path $Deps 'downloads/perl/perl/bin/perl.exe'
$env:PATH = (Join-Path $Deps 'downloads/perl/perl/bin') + ';' + (Join-Path $Deps 'downloads/nasm-2.13.02') + ';' + $env:PATH
$env:NPY_BLAS_ORDER = ''
$env:NPY_LAPACK_ORDER = ''
$env:NPY_DISABLE_SVML = '1'
$env:CMAKE_BUILD_PARALLEL_LEVEL = '2'
function Run([string]$Exe,[string[]]$Arguments,[string]$LogName) {
 & $Exe @Arguments *> (Join-Path $Logs $LogName)
 if ($LASTEXITCODE -ne 0) { Get-Content (Join-Path $Logs $LogName) -Tail 25; throw "$Exe failed ($LASTEXITCODE): $LogName" }
 Write-Host "Completed: $LogName"
}
if ($Stage -in @('Prepare','All')) {
 Run 'python' @((Join-Path $Here 'prepare_source.py'),$BuildRoot) 'source-prepare.log'
 Run 'cmake' @('-S',$Here,'-B',(Join-Path $BuildRoot 'cpu-probe'),'-G','Visual Studio 17 2022','-A','x64','-T','host=x64') 'cpu-configure.log'
 Run 'cmake' @('--build',(Join-Path $BuildRoot 'cpu-probe'),'--config','Release') 'cpu-build.log'
 $cpuText = & (Join-Path $BuildRoot 'cpu-probe\Release\cpu_probe.exe')
 if ($LASTEXITCODE -ne 0) { throw 'CPUID probe failed' }
 $cpuText | Set-Content -LiteralPath (Join-Path $BuildRoot 'cpu.json') -Encoding utf8
 $cpu = $cpuText | ConvertFrom-Json
 if (-not $cpu.x86_64 -or -not $cpu.sse2) { throw 'x64 with SSE2 is required' }
 Write-Host $cpuText
}
if ($Stage -in @('Dependencies','All')) {
 Run 'python' @((Join-Path $Here 'prepare_tools.py'),$BuildRoot) 'tools-prepare.log'
 Run 'cmake' @('-S',"$Source/build_files/build_environment",'-B',$Deps,'-G','Ninja','-DCH_BLENDER_LEGACY_CPU=ON','-DCMAKE_POLICY_VERSION_MINIMUM=3.5',"-DHARVEST_TARGET=$Harvest",'-DBUILD_MODE=Release',"-DMAKE_THREADS=$Jobs") 'deps-configure.log'
 Run 'cmake' @('--build',$Deps,'--parallel',"$Jobs") 'deps-build.log'
 Run 'cmake' @('--build',$Deps,'--target','Harvest_Release_Results') 'deps-harvest.log'
 Run "$Deps/Release/python/python.exe" @("$Here/dependency_probe.py",$Harvest,"$BuildRoot/logs/dependency-probe.json") 'dependency-probe.log'
}
if ($Stage -in @('Blender','All')) {
 Run 'cmake' @('-S',$Source,'-B',$Build,'-G','Ninja','-C',"$Here/legacy.cmake",'-DCMAKE_POLICY_VERSION_MINIMUM=3.5',"-DLIBDIR=$Harvest",'-DCMAKE_BUILD_TYPE=Release',"-DCMAKE_INSTALL_PREFIX=$InstallDir") 'blender-configure.log'
 Run 'python' @("$Here/audit_flags.py",$Build,$Deps) 'isa-flags.log'
 Run 'cmake' @('--build',$Build,'--parallel',"$Jobs") 'blender-build.log'
 Run 'cmake' @('--install',$Build) 'blender-install.log'
 Run 'python' @("$Here/write_build_manifest.py",$BuildRoot,$InstallDir) 'manifest.log'
}
if ($Stage -in @('Validate','All')) {
 Run 'python' @("$Here/smoke_test.py",'--blender',"$InstallDir/blender.exe",'--output',"$BuildRoot/validation") 'validation.log'
 Run 'python' @("$Here/real_recipe_test.py",'--blender',"$InstallDir/blender.exe") 'real-recipe.log'
 $dumpbin = (Get-Command dumpbin.exe -ErrorAction Stop).Source
 Run 'python' @("$Here/audit_binary.py",'--dumpbin',$dumpbin,'--output',"$BuildRoot/validation/binary-isa.json",$InstallDir) 'binary-isa.log'
}

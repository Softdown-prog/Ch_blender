param([string]$BuildRoot='C:\CH-Blender-Build',[int]$Jobs=2)
$ErrorActionPreference='Stop'
$Here=$PSScriptRoot
$validation=Get-Content "$BuildRoot/validation/validation.json" -Raw|ConvertFrom-Json
if($validation.status -ne 'ok'){throw 'Basic Blender validation must pass first'}
$vswhere="${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vsPath=(& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath)
$vcvars=Join-Path $vsPath 'VC\Auxiliary\Build\vcvarsall.bat'
$environment=& cmd.exe /d /c "call `"$vcvars`" x64 >nul && set"
foreach($line in $environment){if($line -match '^([^=]+)=(.*)$'){[Environment]::SetEnvironmentVariable($Matches[1],$Matches[2],'Process')}}
$env:PATH=(Join-Path $vsPath 'Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja')+';'+$env:PATH
$env:_CL_='/Od /Ob0 /Oi-'
$env:PYTHONUTF8='1'
$env:VSLANG='1033'
function Run([string]$Exe,[string[]]$Arguments,[string]$LogName){& $Exe @Arguments *> "$BuildRoot/logs/$LogName";if($LASTEXITCODE -ne 0){Get-Content "$BuildRoot/logs/$LogName" -Tail 25;throw "$LogName failed ($LASTEXITCODE)"};Write-Host "Completed: $LogName"}
Run 'python' @("$Here/prepare_embree.py",$BuildRoot) 'embree-source.log'
$Source="$BuildRoot/embree-source/embree-4.3.2-blender"
$Build="$BuildRoot/build-embree-sse2"
$Install="$BuildRoot/deps/embree-sse2"
Run 'cmake' @('-S',$Source,'-B',$Build,'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_POLICY_VERSION_MINIMUM=3.5',"-DCMAKE_INSTALL_PREFIX=$Install",'-DEMBREE_MAX_ISA=SSE2','-DEMBREE_SYCL_SUPPORT=OFF','-DEMBREE_ISPC_SUPPORT=OFF','-DEMBREE_TUTORIALS=OFF','-DEMBREE_STATIC_LIB=OFF','-DEMBREE_RAY_MASK=ON','-DEMBREE_FILTER_FUNCTION=ON','-DEMBREE_BACKFACE_CULLING=OFF','-DEMBREE_BACKFACE_CULLING_CURVES=ON','-DEMBREE_BACKFACE_CULLING_SPHERES=ON','-DEMBREE_TASKING_SYSTEM=TBB',"-DTBB_ROOT=$BuildRoot/deps/output/tbb","-DEMBREE_TBB_ROOT=$BuildRoot/deps/output/tbb",'-DCMAKE_CXX_FLAGS_RELEASE=/MD /Od /Ob0 /Oi- /DNDEBUG /bigobj','-DCMAKE_SHARED_LINKER_FLAGS_RELEASE=/MAP') 'embree-configure.log'
Run 'python' @("$Here/audit_flags.py",$Build) 'embree-flags.log'
Run 'cmake' @('--build',$Build,'--parallel',"$Jobs") 'embree-build.log'
Run 'cmake' @('--install',$Build) 'embree-install.log'
Write-Host 'Embree library built in isolation; Blender integration and Phenom render validation still required.'
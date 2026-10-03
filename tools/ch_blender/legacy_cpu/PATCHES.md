# Patches da variante Legacy (base exata v4.2.3)

Todos os patches são aplicados em checkout externo. A ordem está em build-manifest.json.
prepare_source.py registra hashes dos patches e do diff; alterações não registradas interrompem o preparo.
Os patches não mudam version_string, DNA/.blend, câmeras ou receitas.

| Patch | Arquivo upstream / original | Comportamento Legacy e motivo | Risco / teste |
|---|---|---|---|
| 0001 | intern/cycles/util/optimization.h: força SSE4.2 em x64 | CH_BLENDER_LEGACY_CPU impede essa definição; caminhos escalares | Desempenho e arredondamento: render CPU e comparação visual |
| 0002 | build_environment/CMakeLists.txt e receitas; platform_win32.cmake exige .git de libs binárias | Subconjunto de fontes; /Od; JPEG SIMD off; NumPy sem dispatch; OCIO SSE2; libs locais sem .git falso | Falta de libs: configurar, auditar e executar pipeline real |
| 0003 | options.cmake passa flags para ExternalProject | Política mínima CMake 3.5 para CMake 4.x | Configurar todos os projetos filhos |
| 0004 | package_python.cmake usa OUTPUT em add_custom_target | Arquivo gerado passa a ser dependência do alvo Ninja | Python instalado e import numpy |
| 0005 | setup_msys2.cmake tenta MSYS2 20221028 indisponível | Subconjunto nativo usa patch.exe local; download de fonte OIIO incluído | Verificar todas as ferramentas e hashes |
| 0006 | kernel/device/cpu/kernel.cpp força SSE/SSSE3/SSE4.2; device/cpu/device.cpp indexa string vazia | Kernel escalar; consulta de capacidades aceita CPU sem SSE4 | Cycles CPU, capabilities e disassembly |
| 0007 | ambiente Windows define CC com espaço final antes de && | Ambiente VS nativo sem valor CC incorreto | OpenSSL compila com cl real |
| 0008 | subconjunto de dependências sem OpenSubdiv | Preserva OpenSubdiv v3_6_0 para SUBSURF usado nos scripts | Avaliar SUBSURF e render com modifier |
| 0009 | python.cmake e patch adicional para CPython PCbuild/openssl.vcxproj | OpenSSL no-asm no-tests: remove teste auxiliar incompatível com MSVC #warning; runtime preservado | import ssl, zlib e compilação Python; audit DLLs |
| 0010 | platform_win32.cmake presume Boost vc142 e libs debug oficiais | Usa bibliotecas compartilhadas vc143 recompiladas com MSVC 2022 | Configurar, linkar, iniciar Blender e Cycles |
| 0011 | python.cmake e helper de preparacao | Juncoes e patches idempotentes; retoma objetos existentes | Executar Dependencies novamente e importar bpy |
| 0012 | helper de patches CPython | Usa GNU patch para o diff upstream misto que git apply rejeita | Dry-run reverso detecta patch aplicado; build Python |
| 0013 | opencolorio.cmake, helper idempotente e patch de src/OpenColorIO/CMakeLists.txt | Exclui quatro unidades AVX/AVX2 quando as respectivas opcoes estao OFF; upstream ainda lhes passa /arch | Auditar comandos Ninja sem /arch:AVX e render color management no Phenom |
| 0014 | package_python.cmake usa %%d de batch dentro de cmd /C Ninja | Preserva caches .pyc compativeis do Python 3.11.7 e elimina limpeza auxiliar invalida; nenhuma exclusao recursiva | Package_Python, imports NumPy/SSL e bpy |
| 0015 | boost.cmake e libs/atomic/build/Jamfile.v2 | MSVC e vcvarsall explicitamente configurados; Atomic SSE2 sem selecionar SSE4.1; ICU off | Compilar vc143 real, auditar comandos e DLLs, testar Cycles/worker |

O patch de dependência Python está em patches/dependencies/python-openssl-no-tests.patch;
0009 instala cópia dele na árvore externa e integra sua aplicação ao build.

## 0016 — include chrono explicito
Arquivo upstream: intern/cycles/util/profiling.cpp. MSVC 19.44 nao fornece system_clock por includes transitivos de thread. Legacy inclui chrono diretamente, sem alterar logica ou ISA. Risco baixo; testar compilacao de cycles_util e render CPU.

## 0017 — Windows DLL installation respects options
Upstream: source/creator/CMakeLists.txt. Original install unconditionally copied GMP, OpenVDB and MaterialX DLLs even when their features were OFF. Legacy wraps each group in the existing WITH_* option. Risk: missing DLL if an enabled feature is incorrectly configured; enabled groups still fail on missing files. Test: configure/build/install and bpy/Cycles smoke.

## 0018 — Optional Python/media/Vulkan installation
Upstream: source/creator/CMakeLists.txt. Original Windows installation copied MaterialX Python, FFmpeg, sndfile, shaderc, OpenAL and SDL regardless of WITH_* flags. Legacy conditions each group on its existing feature option. No enabled file is silently skipped. Risk: packaging regression; test install, bpy imports, Cycles and real recipe.

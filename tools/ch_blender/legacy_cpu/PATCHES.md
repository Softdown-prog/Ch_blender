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

O patch de dependência Python está em patches/dependencies/python-openssl-no-tests.patch;
0009 instala cópia dele na árvore externa e integra sua aplicação ao build.


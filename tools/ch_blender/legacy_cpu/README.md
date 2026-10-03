# CH Blender Engine 4.2.3 Legacy CPU

Estado atual: em construção, **não validado para produção**. O contrato permanece Blender 4.2.3 LTS.
A primeira build prioriza compatibilidade x64/SSE2 no Phenom II X6 e não inclui Embree, OIDN ou OpenPGL.
Não use este backend como aprovado antes dos testes reais e da auditoria ISA.

## Estrutura

- Fonte externo: `C:\CH-Blender-Build\blender-4.2.3-source`, tag v4.2.3 / commit 0e22e4fcea037eeec1531fdbfc32d3acb88b4bd5.
- Dependências de fonte: `C:\CH-Blender-Build\deps`; saída `deps\output`.
- Build: `C:\CH-Blender-Build\build-legacy`.
- Instalação final: `C:\Users\User\.ch-blender\blender-4.2.3-legacy\blender.exe`.
- Logs e validação fora do repositório: `C:\CH-Blender-Build\logs` e `validation`.

## Ferramentas e execução

Visual Studio 2022 C++ Build Tools x64, Windows SDK, CMake, Ninja (incluído no VS), Git com patch.exe,
Python host e Pillow (`python -m pip install Pillow` se faltar). Perl portátil é baixado e verificado por SHA256.
As bibliotecas são recompiladas pelo subconjunto do build_environment upstream; não se usa o lib/windows_x64 oficial.

```powershell
.\tools\ch_blender\legacy_cpu\verify_cpu.ps1
.\tools\ch_blender\legacy_cpu\build.ps1 -Stage All -Jobs 2
```

Etapas retomáveis: `Prepare`, `Dependencies`, `Blender`, `Validate`.
Para um checkout limpo separado, use `-BuildRoot C:\CH-Blender-Build-Fresh`.
Prepare recusa outros commits e alterações upstream não registradas; não faz reset nem remove código do usuário.

## Baseline

MSVC x64 sem /arch:AVX ou outras extensões: SSE2 é o padrão x64.
`/Od /Ob0 /Oi-` desliga otimização, inlining e substituições intrínsecas automáticas no primeiro build.
`WITH_CPU_CHECK=OFF`, `WITH_CPU_SIMD=OFF` e `WITH_CYCLES_NATIVE_ONLY=OFF`.
Os dois locais do Cycles que habilitam SSE4.2 automaticamente recebem patches para o caminho escalar.
Eigen e outras dependências internas continuam sujeitos à auditoria e aos testes reais.

OpenImageIO 2.5.11.0 usa USE_SIMD=sse2; OpenColorIO 2.3.2 usa somente SSE2.
NumPy é recompilado sem CPU dispatch; JPEG sem SIMD; OpenSSL recompilado com no-asm.
`dependencies.json` fixa versões, arquivos e hashes dos fontes; `legacy.cmake` é a configuração autoritativa.
Libffi 3.4.4 é a DLL do shim CPython: auditoria registrou 5309 instruções sem ISA elevada; ainda exige teste ctypes no runtime.
CRT/UCRT do compilador e Windows são dependências de sistema com dispatch próprio, que devem ser distinguidas das libs recompiladas na auditoria.

## Backend e recursos

A distribuição Legacy recebe `ch-legacy-build.json` ao instalar. O worker usa esse marcador e registra
`legacy_cpu_4_2_3` no relatório; sem marcador, `official_4_2_3`.
O baker desliga denoising somente no Legacy, incluindo overrides de shadow pass.
Presets oficiais, samples e contratos geométricos permanecem intactos.
Headless, bpy, meshes, materiais/nodes, modifiers, SUBSURF/OpenSubdiv, PNG, .blend e compositor CPU são preservados.
FBX/glTF estão nos scripts addons_core upstream; precisam de probes antes de declarar suporte validado.

Desativados nesta configuração: OIDN, OpenPGL/path guiding, Embree, OSL, GPUs de Cycles, USD/Hydra,
MaterialX, OpenXR, áudio, NDOF, OpenVDB, fluid/ocean, Alembic, Collada, Freestyle, tracking/libmv,
internacionalização/Harfbuzz/Fribidi, thumbnailer, GMP/exact Boolean e Quadriflow.
A busca nos scripts não encontrou uso de exact Boolean/volume/fluid/OSL; SUBSURF foi encontrado e mantido.
Só declare indisponibilidade efetiva depois de conferir a configuração final e probes do executável.

## Gates obrigatórios

```powershell
python tools/ch_blender/legacy_cpu/smoke_test.py --blender C:\Users\User\.ch-blender\blender-4.2.3-legacy\blender.exe --output C:\CH-Blender-Build\validation
python tools/ch_blender/legacy_cpu/real_recipe_test.py --blender C:\Users\User\.ch-blender\blender-4.2.3-legacy\blender.exe
```

O primeiro gate exige versão exata, bpy, background, SSL/zlib/ctypes/NumPy, BEVEL/SUBSURF, round-trip FBX/GLB/.blend/OpenEXR, render Cycles CPU 64×64 e PNG RGBA não vazio.
O segundo usa a receita existente `assets/tests/color_mask_smoke.asset.json`, o studio congelado e o worker real:
quatro direções, color/shadow/mask PNGs, câmera CH_CAMERA_V1, footprint 1×1, origem/anchor finita e luzes fixas.
Não cria aprovação artística e não promove assets.

`audit_flags.py` verifica comandos Ninja gerados; configure e execute em ambiente VS com Ninja no PATH.
`audit_binary.py --dumpbin <dumpbin.exe> --output <report.json> <distribuição>` inventaria instruções elevadas.
Disassembly linear não prova reachability: hits em dispatch ou dados exigem revisão explícita, junto dos testes na CPU real.
Nenhum relatório deve alegar auditoria ISA completa só porque encontrou zero flags.

Antes de concluir: testar imports SSL/zlib/ctypes/NumPy, modifiers usados, FBX/glTF se necessários; revisar DLLs e binários;
comparar imagens oficiais existentes sem exigir bit-exact. O runner só deve ser alterado após validação local.

## Embree experimental

Somente após todos os gates básicos: build separada com fonte Embree 4.3.2-blender e EMBREE_MAX_ISA=SSE2,
sem GPU, auditar flags/binário e repetir bpy/Cycles/worker, estabilidade e tempo. Não usar o Embree AVX2 oficial.
Se a experiência não passar, manter Cycles sem Embree.

O manifesto instalado registra compilador efetivo, cache CMake, hashes dos patches e dos binarios; começa como built_unvalidated. Validate executa os renders antes da auditoria binaria e falha com review_required se houver instrucoes elevadas pendentes de revisao.

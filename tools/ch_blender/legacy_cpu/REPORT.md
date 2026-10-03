# Resultado local — CH Blender Engine 4.2.3 Legacy CPU

Executável pronto: `C:\Users\User\.ch-blender\blender-4.2.3-legacy\blender.exe`.
Validado nesta máquina para o pipeline headless descrito abaixo; manifesto e evidências em `legacy-validation` junto ao executável.

| Item | Resultado |
| --- | --- |
| CPU | AMD Phenom II X6 1055T, 6 núcleos; x64/SSE/SSE2/SSE3/SSE4a; sem SSSE3/SSE4.1/SSE4.2/AVX/AVX2/F16C |
| Compilador | Visual Studio 2022 Build Tools, MSVC 19.44.35228.0 x64; SDK 10.0.26100.0; CMake/Ninja |
| Arquitetura | MSVC x64 SSE2 padrão; `/Od /Ob0 /Oi-`; sem `/arch:AVX`, x86-64-v2 ou SIMD automático; WITH_CPU_CHECK/CPU_SIMD=OFF |
| Versão | Primeira linha `Blender 4.2.3 LTS`, exit 0 |
| bpy/background | `bpy.app.version_string`: `4.2.3 LTS`, exit 0; version tuple 4.2.3 |
| Cycles | CPU, 64×64, PNG RGBA válido; BEVEL/SUBSURF e textura PNG passaram |
| Formatos | .blend, FBX, GLB/glTF e OpenEXR round-trips passaram |
| CH Blender real | Worker → receita existente color_mask_smoke → Cycles CPU → quatro vistas, 12 PNGs RGBA válidos |
| Contratos | CH_CAMERA_V1, CH_TYCOON_STUDIO_V1, CH_STYLIZED_PRERENDER_V1 preservados; footprint 1×1, anchor fixo, materiais e luzes validados |
| Preflight/proxy | Probe existente passou: projeção 2:1, quatro vistas enquadradas, modifiers, dimensões e restauração de visibilidade; rejeição de câmera/luzes/footprint incorretos |
| ISA | 6243 comandos sem flags elevadas; 159 PEs revisados por hash/fonte/símbolos; nenhum requisito elevado no caminho efetivamente testado |
| Embree SSE2 | 4.3.2-blender recompilado; triangle probe, Blender e worker passaram; 12 PNGs bit-exact frente ao baseline |
| Tempo ABBA | Sem Embree 17,70 s; Embree 19,53 s em média. Final mantém Embree OFF |
| Testes unitários | 32 selecionados passaram; inventário completo tem 15 inputs ausentes já no HEAD anterior |

Dependências críticas recompiladas: Python 3.11.7, NumPy 1.24.3, OpenSSL 3.1.5 (no-asm),
OpenImageIO 2.5.11.0 (SSE2), OpenColorIO 2.3.2 (somente SSE2), TBB 2020_U3, Boost 1.82,
OpenEXR 3.2.4, Imath 3.1.7, zlib 1.2.13, libpng 1.6.37, libjpeg-turbo 2.1.3 (SIMD OFF)
e OpenSubdiv 3.6.0. Outras bibliotecas e hashes estão em [dependencies.json](dependencies.json).
libffi é a exceção pré-compilada da preparação Windows do Python: hash/ISA revistos e ctypes executado no Phenom.
Nenhum pacote binário oficial de dependências Blender foi aceito sem revisão.

Recursos indisponíveis pela configuração final: interface gráfica/Eevee/OpenGL no headless,
OIDN/denoising, OpenPGL/path guiding, Embree, OSL, CUDA/OptiX/HIP/HIPRT/oneAPI/Metal,
USD/Hydra/MaterialX, OpenXR, áudio/FFmpeg, OpenVDB, fluid/ocean, Alembic/Collada,
NDOF, Freestyle, tracking/libmv, internacionalização, GMP/exact Boolean, Quadriflow,
Potrace, FFTW3 e exportação Grease Pencil SVG/PDF. A lista efetiva completa está no manifesto instalado.
Máscaras canônicas CH_COLOR_MASK_V1 usam emissão Cycles CPU apenas no Legacy; oficial mantém Eevee.
Denoising desativado somente no Legacy; samples oficiais e contratos geométricos não foram alterados.
Scripts especiais que exigem Eevee/UI não foram portados nem declarados compatíveis.

Não havia referência PNG oficial 4.2.3 comparável disponível; não se afirma comparação visual oficial
nem aprovação artística. A auditoria ISA aprova o artefato e caminho testados, não todos os caminhos possíveis.
Opcodes modernos opcionais podem existir em dispatch protegido por CPUID e CRT, conforme [ISA_REVIEW.md](ISA_REVIEW.md).

Fonte oficial externo: tag v4.2.3, commit `0e22e4fcea037eeec1531fdbfc32d3acb88b4bd5`.
18 patches reproduzíveis em 22 arquivos upstream; fonte completo permaneceu fora do CH Blender.
Sem downgrade para 3.6. Workflow Windows ajustado após os testes: CH_BLENDER_EXE → Legacy → oficial em CPU moderna,
com rejeição de versão diferente de 4.2.3; nenhuma transferência pelo GitHub Actions.

Branch local: `ch-blender-423-legacy-cpu`, sem push. Commits iniciais:
`fbed0d4`, `362eff1`, `cec2230`, `91aeac2`; commits finais de validação e runner constam em `git log` e na entrega.
SHA256 final: `312bf1f30c634222c4d5bd19762d47918705756f4a127df630811624d75b389a`.

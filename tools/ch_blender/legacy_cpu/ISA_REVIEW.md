# Revisão ISA do artefato validado

Status: `approved_for_tested_pipeline`, vinculado aos 159 hashes de [isa-review.json](isa-review.json).
Blender SHA256: `312bf1f30c634222c4d5bd19762d47918705756f4a127df630811624d75b389a`.
Escopo: AMD Phenom II X6 1055T, bpy/background, Cycles CPU e receita existente color_mask_smoke com quatro vistas.
Não equivale a verificar todos os recursos/caminhos possíveis do Blender.

6243 comandos gerados passaram sem flags SSE4.x/AVX/AVX2/F16C ou x86-64-v2.
MSVC x64 SSE2 padrão; `_CL_=/Od /Ob0 /Oi-`; CPU_CHECK e CPU_SIMD desligados.
NumPy tem baseline/dispatch vazios; OIIO usa SSE2; OCIO somente SSE2; OpenSSL sem ASM.

Disassembly linear encontrou código moderno opcional e dados. A revisão usa fonte, símbolos/mapas e CPU real:

- MSVC CRT/STL: dispatch por `__isa_available`/`__isa_enabled` antes de AVX2/SSE4.2; fallback SSE2.
- 48 grupos no blender.exe: 33 CRT/STL, 11 tabelas de saltos após retorno, um wmemcmp com flag weak zero,
  um FMA protegido pelo nível ISA e dois LZMA protegidos por CPUID.
- OpenEXR ImfZip seleciona SSE4.1 após CpuId; libdeflate distingue baseline de dispatch CPUID.
- WebP consulta CPUID e OSXSAVE/xgetbv antes dos caminhos elevados.
- Python/elementtree e dois hits de OIIO eram RVAs de tabelas interpretados como instruções, após retorno.
- python3.dll contém forwarders e nenhuma seção de código; não inventariamos instruções inexistentes.
- O libffi fornecido pela preparação do Python não contém opcodes elevados no inventário e ctypes passou.

Evidências completas externas: `C:\CH-Blender-Build\validation`, incluindo mapas e contextos de disassembly.
Evidências portáteis e revisão: `blender-4.2.3-legacy\legacy-validation`.
SSL/zlib/ctypes/NumPy, OCIO Exponent e OIIO PNG round-trip passaram no Phenom.
Blender, bpy, Cycles CPU, FBX/GLB/.blend/OpenEXR, worker real e preflight/proxy passaram sem illegal instruction.

`audit_binary.py --review isa-review.json` recusa diferenças no conjunto de PEs, hashes ou contagens ISA.
Não há aprovação automática por nome de DLL. Novos binários requerem revisão nova e repetição dos testes.
Embree experimental SSE2 passou os testes mas foi mais lento e não integra o artefato aprovado.

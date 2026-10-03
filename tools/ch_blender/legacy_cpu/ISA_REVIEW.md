# Revisao ISA em andamento

Ainda nao e uma aprovacao de producao. Flags limpas e DLLs carregadas nao substituem bpy, Cycles e a receita real.

Evidencias locais:
- Phenom II X6 1055T: SSE2/SSE3/SSE4a, sem SSSE3/SSE4.1/SSE4.2/AVX/AVX2/F16C.
- NumPy 1.24.3 recompilado: __cpu_baseline__=[] e __cpu_dispatch__=[]; dot executou na CPU real.
- Python 3.11.7: SSL 3.1.5, zlib, ctypes e parser XML executaram normalmente.
- OpenColorIO 2.3.2: transformacao Exponent CPU validada; AVX/AVX2/SSE4 desativados e unidades AVX removidas pelo patch 0013.
- Auditoria de comandos apos o patch: 1550 comandos, zero flags elevadas.

Hits preliminares de disassembly devem ser revistos por hash do binario final:
- OpenEXR ImfZip.cpp initializeFuncs seleciona reconstruct_sse41 somente se CpuId.sse4_1; ImfSystemSpecific.cpp consulta o CPUID.
- libdeflate lib/x86/cpu_features.h distingue HAVE_*_NATIVE de dispatch. Sem macros __AVX__/__AVX2__, adler32_impl.h e decompress_impl.h exigem features de CPUID para AVX2/BMI2.
- MSVC 14.44 CRT crt/src/x64/memcpy.asm compara __isa_available antes do caminho AVX e tem NoAVX/SSE; STL vector_algorithms.cpp usa _Use_avx2()/_Use_sse42() antes das rotinas correspondentes.
- Disassembly linear de _elementtree.pyd encontrou vpshufb em VA 0x18001078c depois de ret e dentro de dados de uma jump table; python311.dll encontrou vmovupd em VA 0x180102658 tambem entre RVAs de jump table, apos ret/nop. Esses dados nao devem ser declarados codigo executado.
- python3.dll e uma DLL de forwarders sem secao executavel; nao exige decodificar instrucoes inexistentes.
- UCRT/CRT de sistema podem conter caminhos opcionais; nao declarar compatibilidade apenas por nao encontrar opcodes.

Pendente: hashes e revisao de todos os binarios instalados, testes Blender e render real, limites do suporte comprovado.

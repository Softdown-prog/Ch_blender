"""Execute source-built Python and color dependencies on the actual host CPU."""
import argparse,ctypes,json,os,ssl,sys,zlib
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('harvest',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    assert sys.version_info[:3]==(3,11,7),sys.version
    root=a.harvest.resolve();handles=[];loaded=[]
    folders=list(root.glob('*/bin'))+list(root.glob('*/lib'))
    for folder in folders:handles.append(os.add_dll_directory(str(folder)))
    for folder in folders:
        for dll in folder.glob('*.dll'):
            ctypes.WinDLL(str(dll));loaded.append(str(dll.relative_to(root)))
    import numpy as np
    from numpy.core import _multiarray_umath as native
    assert not native.__cpu_dispatch__ and not native.__cpu_baseline__
    assert int(np.dot(np.arange(5),np.arange(5)))==30
    assert zlib.decompress(zlib.compress(b'legacy'))==b'legacy'
    sys.path.insert(0,str(root/'opencolorio/lib/site-packages'))
    import PyOpenColorIO as ocio
    assert ocio.__version__=='2.3.2'
    processor=ocio.Config.CreateRaw().getProcessor(ocio.ExponentTransform(value=[2.,2.,2.,1.])).getDefaultCPUProcessor()
    color=processor.applyRGBA([0.25,0.5,1.,1.])
    assert max(abs(actual-expected) for actual,expected in zip(color,[0.0625,0.25,1.,1.]))<0.001
    sys.path.insert(0,str(root/'OpenImageIO/lib/python3.11/site-packages'))
    import OpenImageIO as oiio
    assert oiio.VERSION_STRING=='2.5.11.0',oiio.VERSION_STRING
    png=a.output.with_suffix('.png')
    output=oiio.ImageOutput.create(str(png)); assert output
    assert output.open(str(png),oiio.ImageSpec(2,2,4,oiio.UINT8))
    pixels=np.full((2,2,4),[48,96,192,255],dtype=np.uint8)
    assert output.write_image(pixels),output.geterror()
    assert output.close()
    image=oiio.ImageInput.open(str(png)); assert image
    decoded=image.read_image(format=oiio.UINT8)
    assert decoded.shape==(2,2,4) and np.array_equal(decoded,pixels)
    assert image.close()
    report={'openImageIO':oiio.VERSION_STRING,'pngRoundTrip':True,'status':'ok','python':sys.version,'openssl':ssl.OPENSSL_VERSION,'numpy':np.__version__,'numpyBaseline':native.__cpu_baseline__,'numpyDispatch':native.__cpu_dispatch__,'openColorIO':ocio.__version__,'colorTransform':color,'loadedLibraries':loaded,'isaAuditComplete':False}
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

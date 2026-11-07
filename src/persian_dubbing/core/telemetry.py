import shutil, subprocess
import psutil

def snapshot():
    mem=psutil.virtual_memory()
    result={'cpu_percent':psutil.cpu_percent(),'ram_used_gb':round(mem.used/1024**3,2),
            'ram_total_gb':round(mem.total/1024**3,2)}
    if shutil.which('nvidia-smi'):
        try:
            out=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.total,utilization.gpu',
                                         '--format=csv,noheader,nounits'],text=True,timeout=2,
                                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            used,total,util=map(int,out.splitlines()[0].split(','))
            result.update(vram_used_mb=used,vram_total_mb=total,gpu_percent=util)
        except (subprocess.SubprocessError,ValueError,OSError): pass
    return result

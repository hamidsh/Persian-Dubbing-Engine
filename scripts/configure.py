import sys
from pathlib import Path
from persian_dubbing.core.config import Config
path=Path('config.local.json')
config=Config.load(path) if path.exists() else Config()
name=sys.argv[1]
if name not in ('moss','seed','diarization'): raise ValueError('Unknown runtime')
setattr(config,name+'_python',str(Path(sys.argv[2]).resolve()))
if len(sys.argv)>3:setattr(config,name+'_repo',str(Path(sys.argv[3]).resolve()))
config.save(path)
print('Updated',path)

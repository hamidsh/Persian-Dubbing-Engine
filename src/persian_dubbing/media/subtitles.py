import re
from pathlib import Path
from persian_dubbing.core.types import Segment

STAMP = r'(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})'

def seconds(groups):
    h,m,s,ms=map(int,groups)
    if m>=60 or s>=60: raise ValueError('Invalid SRT timestamp')
    return h*3600+m*60+s+ms/1000


def import_srt(path, persian=False):
    text=Path(path).read_text(encoding='utf-8-sig').replace('\r\n','\n')
    results=[]
    for block in re.split(r'\n\s*\n',text.strip()):
        lines=block.splitlines()
        index=next((i for i,l in enumerate(lines) if '-->' in l),None)
        if index is None: raise ValueError('Invalid SRT block')
        match=re.fullmatch(STAMP+r'\s*-->\s*'+STAMP+r'\s*',lines[index])
        if not match: raise ValueError('Invalid SRT timing')
        value=' '.join(lines[index+1:]).strip()
        speaker='speaker_01'
        label=re.match(r'^\[([^]]+)\]\s*(.*)',value)
        if label: speaker,value=label.groups()
        s=Segment(f's{len(results)+1:05d}',seconds(match.groups()[:4]),seconds(match.groups()[4:]),
                  source='' if persian else value, translation=value if persian else '',speaker=speaker)
        results.append(s.validate())
    return results


def timestamp(value):
    ms=round(value*1000); seconds,ms=divmod(ms,1000); minutes,seconds=divmod(seconds,60);hours,minutes=divmod(minutes,60)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'


def export_srt(segments,path):
    text='\n\n'.join(f'{i}\n{timestamp(s.start)} --> {timestamp(s.end)}\n{s.translation}' for i,s in enumerate(segments,1))+'\n'
    Path(path).write_text(text,encoding='utf-8-sig')

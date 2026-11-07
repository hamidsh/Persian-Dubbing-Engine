"""Deadline ordering and explicit buffering policy; never swaps voices."""
from dataclasses import dataclass
import heapq

@dataclass
class PlaybackGate:
    target: float = 10
    def should_pause(self,position,ready_until,total):
        return position < total and ready_until < min(total,position+self.target)

class DeadlineQueue:
    def __init__(self): self._heap=[];self._serial=0
    def push(self,deadline,item):
        heapq.heappush(self._heap,(deadline,self._serial,item));self._serial+=1
    def pop(self): return heapq.heappop(self._heap)[2]
    def __len__(self): return len(self._heap)


def require_vram(config):
    from persian_dubbing.core.telemetry import snapshot
    state=snapshot()
    if 'vram_total_mb' in state and state['vram_total_mb']-state['vram_used_mb']<config.vram_reserve_mb:
        raise RuntimeError('Insufficient free VRAM reserve. Stop other GPU jobs; no automatic voice fallback.')
    return state

import json,threading
from http.server import BaseHTTPRequestHandler,HTTPServer
from persian_dubbing.translation.llama import translate
from persian_dubbing.core.config import Config
from persian_dubbing.core.types import Segment

def test_actual_http_translation_contract():
    captured=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));captured.append(body)
            data=json.dumps({'choices':[{'message':{'content':json.dumps({'translation':'سلام، خوبی؟','emotion':'question','review':False})}}]}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)
    server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        cfg=Config(translator_url=f'http://127.0.0.1:{server.server_port}/v1/chat/completions')
        segment=translate(Segment('x',0,2,source='Hello, how are you?'),['Before'],['After'],cfg)
        assert segment.translation=='سلام، خوبی؟' and segment.emotion=='question'
        payload=json.loads(captured[0]['messages'][1]['content']);assert payload['following']==['After'] and payload['duration_seconds']==2
    finally:server.shutdown();server.server_close();thread.join()

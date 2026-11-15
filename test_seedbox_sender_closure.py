"""Installed-only frozen sender, invented transport; no host or provider access."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from automation.seedbox_package import build

class ClosureTests(unittest.TestCase):
 def test_installed_frozen_edit_and_failure_phases(self):
  with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
   root=Path(tmp);runtime=root/'runtime';runtime.mkdir(mode=0o700);build(Path.cwd(),runtime)
   actor={name:Path(name).read_text() for name in ('movie_intel_service.py','retry_telegram.py','deploy/run.py')}
   fixture=root/'actor.json';fixture.write_text(json.dumps(actor))
   script=r'''
import sys,json,io,importlib.util,socket
sys.path.insert(0,sys.argv[1])
assert importlib.util.find_spec('retry_telegram') is None
from automation import reviewed_telegram_UNISSUED as module
socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError('real network'))
actor=json.load(open(sys.argv[2]));stages=[];calls=[]
class Response(io.BytesIO):
 status=200
payload=b'{"ok":true,"result":{}}'
def http(request,timeout):
 assert timeout==15
 calls.append(json.loads(request.data))
 return Response(payload)
module.urlopen=http
edit=module.sender(actor,b'TELEGRAM_BOT_TOKEN=INVENTED\nTELEGRAM_CHAT_ID=123\n',observe=stages.append)
edit([dict(chat_id=123,message_id=17,kind='text')],dict(text='Invented report',token=None))
assert len(calls)==1 and calls[0]['text']=='Invented report'
assert stages==['transport_started','response_received','response_accepted','receipt_started','receipt_returned'],stages
assert 'retry_telegram' not in sys.modules
payload=b'{"ok":false}'
stages.clear()
try:edit([dict(chat_id=123,message_id=17,kind='text')],dict(text='Invented',token=None))
except RuntimeError:pass
else:raise AssertionError('accepted rejection')
assert stages==['transport_started','response_received','response_rejected'],stages
# Exact frozen hook raises after successful JSON: never invent a receipt.
actor['retry_telegram.py']='def receipt(method,body,response):\n raise ModuleNotFoundError("INVENTED_PRIVATE_TEXT")\n'
payload=b'{"ok":true}';stages.clear()
edit=module.sender(actor,b'TELEGRAM_BOT_TOKEN=INVENTED\nTELEGRAM_CHAT_ID=123\n',observe=stages.append)
try:edit([dict(chat_id=123,message_id=17,kind='caption')],dict(text='Invented',token=None))
except ModuleNotFoundError:pass
else:raise AssertionError('masked receipt failure')
assert stages[-1]=='receipt_started'
actor['retry_telegram.py']=''
try:module.sender(actor,b'TELEGRAM_BOT_TOKEN=INVENTED\nTELEGRAM_CHAT_ID=123\n')
except ValueError as error:assert str(error)=='selected_functions'
else:raise AssertionError('missing frozen receipt accepted')
assert len(calls)==3
print('installed frozen sender and refusal phases passed')
'''
   result=subprocess.run([sys.executable,'-I','-S','-B','-c',script,str(runtime),str(fixture)],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
   self.assertIn('refusal phases passed',result.stdout)

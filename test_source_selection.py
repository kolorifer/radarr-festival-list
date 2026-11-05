"""Two synthetic selections on real local SQLite; no operational source access."""
import copy,json,socket,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator import source_case as core, source_observer as observer, source_output as output
from ai_movie_investigator.source_selector import pair, validate_artifact
from ai_movie_investigator.contracts import encoded, Refusal

T=1700000000.0
class SelectionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.writer=sqlite3.connect(self.root/'collector.db');self.addCleanup(self.writer.close)
  self.writer.executescript('''
   create table selection_current(case_key TEXT PRIMARY KEY,version TEXT,release TEXT,observed REAL);
   create table selection_history(version TEXT PRIMARY KEY,case_key TEXT,route TEXT,correlation TEXT,evidence TEXT,material TEXT);
   create table selection_events(id TEXT PRIMARY KEY,release TEXT,evidence TEXT,observed REAL,received REAL,outcome TEXT);
   create table evidence(id TEXT PRIMARY KEY,release TEXT,metadata TEXT);
   create table deliveries(channel TEXT,event_id TEXT,signature TEXT,evidence TEXT,reason TEXT,source_time REAL,received REAL);
   create table conflicts(channel TEXT,event_id TEXT,signature TEXT);
   create table selection_reviews(case_key TEXT,event TEXT,delivery INTEGER,id TEXT,reviewed REAL,imdb TEXT,tmdb INTEGER,year INTEGER);
  ''')
  self.writer.execute('pragma journal_mode=wal');self.writer.execute('pragma wal_autocheckpoint=0')
  self.spool=sqlite3.connect(self.root/'observer.db');self.addCleanup(self.spool.close)
  self.spool.execute('create table pending(id TEXT PRIMARY KEY,body TEXT NOT NULL,created REAL NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,due REAL NOT NULL)')
  self.selectors=[];self.events=[];self.materials=[]
  for index,title in enumerate(("Synthetic O'Connor Film",'Другой синтетический фильм')):
   release=('a' if index==0 else 'b')*64;case='outcome-'+release
   metadata=dict(title=title,year=1998,imdb=None,tmdb=None,name='PRIVATE_DO_NOT_EXPORT')
   outcome=dict(status='needs_review',category='other',reason='title_conflict',asserted_imdb=None,asserted_tmdb=None)
   evidence=core.digest([release,metadata]);event=core.digest([release,evidence,T,outcome]);event_uuid=f'00000000-0000-4000-8000-00000000000{index+1}'
   material=dict(metadata=metadata,outcome=outcome,route='eligible',underlying_route='eligible',correlation='strong_source_id');version=core.digest([case,material])
   self.writer.execute('insert into evidence values (?,?,?)',(evidence,release,json.dumps(metadata)))
   self.writer.execute('insert into selection_current values (?,?,?,?)',(case,version,release,T))
   self.writer.execute('insert into selection_history values (?,?,?,?,?,?)',(version,case,'eligible','strong_source_id',evidence,json.dumps(material)))
   self.writer.execute('insert into selection_events values (?,?,?,?,?,?)',(event,release,evidence,T,T+1,json.dumps(outcome)))
   signature=core.digest(dict(event_id=event_uuid,release=release,metadata=metadata,outcome=outcome))
   self.writer.execute('insert into deliveries values (?,?,?,?,?,?,?)',('outcome',event_uuid,signature,evidence,None,T,T+1))
   self.spool.execute('insert into pending values (?,?,?,0,?)',(event_uuid,'PRIVATE_BODY',T,T))
   self.selectors.append(dict(case_id=case,version=version,title=title));self.events.append(event);self.materials.append(material)
  self.writer.commit();self.spool.commit()
  self.net=patch.object(socket,'socket',side_effect=AssertionError('network forbidden'));self.net.start();self.addCleanup(self.net.stop)
 def read(self,selector,after_observer=None):
  db=sqlite3.connect((self.root/'collector.db').as_uri()+'?mode=ro',uri=True,isolation_level=None)
  def probe(event):
   spool=sqlite3.connect((self.root/'observer.db').as_uri()+'?mode=ro',uri=True,isolation_level=None)
   try:r=observer.probe(spool,event)
   finally:spool.close()
   self.assertEqual(r['status'],'ok')
   if after_observer:after_observer()
   return r['pending'],r['observed_at']
  try:return core.collect(db,probe,selector)
  finally:db.close()
 def test_two_caller_selected_cases_are_distinct_and_minimized(self):
  for i,s in enumerate(self.selectors):
   r=self.read(s);self.assertEqual(r['status'],'ok');output.validate(r,r['event_uuid'],s)
   self.assertEqual(r['case_id'],s['case_id']);self.assertEqual(r['facts']['title'],s['title'])
   self.assertEqual(r['outcome_delivery_rowid'],i+1);self.assertEqual(r['decision_history'],'incomplete_unknown')
   self.assertNotIn('PRIVATE',json.dumps(r));self.assertNotIn(self.selectors[1-i]['title'],json.dumps(r))
   envelope=dict(status='completed',case=s['case_id'],version=s['version'],source_file_size_bound=33554432,result=r,observer_journal_mode='delete')
   validate_artifact(encoded(envelope),s)
   with self.assertRaises(Refusal):validate_artifact(encoded(envelope),self.selectors[1-i])
 def test_bad_selector_stale_version_and_title_mismatch_refuse(self):
  for key,bad in [('case_id',"' OR 1=1 --"),('version','unknown'),('title','https://private.invalid/key')]:
   s=dict(self.selectors[0]);s[key]=bad;self.assertEqual(self.read(s),dict(status='refused',code='selection_invalid'))
  s=dict(self.selectors[0],version='e'*64);self.assertEqual(self.read(s),dict(status='refused',code='version_changed'))
  s=dict(self.selectors[0],title='Wrong title');self.assertEqual(self.read(s),dict(status='refused',code='disclosure_mismatch'))
  s=dict(self.selectors[0],case_id='outcome-'+'c'*64);self.assertEqual(self.read(s),dict(status='refused',code='case_missing'))
 def test_post_observer_change_refuses(self):
  def mutate():
   self.writer.execute('update selection_current set version=? where case_key=?',('e'*64,self.selectors[0]['case_id']));self.writer.commit()
  self.assertEqual(self.read(self.selectors[0],mutate),dict(status='refused',code='case_changed'))
 def test_ambiguous_delivery_refuses(self):
  row=self.writer.execute('select * from deliveries where rowid=1').fetchone();self.writer.execute('insert into deliveries values (?,?,?,?,?,?,?)',row);self.writer.commit()
  self.assertEqual(self.read(self.selectors[0]),dict(status='refused',code='delivery_ambiguous'))
 def test_current_review_never_transfers_approval(self):
  s=self.selectors[0];material=copy.deepcopy(self.materials[0]);event=self.events[0];material['occurrence']=core.digest([event,1]);version=core.digest([s['case_id'],material])
  self.writer.execute('update selection_history set version=?,material=? where case_key=?',(version,json.dumps(material),s['case_id']))
  self.writer.execute('update selection_current set version=? where case_key=?',(version,s['case_id']))
  self.writer.execute('insert into selection_reviews values (?,?,?,?,?,?,?,?)',(s['case_id'],event,1,core.digest([s['case_id'],event,1]),T+2,'tt12345678',123,1998));self.writer.commit()
  self.assertEqual(self.read(dict(s,version=version)),dict(status='refused',code='already_reviewed'))
 def test_sql_literals_are_unchanged_and_selector_is_bound_data(self):
  # SQL injection-like case IDs fail selector validation before any SQL lookup.
  s=dict(self.selectors[0],case_id="outcome-"+'a'*64+"' --")
  self.assertEqual(self.read(s),dict(status='refused',code='selection_invalid'))

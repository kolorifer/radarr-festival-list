"""At most three fresh confined handoffs per daily scan; no provider requests here."""
import subprocess
import sys
import time

COMMAND=[sys.executable,'-I','-B','-c','import sys; sys.path.insert(0,"."); import identity_research_handoff; sys.exit(identity_research_handoff.main())']


def main():
    for attempt in range(3):
        try:
            result=subprocess.run(COMMAND,timeout=15,check=False,close_fds=True)
            if result.returncode==0:return 0
        except subprocess.TimeoutExpired:
            print('handoff stopped_safe stage=process reason=timeout',flush=True)
        if attempt<2:time.sleep(5)
    print('handoff attempts_exhausted count=3',flush=True)
    return 1


if __name__=='__main__':raise SystemExit(main())

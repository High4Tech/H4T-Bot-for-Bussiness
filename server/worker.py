"""Single bounded local ingestion worker. Run separately from the API."""
from __future__ import annotations
import argparse
from pathlib import Path
import time
from server.database import Database
from server.knowledge import next_job, process_job

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--once',action='store_true',help='Process one queued job and exit')
    args=parser.parse_args()
    database=Database()
    lock_path=Path(__file__).resolve().parent.parent/'.local/ingestion-worker.lock'
    lock_path.parent.mkdir(exist_ok=True)
    with lock_path.open('a+b') as lock:
        try:
            import msvcrt
            lock.seek(0)
            if lock.read(1)==b'': lock.write(b'0');lock.flush()
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            raise SystemExit('An ingestion worker is already running.')
        while True:
            job=next_job(database)
            if job:
                status=process_job(database,job)
                print(f"source={job['source_id'][:8]} version={job['version']} status={status}",flush=True)
            elif args.once: break
            if args.once: break
            time.sleep(2 if not job else .25)

if __name__=='__main__': main()

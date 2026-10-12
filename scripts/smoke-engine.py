"""Local-only engine smoke test with synthetic business knowledge."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import ai, knowledge
from server.database import APP_ROOT, Database


def main() -> None:
    with tempfile.TemporaryDirectory(dir=APP_ROOT / '.local') as folder:
        database = Database(Path(folder) / 'smoke.sqlite3')
        now = time.time()
        content = b'Cedar builds websites for small businesses. Maintenance starts at USD 49 per month.'
        key = 'fixture.txt'
        (database.upload_root / key).write_bytes(content)
        with database.connect(write=True) as conn:
            for company in ('cedar', 'other'):
                conn.execute(
                    'INSERT INTO companies(id,name,bot_id,appearance,created) VALUES(?,?,?,?,?)',
                    (company, company, company + '-bot', '{}', now),
                )
            conn.execute(
                'INSERT INTO knowledge_sources(id,company_id,name,kind,status,created,updated) VALUES(?,?,?,?,?,?,?)',
                ('fixture-source', 'cedar', 'Fixture.txt', 'File', 'Demo published', now, now),
            )
            conn.execute(
                'INSERT INTO source_versions(source_id,company_id,version,status,file_key,sha256,bytes,created) VALUES(?,?,?,?,?,?,?,?)',
                ('fixture-source', 'cedar', 1, 'Demo published', key, hashlib.sha256(content).hexdigest(), len(content), now),
            )
            conn.execute(
                'INSERT INTO ingestion_jobs(id,company_id,source_id,version,status,created,updated) VALUES(?,?,?,?,?,?,?)',
                ('fixture-job', 'cedar', 'fixture-source', 1, 'queued', now, now),
            )

        job = {'id': 'fixture-job', 'company_id': 'cedar', 'source_id': 'fixture-source', 'version': 1}
        if knowledge.process_job(database, job) != 'ready':
            raise RuntimeError('The synthetic knowledge job did not become ready')
        question = 'What services do you offer?'
        evidence = knowledge.search(database, 'cedar', question)
        other_evidence = knowledge.search(database, 'other', question)
        raw_outputs = []
        original_ollama = ai._ollama
        def captured_ollama(messages):
            result = original_ollama(messages)
            raw_outputs.append(result[0])
            return result
        ai._ollama = captured_ollama
        supported = ai.answer(question, evidence, 'Cedar')
        missing_question = 'Do you build mobile apps?'
        missing = ai.answer(missing_question, knowledge.search(database, 'cedar', missing_question), 'Cedar')
        price_question = 'How much does website building cost?'
        price = ai.answer(price_question, knowledge.search(database, 'cedar', price_question), 'Cedar')
        outcome = {
            'ingestion': 'ready',
            'retrievedPassages': len(evidence),
            'otherTenantPassages': len(other_evidence),
            'supported': supported,
            'unsupported': missing,
            'unpricedService': price,
        }
        print(json.dumps(outcome, indent=2))
        if not evidence or other_evidence or not supported['citations'] or missing['citations'] or price['citations'] or '49' in supported['text']:
            print('Raw local model outputs:', json.dumps(raw_outputs, indent=2))
            raise RuntimeError('Retrieval, tenant isolation, or answer grounding failed')


if __name__ == '__main__':
    main()

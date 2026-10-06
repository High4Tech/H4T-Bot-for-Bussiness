"""Bounded, tenant-scoped local knowledge ingestion and semantic retrieval."""
from __future__ import annotations
import csv
from difflib import SequenceMatcher
from functools import lru_cache
import hashlib
import io
import ipaddress
import json
from pathlib import Path
import re
import secrets
import socket
import time
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader

MODEL_DIR = Path(__file__).resolve().parent.parent / '.local/models/all-MiniLM-L6-v2'
MAX_SOURCE_BYTES = 10 * 1024 * 1024
MAX_TEXT = 60000
MAX_CHUNKS = 100
MAX_COMPANY_CHUNKS = 5000

class KnowledgeError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)

@lru_cache(maxsize=1)
def embedder():
    if not (MODEL_DIR / 'modules.json').exists():
        raise KnowledgeError('embedding_model_missing')
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(str(MODEL_DIR), device='cpu', local_files_only=True)

def encode(texts: list[str]) -> list[list[float]]:
    values = embedder().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [[round(float(x), 6) for x in row] for row in values]

def _public_host(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise KnowledgeError('invalid_website_url')
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise KnowledgeError('website_dns_failed') from exc
    if not addresses or any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
        raise KnowledgeError('website_not_public')

def fetch_website(url: str) -> str:
    _public_host(url)
    try:
        with httpx.Client(timeout=httpx.Timeout(12.0), follow_redirects=False, trust_env=False) as client:
            with client.stream('GET', url, headers={'User-Agent': 'H4TBotLocalKnowledge/0.1', 'Accept': 'text/html,text/plain'}) as response:
                if response.is_redirect: raise KnowledgeError('website_redirect_not_supported')
                response.raise_for_status()
                kind = response.headers.get('content-type', '').lower()
                if not ('text/html' in kind or 'text/plain' in kind): raise KnowledgeError('website_not_text')
                raw = bytearray()
                for part in response.iter_bytes():
                    raw.extend(part)
                    if len(raw) > 1024 * 1024: raise KnowledgeError('website_too_large')
                text = raw.decode(response.encoding or 'utf-8', errors='replace')
    except (httpx.HTTPError, UnicodeError) as exc:
        raise KnowledgeError('website_fetch_failed') from exc
    if 'text/html' in kind:
        soup = BeautifulSoup(text, 'html.parser')
        for item in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript']): item.decompose()
        text = soup.get_text('\n', strip=True)
    return text[:MAX_TEXT]

def extract_file(data: bytes, name: str) -> str:
    if len(data) > MAX_SOURCE_BYTES: raise KnowledgeError('file_too_large')
    suffix = Path(name).suffix.lower()
    try:
        if suffix == '.txt': text = data.decode('utf-8-sig')
        elif suffix == '.pdf':
            reader = PdfReader(io.BytesIO(data))
            if len(reader.pages) > 50: raise KnowledgeError('too_many_pdf_pages')
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        elif suffix == '.docx': text = '\n'.join(paragraph.text for paragraph in Document(io.BytesIO(data)).paragraphs)
        elif suffix == '.csv':
            rows = csv.reader(io.StringIO(data.decode('utf-8-sig')))
            text = '\n'.join(' | '.join(cell[:500] for cell in row[:25]) for _, row in zip(range(1000), rows))
        else: raise KnowledgeError('unsupported_file_type')
    except KnowledgeError: raise
    except Exception as exc: raise KnowledgeError('file_extract_failed') from exc
    return text[:MAX_TEXT]

def chunks(text: str) -> list[str]:
    text = re.sub(r'[\t\r]+', ' ', text)
    parts = [re.sub(r' +', ' ', line).strip() for line in text.split('\n')]
    expanded = []
    for part in (part for part in parts if part):
        while len(part) > 900:
            split = part.rfind('. ', 350, 900)
            if split < 350: split = 900
            expanded.append(part[:split].strip())
            part = part[split:].strip()
        if part: expanded.append(part)
    output, current = [], ''
    for part in expanded:
        if len(current) + len(part) + 1 > 900 and current:
            output.append(current)
            current = current[-120:] + '\n' + part
        else: current = (current + '\n' + part).strip()
        if len(output) >= MAX_CHUNKS: break
    if current and len(output) < MAX_CHUNKS: output.append(current)
    if not output: raise KnowledgeError('no_readable_text')
    return output

def next_job(database):
    with database.connect(plane='worker') as conn:
        row = conn.execute("SELECT id,company_id,source_id,version FROM ingestion_jobs WHERE status='queued' OR (status='running' AND updated<?) ORDER BY created,id LIMIT 1",(time.time()-180,)).fetchone()
    return dict(row) if row else None

def process_job(database, job: dict, vectorize=encode):
    company, source_id, version, job_id = job['company_id'], job['source_id'], job['version'], job['id']
    with database.connect(company=company, write=True) as conn:
        row = conn.execute(database.locked('SELECT status,updated FROM ingestion_jobs WHERE id=? AND company_id=?'), (job_id, company)).fetchone()
        if not row or not (row['status']=='queued' or (row['status']=='running' and row['updated']<time.time()-180)): return 'skipped'
        conn.execute("UPDATE ingestion_jobs SET status='running',updated=?,attempts=attempts+1,error='' WHERE id=? AND company_id=?", (time.time(),job_id,company))
    try:
        with database.connect(company=company) as conn:
            source = conn.execute('SELECT k.name,k.kind,k.source_url,k.status,k.version,k.deleted_at,v.file_key,v.sha256 FROM knowledge_sources k JOIN source_versions v ON v.source_id=k.id AND v.company_id=k.company_id AND v.version=? WHERE k.id=? AND k.company_id=?',(version,source_id,company)).fetchone()
        if not source or source['version'] != version or source['deleted_at'] is not None or source['status'] != 'Demo published':
            result = 'obsolete'
        else:
            if source['kind'] == 'Website': text = fetch_website(source['source_url'])
            else:
                path = (database.upload_root / source['file_key']).resolve()
                if not path.is_relative_to(database.upload_root.resolve()) or not path.is_file(): raise KnowledgeError('file_missing')
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != source['sha256']: raise KnowledgeError('file_integrity_failed')
                text = extract_file(data, source['name'])
            segments = chunks(text)
            vectors = vectorize(segments)
            if len(vectors) != len(segments) or any(len(vector) != 384 for vector in vectors): raise KnowledgeError('embedding_dimension_error')
            with database.connect(company=company,write=True) as conn:
                latest = conn.execute(database.locked('SELECT status,version,deleted_at FROM knowledge_sources WHERE id=? AND company_id=?'),(source_id,company)).fetchone()
                if latest['version'] != version or latest['deleted_at'] is not None or latest['status'] != 'Demo published': result = 'obsolete'
                else:
                    total = conn.execute('SELECT COUNT(*) AS n FROM knowledge_chunks WHERE company_id=?',(company,)).fetchone()['n']
                    existing = conn.execute('SELECT COUNT(*) AS n FROM knowledge_chunks WHERE company_id=? AND source_id=?',(company,source_id)).fetchone()['n']
                    if total - existing + len(segments) > MAX_COMPANY_CHUNKS: raise KnowledgeError('company_knowledge_limit')
                    conn.execute('DELETE FROM knowledge_chunks WHERE company_id=? AND source_id=?',(company,source_id))
                    now = time.time()
                    for index, (content, vector) in enumerate(zip(segments,vectors)):
                        conn.execute('INSERT INTO knowledge_chunks VALUES(?,?,?,?,?,?,?,?)',(secrets.token_hex(16),company,source_id,version,index,content,json.dumps(vector),now))
                    result = 'ready'
        with database.connect(company=company,write=True) as conn:
            conn.execute('UPDATE ingestion_jobs SET status=?,updated=? WHERE id=? AND company_id=?',(result,time.time(),job_id,company))
        return result
    except KnowledgeError as exc:
        error = exc.code
    except Exception:
        error = 'indexing_failed'
    with database.connect(company=company,write=True) as conn:
        conn.execute("UPDATE ingestion_jobs SET status='failed',error=?,updated=? WHERE id=? AND company_id=?",(error,time.time(),job_id,company))
    return 'failed'

def search(database, company: str, question: str, previous: str = '', vectorize=encode, limit: int = 4):
    combined = question
    if previous and re.search(r'\b(it|that|those|they|their|this|also|what about|and)\b', question, re.I):
        combined = previous[:300] + ' ' + question
    with database.connect(company=company) as conn:
        rows = conn.execute("SELECT c.id,c.source_id,c.version,c.content,c.embedding,s.name,s.kind,s.source_url FROM knowledge_chunks c JOIN knowledge_sources s ON s.id=c.source_id AND s.company_id=c.company_id AND s.version=c.version AND s.status='Demo published' AND s.deleted_at IS NULL JOIN ingestion_jobs j ON j.source_id=c.source_id AND j.company_id=c.company_id AND j.version=c.version AND j.status='ready' WHERE c.company_id=? ORDER BY c.created DESC LIMIT 5000",(company,)).fetchall()
    if not rows: return []
    query_vector = vectorize([combined])[0]
    tokens = set(re.findall(r'[a-z0-9]{3,}', combined.lower()))
    ranked = []
    for row in rows:
        vector = json.loads(row['embedding'])
        semantic = sum(a*b for a,b in zip(query_vector, vector))
        content_tokens = set(re.findall(r'[a-z0-9]{3,}', (row['content']+' '+row['name']).lower()))
        lexical = len(tokens & content_tokens) / max(1, len(tokens))
        score = .72 * semantic + .23 * lexical
        ranked.append((score,semantic,dict(row),content_tokens))
    ranked.sort(key=lambda item:item[0],reverse=True)
    # Typo matching is useful but quadratic; apply it only to semantic candidates.
    candidates = []
    for score,semantic,row,content_tokens in ranked[:40]:
        fuzzy = max((SequenceMatcher(None, word, other).ratio() for word in tokens for other in content_tokens if abs(len(word)-len(other))<=2),default=0)
        candidates.append((score+.05*fuzzy,semantic,row))
    candidates.sort(key=lambda item:item[0],reverse=True)
    ranked = candidates
    if not ranked or ranked[0][0] < .29: return []
    selected = []
    for score,semantic,row in ranked:
        if len(selected) >= limit or score < max(.25,ranked[0][0]-.16): break
        selected.append({'chunkId':row['id'],'sourceId':row['source_id'],'version':row['version'],'title':row['name'],'url':row['source_url'] if row['kind']=='Website' else None,'text':row['content'],'score':round(score,3)})
    return selected

#!/usr/bin/env python3
"""SSH-friendly, local-only profile downloader job runner (stdlib)."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import uuid
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('PROFILEDL_DATA', str(ROOT / 'data'))).expanduser().resolve()
DB = DATA / 'jobs.sqlite3'
PLATFORMS = {
    'instagram.com': 'instagram', 'www.instagram.com': 'instagram',
    'tiktok.com': 'tiktok', 'www.tiktok.com': 'tiktok', 'vm.tiktok.com': 'tiktok',
    'x.com': 'x', 'www.x.com': 'x', 'twitter.com': 'x', 'www.twitter.com': 'x',
    'youtube.com': 'youtube', 'www.youtube.com': 'youtube', 'm.youtube.com': 'youtube',
    'youtu.be': 'youtube', 'www.facebook.com': 'facebook', 'facebook.com': 'facebook',
    'www.reddit.com': 'reddit', 'reddit.com': 'reddit',
    'www.pinterest.com': 'pinterest', 'pinterest.com': 'pinterest',
    'www.tumblr.com': 'tumblr', 'tumblr.com': 'tumblr',
    'www.threads.net': 'threads', 'threads.net': 'threads',
}
PHOTO_EXT = ('jpg','jpeg','png','webp','avif','heic','bmp','gif')
VIDEO_EXT = ('mp4','mov','webm','mkv','m4v','gifv','flv')

def connect():
    DATA.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=30)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('''CREATE TABLE IF NOT EXISTS jobs(
        id TEXT PRIMARY KEY, created_at TEXT, started_at TEXT, finished_at TEXT,
        status TEXT, platform TEXT, url TEXT, mode TEXT, media TEXT,
        limit_posts INTEGER, after_date TEXT, before_date TEXT, metadata INTEGER,
        folder TEXT, log TEXT, error TEXT, pid INTEGER)''')
    db.commit()
    return db

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError('Expected a JSON object')
    url = str(payload.get('url', '')).strip()
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or host not in PLATFORMS:
        raise ValueError('Only HTTPS URLs from the supported platform allowlist are accepted')
    if parsed.username or parsed.password or parsed.port is not None:
        raise ValueError('URL credentials and ports are disallowed')
    if len(url) > 2048:
        raise ValueError('URL too long')
    media = payload.get('media', 'both')
    if media not in ('photos', 'videos', 'both'):
        raise ValueError('media must be photos/videos/both')
    mode = payload.get('mode', 'all')
    if mode not in ('all', 'recent', 'new'):
        raise ValueError('mode must be all/recent/new')
    limit = payload.get('limit', 50 if mode == 'recent' else 0)
    if type(limit) is not int or limit < 0 or limit > 100000:
        raise ValueError('limit must be an integer 0..100000')
    if mode == 'recent' and limit == 0:
        raise ValueError('recent mode requires a nonzero limit')
    for k in ('after', 'before'):
        v = payload.get(k)
        if v:
            dt.date.fromisoformat(v)
    if payload.get('after') and payload.get('before') and payload['after'] > payload['before']:
        raise ValueError('after must be <= before')
    if type(payload.get('metadata', True)) is not bool:
        raise ValueError('metadata must be boolean')
    return {
        'url':url, 'platform':PLATFORMS[host], 'mode':mode, 'media':media,
        'limit_posts':limit, 'after_date':payload.get('after'),
        'before_date':payload.get('before'), 'metadata':int(payload.get('metadata', True)),
    }

def target_dir(j):
    parsed = urlparse(j['url'])
    path = parsed.path.strip('/').split('/')
    account = next((p.lstrip('@') for p in path if p and p not in ('videos','shorts','reels','posts','channel','user','c','@')), 'profile')
    if parsed.hostname == 'youtu.be': account = 'shared-video'
    account = re.sub('[^A-Za-z0-9_.-]', '_', account)[:70] or 'profile'
    # URL hash avoids collisions between profiles with the same display path.
    import hashlib
    suffix = hashlib.sha256(j['url'].split('?')[0].encode()).hexdigest()[:10]
    return DATA / 'downloads' / j['platform'] / f'{account}-{suffix}'

def build_command(j):
    folder = Path(j['folder'])
    folder.mkdir(parents=True, exist_ok=True)
    if j['platform'] == 'youtube':
        if j['media'] == 'photos':
            raise ValueError('YouTube photos-only mode is not implemented; choose videos/both')
        cmd = ['yt-dlp', '--ignore-config', '--yes-playlist', '--continue', '--no-overwrites',
               '--download-archive', str(folder / 'yt-archive.txt'),
               '--paths', str(folder), '--output', '%(upload_date|unknown)s_%(id)s.%(ext)s',
               '--retries', '5', '--fragment-retries', '5', '--sleep-requests', '1',
               '--merge-output-format', 'mp4']
        if j['metadata']:
            cmd += ['--write-info-json', '--write-description']
        if j['after_date']: cmd += ['--dateafter', j['after_date'].replace('-', '')]
        if j['before_date']: cmd += ['--datebefore', j['before_date'].replace('-', '')]
        if j['limit_posts']: cmd += ['--playlist-items', f'1:{j["limit_posts"]}']
        cmd += [j['url']]
    else:
        cmd = ['gallery-dl', '--config-ignore', '--no-input', '--directory', str(folder),
               '--download-archive', str(folder / 'gallery-archive.sqlite3'),
               '--sleep-request', '1-3', '--retries', '5']
        if j['metadata']: cmd.append('--write-metadata')
        if j['media'] != 'both':
            ext = PHOTO_EXT if j['media'] == 'photos' else VIDEO_EXT
            cmd += ['--filter', 'extension in ' + repr(ext)]
        if j['after_date']: cmd += ['--date-after', j['after_date']]
        if j['before_date']: cmd += ['--date-before', j['before_date']]
        if j['limit_posts']: cmd += ['--post-range', f'1-{j["limit_posts"]}']
        cmd += [j['url']]
    return cmd

def submit(payload):
    v = validate(payload)
    jid = uuid.uuid4().hex[:16]
    j = dict(v, id=jid)
    j['folder'] = str(target_dir(j))
    j['log'] = str(DATA / 'logs' / (jid + '.log'))
    (DATA / 'logs').mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute('''INSERT INTO jobs (id,created_at,status,platform,url,mode,media,limit_posts,
                     after_date,before_date,metadata,folder,log) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                   (jid,now(),'queued',j['platform'],j['url'],j['mode'],j['media'],j['limit_posts'],
                    j['after_date'],j['before_date'],j['metadata'],j['folder'],j['log']))
    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'worker', jid],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True,
                            close_fds=True)
    return {'id':jid,'status':'queued','platform':j['platform'],'folder':j['folder'],'worker_pid':proc.pid}

def status(jid):
    with connect() as db:
        db.row_factory = sqlite3.Row
        row = db.execute('SELECT * FROM jobs WHERE id=?', (jid,)).fetchone()
    if not row: raise ValueError('Unknown job ID')
    result = dict(row)
    path = Path(result['log'])
    result['last_log_lines'] = path.read_text(errors='replace').splitlines()[-12:] if path.exists() else []
    return result

def worker(jid):
    j = status(jid)
    with connect() as db:
        cursor = db.execute("UPDATE jobs SET status='running',started_at=?,pid=? WHERE id=? AND status='queued'",
                            (now(), os.getpid(), jid))
        db.commit()
        if cursor.rowcount != 1: return
    try:
        command = build_command(j)
        with open(j['log'], 'a', encoding='utf-8') as f:
            f.write('START ' + now() + ' engine=' + command[0] + '\n')
            f.flush()
            run = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT,
                                 check=False, cwd=str(ROOT))
        state = 'completed' if run.returncode == 0 else 'failed'
        err = None if run.returncode == 0 else f'Downloader exited with code {run.returncode}; inspect job log'
    except Exception as exc:
        state,err = 'failed', str(exc)
    with connect() as db:
        db.execute('UPDATE jobs SET status=?,finished_at=?,error=? WHERE id=?', (state,now(),err,jid))
        db.commit()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('submit-stdin')
    p = sub.add_parser('submit'); p.add_argument('url'); p.add_argument('--media',default='both');
    p.add_argument('--mode',default='all'); p.add_argument('--limit',type=int,default=0)
    p.add_argument('--after'); p.add_argument('--before'); p.add_argument('--no-metadata',action='store_true')
    s = sub.add_parser('status'); s.add_argument('id')
    w = sub.add_parser('worker'); w.add_argument('id')
    sub.add_parser('list')
    args = parser.parse_args()
    try:
        if args.command == 'submit-stdin': print(json.dumps(submit(json.load(sys.stdin))))
        elif args.command == 'submit':
            print(json.dumps(submit({'url':args.url,'media':args.media,'mode':args.mode,
                                     'limit':args.limit,'after':args.after,'before':args.before,
                                     'metadata':not args.no_metadata})))
        elif args.command == 'status': print(json.dumps(status(args.id),indent=2))
        elif args.command == 'worker': worker(args.id)
        elif args.command == 'list':
            with connect() as db:
                db.row_factory = sqlite3.Row
                rows = db.execute('SELECT id,created_at,status,platform,url,folder FROM jobs ORDER BY created_at DESC LIMIT 30').fetchall()
            print(json.dumps([dict(r) for r in rows],indent=2))
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(json.dumps({'error':str(e)})); sys.exit(1)

if __name__ == '__main__': main()

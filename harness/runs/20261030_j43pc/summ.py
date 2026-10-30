import json, sys, datetime
for f in sys.argv[1:]:
    d = json.load(open(f))
    t = lambda s: datetime.datetime.fromisoformat(s[:-1])
    g = d.get('got', {}); c = d.get('check', {})
    print(f.split('/')[-1], d['status'], d['reason'], d.get('kind'), {k: g.get(k) for k in ('x', 'y', 'z', 'yaw', 'pitch', 'fov', 'rms_px')} if g else c.get('got'), round((t(d['end_utc']) - t(d['start_utc'])).total_seconds(), 2), 's')

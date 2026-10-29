"""Deterministic gzip TSV files: sorted rows, gzip mtime 0 and no file name, so a re-run writes byte-identical bytes.

purpose: write and read the committed discovery tables (discovery/assets/index.tsv.gz, discovery/loc/keys.tsv.gz) so a re-run diffs cleanly
usage: from tsvgz import write, read, problems; write(path, header, rows); header, rows = read(path); problems(path) -> [str]   (library)
when: every J7 pass that commits a large table; `wsc discovery check` runs problems() on each committed file
not-a-verb: a library module imported by the discovery passes and the discovery verb
"""
import gzip
import io


def cell(v):
    """One cell: None is empty; tabs and line breaks (never in paths, keys or hashes) become spaces."""
    return '' if v is None else str(v).replace('\t', ' ').replace('\r', ' ').replace('\n', ' ')


def dumps(header, rows):
    text = '\t'.join(header) + '\n' + ''.join('\t'.join(cell(v) for v in r) + '\n' for r in sorted(rows))
    buf = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=buf, mtime=0, compresslevel=9) as g:
        g.write(text.encode('utf-8'))
    return buf.getvalue()


def write(path, header, rows):
    rows = [tuple(cell(v) for v in r) for r in rows]
    data = dumps(header, rows)
    with open(path, 'wb') as f:
        f.write(data)
    return len(rows)


def read(path):
    with open(path, 'rb') as f:
        lines = gzip.decompress(f.read()).decode('utf-8').split('\n')
    return lines[0].split('\t'), [tuple(x.split('\t')) for x in lines[1:] if x]


def problems(path, header=None):
    """Header as expected, rows sorted and unique, and the bytes exactly what dumps() writes for them."""
    try:
        raw = open(path, 'rb').read()
        h, rows = read(path)
    except (OSError, ValueError, EOFError) as e:
        return [f'{path}: {e}']
    out = []
    if header is not None and h != list(header):
        out.append(f'{path}: header {h}, want {list(header)}')
    if rows != sorted(set(rows)):
        out.append(f'{path}: rows are not sorted or repeat')
    elif dumps(h, rows) != raw:
        out.append(f'{path}: not the deterministic gzip of its rows (gzip mtime 0, level 9, no name)')
    return out

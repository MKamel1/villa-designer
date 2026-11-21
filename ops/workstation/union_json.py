"""Union-merge JSON lesson files (LEARNINGS) by lesson_id.

Two ways to use it:

1. Git merge driver (no conflict ever reaches the working tree):
     git config merge.union-json.name "union JSON lists by lesson_id"
     git config merge.union-json.driver "python ops/workstation/union_json.py --driver %O %A %B"
     echo "docs/LEARNINGS.json merge=union-json" >> .gitattributes     # adjust the path
   Ours (%A) is kept; records only in theirs (%B) are appended. The result is written to %A.
2. Repair a file that already has conflict markers (the original 2026-10 use):
     python ops/workstation/union_json.py path/to/file.json
"""
import json
import sys


def split_markers(text, keep):
    out, mode = [], None
    for line in text.splitlines(keepends=True):
        if line.startswith('<<<<<<<'):
            mode = 'ours'; continue
        if line.startswith('=======') and mode:
            mode = 'theirs'; continue
        if line.startswith('>>>>>>>'):
            mode = None; continue
        if mode is None or mode == keep:
            out.append(line)
    return json.loads(''.join(out))


def union(a, b):
    key = next(k for k, v in a.items() if isinstance(v, list))
    ids = {r['lesson_id'] for r in a[key]}
    a[key] += [r for r in b.get(key, []) if r['lesson_id'] not in ids]
    return key, a


def write(path, data):
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def main(argv):
    if argv and argv[0] == '--driver':
        _base, ours, theirs = argv[1:4]
        with open(ours, encoding='utf-8') as fa, open(theirs, encoding='utf-8') as fb:
            key, merged = union(json.load(fa), json.load(fb))
        write(ours, merged)
        print(key, len(merged[key]))
        return 0
    path = argv[0]
    with open(path, encoding='utf-8') as fh:
        text = fh.read()
    key, merged = union(split_markers(text, 'ours'), split_markers(text, 'theirs'))
    write(path, merged)
    print(key, len(merged[key]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))

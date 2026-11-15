import collections
import glob
import sys
sys.path.insert(0, '.tools')
from pypdf import PdfReader
from pypdf.generic import ContentStream

r = PdfReader(glob.glob('*.ai')[0])
p = r.pages[0]
props = p['/Resources']['/Properties']
counts = collections.defaultdict(collections.Counter)
examples = collections.defaultdict(list)
layer = None
for args, op in ContentStream(p['/Contents'], r).operations:
    if op == b'BDC':
        layer = str(props[args[1]].get_object().get('/Name'))
    elif op == b'EMC':
        layer = None
    elif layer:
        counts[layer][op.decode()] += 1
        if len(examples[layer]) < 14:
            examples[layer].append((str(args), op.decode()))
for key, value in counts.items():
    print(key, dict(value))
    if key in ('Route','Base','depthmap'):
        print(examples[key])

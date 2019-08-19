from django.forms import formsets

from collections.abc import Mapping
import re
import itertools as it


class BulkMuxDict(Mapping):
    """An immutable dictionary that pulls from either data or bulk.

    Args:
        data: a Django request dictionary holding form data
        bulk: a sequence like object holding dictionary like objects
        header_fields: a sequence like object holding fields not in bulk
        prefix: the value prefixed to form's fields
    """

    def __init__(self, data, bulk, header_fields, prefix):
        self.data = data
        self.bulk = bulk
        self.prefix = prefix
        self.header_dict = {}
        for f in header_fields:
            k = "%s-%s" % (self.prefix, f)
            if k in data:
                self.header_dict[f] = k
        self.r = re.compile("%s-(\\d+)?-?(.+)" % prefix)
        data_form_i = (i[0] for i in map(self.parse_key, data) if i[0] is not None)
        self.bulk_i_begin = max(data_form_i, default=-1) + 1

    def __getitem__(self, k):
        val = None
        i, f = self.parse_key(k)
        if i is not None:
            i -= self.bulk_i_begin
        if f == formsets.TOTAL_FORM_COUNT:
            val = str(self.bulk_i_begin + len(self.bulk))
        elif k in self.data:
            val = self.data[k]
        elif f in self.header_dict:
            val = self.data[self.header_dict[f]]
        elif i is not None and i < len(self.bulk) and i >= 0:
            val = self.bulk[i].get(f)
        if val is not None:
            return val
        else:
            raise KeyError

    def __iter__(self):
        header_i = set()
        for k in self.data:
            i, f = self.parse_key(k)
            if f not in self.header_dict:
                if i is not None and i not in header_i:
                    header_i.add(i)
                    for hf in self.header_dict:
                        yield "%s-%d-%s" % (self.prefix, i, hf)
                yield k
        for i, d in enumerate(self.bulk, start=self.bulk_i_begin):
            for f in it.chain(self.header_dict, d):
                yield "%s-%d-%s" % (self.prefix, i, f)

    def __len__(self):
        return len(self.data) + sum(len(d) for d in self.bulk)

    def items(self):
        header_i = set()
        for k, v in self.data.items():
            i, f = self.parse_key(k)
            if f not in self.header_dict:
                if i is not None and i not in header_i:
                    header_i.add(i)
                    for hf, hv in self.header_dict:
                        yield ("%s-%d-%s" % (self.prefix, i, hf), hv)
                yield (k, v)
        for i, d in enumerate(self.bulk, start=self.bulk_i_begin):
            for f, v in it.chain(self.header_dict.items(), d.items()):
                yield ("%s-%d-%s" % (self.prefix, i, f), v)

    def parse_key(self, k):
        m = self.r.match(k)
        i = m.group(1) if m is not None else None
        f = m.group(2) if m is not None else None
        if i is not None:
            return (int(i), f)
        else:
            return (i, f)

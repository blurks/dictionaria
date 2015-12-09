# coding: utf8
from __future__ import unicode_literals
from hashlib import md5

from clld.db.models import common
from clldutils.sfm import SFM, Entry
from clldutils.misc import cached_property, slug


#
# FIXME: follow recommendations of EOPAS toolbox import http://www.eopas.org/help
#
#
class Example(Entry):
    """
    \ref
    \rf
    \tx
    \mr
    \mg
    \fg
    """
    markers = ['ref', 'lemma', 'rf', 'tx', 'mr', 'mg', 'fg']

    @staticmethod
    def normalize(morphemes_or_gloss):
        if morphemes_or_gloss:
            return '\t'.join(
                [p for p in morphemes_or_gloss.split() if not p.startswith('#')])

    @property
    def id(self):
        res = self.get('ref')
        if not res:
            res = md5(slug(self.text + self.translation).encode('utf')).hexdigest()
            self.insert(0, ('ref', res))
        return res

    def set(self, key, value):
        assert key in self.markers
        for i, (k, v) in enumerate(self):
            if k == key:
                if key == 'lemma':
                    value = ' ; '.join([v, value])
                self[i] = (key, value)
                break
        else:
            self.append((key, value))

    @property
    def lemmas(self):
        return [l.strip() for l in self.get('lemma', '').split(';') if l.strip()]

    @property
    def corpus_ref(self):
        return self.get('rf')

    @property
    def text(self):
        return self.get('tx')

    @property
    def translation(self):
        return self.get('fg')

    @property
    def morphemes(self):
        return self.normalize(self.get('mr'))

    @property
    def gloss(self):
        return self.normalize(self.get('mg'))

    def __unicode__(self):
        lines = []
        for key in self.markers:
            value = self.get(key) or ''
            if key in ['mr', 'mg']:
                value = self.normalize(value) or ''
            lines.append('%s %s' % (key, value))
        return '\n'.join('\\' + l for l in lines)


class Examples(SFM):
    """
    \ref d48204ced7d012dd071d0ec402e58d20
    \tx A beiko.
    \mb
    \gl
    \ft The child.
    """
    def read(self, filename, **kw):
        return SFM.read(self, filename, entry_impl=Example, **kw)

    @cached_property()
    def _map(self):
        return {entry.get('ref'): entry for entry in self}

    def get(self, item):
        return self._map.get(item)


def load_examples(submission, data, lang):
    for ex in Examples.from_file(submission.dir.joinpath('processed', 'examples.sfm')):
        data.add(
            common.Sentence,
            ex.id,
            id='%s-%s' % (submission.id, ex.id),
            name=ex.text,
            language=lang,
            analyzed=ex.morphemes,
            gloss=ex.gloss,
            description=ex.translation)


class Corpus(object):
    """
    ELAN corpus exported using the Toolbox exporter

    http://www.mpi.nl/corpus/html/elan/ch04s03s02.html#Sec_Exporting_a_document_to_Toolbox
    """
    def __init__(self, dir_):
        self.examples = Examples()
        marker_map = {
            'utterance_id': 'ref',
            'utterance': 'tx',
            'gramm_units': 'mb',
            'rp_gloss': 'gl',
        }
        for path in dir_.glob('*.eaf.sfm'):
            self.examples.read(path, marker_map=marker_map, entry_sep='\\utterance_id')

    def get(self, key):
        res = self.examples.get(key)
        if not res:
            # We try to correct the lookup key. If a key like 'Abc.34' is used and not
            # found, we try 'Abc.034' as well.
            try:
                prefix, number = key.split('.', 1)
                res = self.examples.get('%s.%03d' % (prefix, int(number)))
            except ValueError:
                pass
        return res

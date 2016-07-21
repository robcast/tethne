import os, re, rdflib, codecs, chardet, copy, unicodedata, logging
import xml.etree.ElementTree as ET

# rdflib complains a lot.
logging.getLogger("rdflib").setLevel(logging.ERROR)

import sys
PYTHON_3 = sys.version_info[0] == 3
if PYTHON_3:
    unicode = str

def _fast_iter(context, func, tag):
    for event, elem in context:
        func(elem)
        if elem.tag == tag:
            elem.clear()
    del context


class dobject(object):
    pass


def _cast(value):
    """
    Attempt to convert ``value`` to an ``int`` or ``float``. If unable, return
    the value unchanged.
    """

    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


class BaseParser(object):
    """
    Base class for all data parsers. Do not instantiate directly.
    """
    def __init__(self, path, **kwargs):
        self.path = path
        self.data = []
        self.fields = set([])

        self.encoding = 'utf-8'

        for k, v in kwargs.items():
            setattr(self, k, v)

        self.open()

    def new_entry(self):
        """
        Prepare a new data entry.
        """
        self.data.append(self.entry_class())

    def _get_handler(self, tag):
        handler_name = 'handle_{tag}'.format(tag=tag)
        if hasattr(self, handler_name):
            return getattr(self, handler_name)
        return

    def set_value(self, tag, value):
        setattr(self.data[-1], tag, value)

    def postprocess_entry(self):
        for field in self.fields:
            processor_name = 'postprocess_{0}'.format(field)
            if hasattr(self.data[-1], field) and hasattr(self, processor_name):
                getattr(self, processor_name)(self.data[-1])


class IterParser(BaseParser):
    entry_class = dobject
    """Model for data entry."""

    concat_fields = []
    """
    Multi-line fields here should be concatenated, rather than represented
    as lists.
    """

    tags = {}

    def __init__(self, *args, **kwargs):
        super(IterParser, self).__init__(*args, **kwargs)

        self.current_tag = None
        self.last_tag = None

        if kwargs.get('autostart', True) and getattr(self, 'autostart', True):
            self.start()

    def parse(self, parse_only=None):
        """

        """
        # The user should be able to limit parsing to specific fields.
        if parse_only:
            tag_lookup = {v: k for k, v in self.tags.items()}
            self.parse_only = set([tag_lookup.get(field)
                                   for field in parse_only
                                   if field in tag_lookup])

        while True:        # Main loop.
            tag, data = self.next()
            if self.is_eof(tag):
                self.postprocess_entry()
                break

            self.handle(tag, data)
            self.last_tag = tag
        return self.data

    def start(self):
        """
        Find the first data entry and prepare to parse.
        """

        while not self.is_start(self.current_tag):
            self.next()
        self.new_entry()

    def handle(self, tag, data):
        """
        Process a single line of data, and store the result.

        Parameters
        ----------
        tag : str
        data :
        """

        if self.is_end(tag):
            self.postprocess_entry()

        if self.is_start(tag):
            self.new_entry()

        if not data or not tag:
            return

        if getattr(self, 'parse_only', None) and tag not in self.parse_only:
            return

        # TODO: revisit encoding here.
        if isinstance(data, unicode):
            data = unicodedata.normalize('NFKD', data)#.encode('utf-8','ignore')
            data = data.replace('\r', '')

        handler = self._get_handler(tag)
        if handler is not None:
            data = handler(data)

        if tag in self.tags:    # Rename the field.
            tag = self.tags[tag]

        # Multiline fields are represented as lists of values.
        if hasattr(self.data[-1], tag):
            value = getattr(self.data[-1], tag)
            if tag in self.concat_fields:
                #if type(data) is str:
                #    data = data.decode(self.encoding)
                value = ' '.join([value, unicode(data)])
            elif type(value) is list:
                value.append(data)
            elif value not in [None, '']:
                value = [value, data]
        else:
            value = data
        setattr(self.data[-1], tag, value)
        self.fields.add(tag)


class FTParser(IterParser):
    """
    Base parser for field-tagged data files.
    """

    start_tag = 'ST'
    """Signals the start of a data entry."""

    end_tag = 'ED'
    """Signals the end of a data entry."""

    def is_start(self, tag):
        return tag == self.start_tag

    def is_end(self, tag):
        return tag == self.end_tag

    def is_eof(self, tag):
        return self.at_eof

    def open(self):
        """
        Open the data file.
        """

        if not os.path.exists(self.path):
            raise IOError("No such path: {0}".format(self.path))

        with codecs.open(self.path, "rb") as f:
            msg = f.read()
        result = chardet.detect(msg)
        self.encoding = result['encoding']
        self.buffer = codecs.open(self.path, "rb", encoding=self.encoding)

        self.at_eof = False

    def next(self):
        """
        Get the next line of data.

        Returns
        -------
        tag : str
        data :
        """
        line = self.buffer.readline()

        while line == '\n':       # Skip forward to the next line with content.
            line = self.buffer.readline()

        if line == '':            # End of file.
            self.at_eof = True
            return None, None

        match = re.match('([A-Z]{2}|[C][1])\W(.*)', line)
        if match is not None:
            self.current_tag, data = match.groups()
        else:
            self.current_tag = self.last_tag
            data = line.strip()
        return self.current_tag, _cast(data)

    def __del__(self):
        if hasattr(self, 'buffer'):
            self.buffer.close()


class XMLParser(IterParser):
    entry_element = 'article'
    entry_class = dobject

    def open(self):
        # with open(self.path, 'r') as f:
        #     self.root = ET.fromstring(f.read())
        # pattern = './/{elem}'.format(elem=self.entry_element)
        # self.elements = self.root.findall(pattern)

        # ET does not support unicode, but it does support encodings. So we
        #  open the file without any intervention.
        self.f = open(self.path, 'r')
        self.iterator = ET.iterparse(self.f)

        self.at_start = False
        self.at_end = False
        self.children = []


    def new_entry(self):
        """
        Prepare a new data entry.
        """
        self.postprocess_entry()
        super(XMLParser, self).new_entry()

    def is_start(self, tag):
        return tag == self.entry_element

    def is_end(self, tag):
        return tag == self.entry_element

    def is_eof(self, tag):
        return len(self.elements) == 0 and len(self.children) == 0

    def start(self):
        self.new_entry()

    def next(self, child):
        child = copy.deepcopy(child)
        tag, data = child.tag, child.text
        if data:
            data = data.strip()

        #if type(data) is str:
        #    data = data.decode(self.encoding)

        self.handle(tag, data)
        self.last_tag = tag

    def parse(self, parse_only=None):
        """

        """
        # The user should be able to limit parsing to specific fields.
        if parse_only:
            tag_lookup = {v: k for k, v in self.tags.items()}
            self.parse_only = set([tag_lookup.get(field)
                                   for field in parse_only
                                   if field in tag_lookup]) | set(parse_only)

        _fast_iter(self.iterator, self.next, self.entry_element)

        if len(self.data[-1].__dict__) == 0:
            del self.data[-1]
        return self.data

    def __del__(self):
        if hasattr(self, 'f'):
            self.f.close()


class RDFParser(BaseParser):
    entry_elements = ['Document']   #
    meta_elements = []
    concat_fields = []

    def open(self):
        self.graph = rdflib.Graph()
        self.graph.parse(self.path)
        self.entries = []

        for element in self.entry_elements:
            query = 'SELECT * WHERE { ?p a ' + element + ' }'
            self.entries += [r[0] for r in self.graph.query(query)]

    def next(self):
        if len(self.entries) > 0:
            return self.entries.pop(0)

    def parse(self):
        meta_fields, meta_refs = zip(*self.meta_elements)

        while True:        # Main loop.
            entry = self.next()
            if entry is None:
                break

            self.new_entry()

            for s, p, o in self.graph.triples((entry, None, None)):
                if p in meta_refs:  # Look for metadata fields.
                    tag = meta_fields[meta_refs.index(p)]
                    self.handle(tag, o)
            self.postprocess_entry()

        return self.data

    def handle(self, tag, data):
        handler = self._get_handler(tag)

        if handler is not None:
            data = handler(data)

        if tag in self.tags:    # Rename the field.
            tag = self.tags[tag]

        if data is not None:
            # Multiline fields are represented as lists of values.
            if hasattr(self.data[-1], tag):
                value = getattr(self.data[-1], tag)
                if tag in self.concat_fields:
                    value = ' '.join([value, data])
                elif type(value) is list:
                    value.append(data)
                elif value not in [None, '']:
                    value = [value, data]
            else:
                value = data

            setattr(self.data[-1], tag, value)
            self.fields.add(tag)

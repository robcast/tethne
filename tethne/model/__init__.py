"""
"""

import os
import re
import shutil
import shutil
import tempfile
import subprocess


class Model(object):
    """
    Base class for models.
    """

    def __init__(self, corpus=None, prep=True, **kwargs):
        """
        Initialize the ModelManager.
        """

        self.corpus = corpus
        self.temp = tempfile.mkdtemp()

        for attr in ['run', 'prep']:
            if not hasattr(self, attr):
                msg = 'Model subclass must implement method {0}'.format(attr)
                raise AttributeError(msg)

        # Make all kwargs available as attributes.
        for key, value in kwargs.items():
            if hasattr(self, key):  # Don't overwrite methods.
                if hasattr(getattr(self, key), '__call__'):
                    continue
            setattr(self, key, value)

        if prep:
            self.prep()

    def __del__(self):
        """
        Delete temporary directory and all files contained therein.
        """
        if getattr(self, 'nodelete', False):
            return
        if hasattr(self, 'temp'):
            shutil.rmtree(self.temp)

    @property
    def ll_trace(self):
        """
        Plots LL/topic over iterations.
        """

        return self.ll

    def fit(self, **kwargs):
        # Make all kwargs available as attributes.
        for key, value in kwargs.items():
            if hasattr(self, key):  # Don't overwrite methods.
                if hasattr(getattr(self, key), '__call__'):
                    continue
            setattr(self, key, value)

        self.run(**kwargs)

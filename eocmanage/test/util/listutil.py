from twisted.trial.util import wait
import os, shutil, errno
from eocmanage import eocinterface

def eoc_destroy(name):
    """Destroy list with given name"""
    assert '@' in name
    assert not name.startswith('.')
    path = os.path.join('dot-eoc', name)
    try:
        shutil.rmtree(path)
    except OSError, e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise

def eoc_create(name, *owners):
    """Create list with given name"""
    assert '@' in name
    assert not name.startswith('.')
    d = eocinterface.create(name, owners)
    wait(d)

__all__ = ['eoc_destroy',
           'eoc_create',
           ]

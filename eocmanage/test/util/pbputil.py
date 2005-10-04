import os, shutil, errno

def destroy(name):
    """Destroy list with given name"""
    print 'DESTROY', repr(name)
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

__all__ = ['destroy',
           ]

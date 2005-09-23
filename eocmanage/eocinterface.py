import os, ConfigParser
from twisted.internet import utils

class EocFailed(Exception):
    """Calling eoc failed"""

    def __init__(self, code, err):
        self.code = code
        self.err = err

    def __str__(self):
        return '%s: %d: %s' % (
            self.__doc__,
            self.code,
            self.err,
            )

def _runEoc(*args):
    d = utils.getProcessOutputAndValue(
        executable='enemies-of-carlotta',
        args=args,
        env=os.environ)
    def _cb((out, err, code)):
        if code != 0:
            raise EocFailed, (code, err)
        return out
    d.addCallback(_cb)
    return d

def create(name, owners):
    def listem():
        for o in owners:
            yield '--owner'
            yield o
    return _runEoc('--create',
                   '--name', name,
                   *list(listem()))

def listLists():
    d = _runEoc('--show-lists')
    def _cb(s):
        return s.splitlines()
    d.addCallback(_cb)
    return d

class MailingList(object):
    def __init__(self, listname):
        self.listname = listname

    def runEoc(self, *args):
        return _runEoc('--name', self.listname, *args)

    def subscribe(self, address):
        return self.runEoc(
            '--subscribe',
            '--',
            address)

    def unsubscribe(self, address):
        return self.runEoc(
            '--unsubscribe',
            '--',
            address)

    def list(self):
        d = self.runEoc('--list')
        def _cb(s):
            return s.splitlines()
        d.addCallback(_cb)
        return d

    def _getConfig(self):
        # TODO going too much under the hood
	cp = ConfigParser.ConfigParser()
	cp.add_section("list")
	cp.set("list", "subscription", "free")
	cp.set("list", "posting", "free")
        cp.read(os.path.join(os.path.expanduser('~/.enemies-of-carlotta'),
                             self.listname,
                             'config'))
        return cp

    def getSubscription(self):
        cp = self._getConfig()
	return cp.get("list", "subscription")

    def getPosting(self):
        cp = self._getConfig()
	return cp.get("list", "posting")

    def edit(self, **kw):
        args = ['--edit']
        for var in ['subscription', 'posting']:
            val = kw.pop(var, None)
            if val is not None:
                args.extend(['--%s' % var, val])
        return self.runEoc(*args)

    def destroy(self):
        return self.runEoc('--destroy')

if __name__ == '__main__':
    from twisted.internet import reactor
    l = MailingList('foo@example.com')
    #d = create('foo@example.com', ['bar'])
    #d = l.subscribe('test@example.com')
    d = l.list()
    def _p(x):
        print x
    d.addBoth(_p)
    d.addBoth(lambda _: reactor.stop())
    reactor.run()


import os, ConfigParser
from cStringIO import StringIO
from twisted.internet import utils, protocol, defer, reactor

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

class _GetEocResult(protocol.ProcessProtocol):

    def __init__(self, deferred, stdin):
        self.deferred = deferred
        self.stdin = stdin

        self.outBuf = StringIO()
        self.errBuf = StringIO()
        self.outReceived = self.outBuf.write
        self.errReceived = self.errBuf.write

    def connectionMade(self):
        protocol.ProcessProtocol.connectionMade(self)
        if self.stdin is not None:
            self.transport.write(self.stdin)
        self.transport.closeStdin()

    def processEnded(self, reason):
        out = self.outBuf.getvalue()
        err = self.errBuf.getvalue()
        e = reason.value
        code = e.exitCode
        if e.signal:
            self.deferred.errback((out, err, e.signal))
        else:
            self.deferred.callback((out, err, code))

def _runEoc(*args, **kwargs):
    kwargs.setdefault('env', os.environ)
    stdin = kwargs.pop('stdin', None)
    d = defer.Deferred()
    p = _GetEocResult(d, stdin)
    EXECUTABLE='enemies-of-carlotta'
    reactor.spawnProcess(p,
                         executable=EXECUTABLE,
                         args=(EXECUTABLE,)+tuple(args),
                         **kwargs)
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

    def runEoc(self, *args, **kwargs):
        return _runEoc('--name', self.listname, *args, **kwargs)

    def messageToEoc(self, *args, **kwargs):
        message = kwargs.pop('message')

        name = self.listname
        command = kwargs.pop('command', None)
        if command is not None:
            local, domain = name.split('@', 1)
            name = '%s-%s@%s' % (local, command, domain)

        kwargs.get('env', {}).setdefault('RECIPIENT', name)
        return _runEoc('--name', self.listname, '--incoming',
                       stdin=message, *args, **kwargs)

    def exists(self):
        d = self.runEoc('--is-list')
        def cb(dummy):
            return True
        def eb(reason):
            reason.trap(EocFailed)
            if reason.value.code == 1:
                return False
            else:
                raise
        d.addCallbacks(cb, eb)
        return d

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

    def requestSubscribe(self, address):
        env = {}
        env.update(os.environ)
        env['SENDER'] = address

        return self.messageToEoc(command='subscribe',
                                 message='TODO',
                                 env=env)

    def requestUnsubscribe(self, address):
        env = {}
        env.update(os.environ)
        env['SENDER'] = address

        return self.messageToEoc(command='unsubscribe',
                                 message='TODO',
                                 env=env)

    def list(self):
        d = self.runEoc('--list')
        def _cb(s):
            return s.splitlines()
        d.addCallback(_cb)
        return d

    def _getConfig(self):
        # TODO going too much under the hood
        EOC_DOTDIR = os.environ.get('EOC_DOTDIR', None)
        if EOC_DOTDIR is None:
            EOC_DOTDIR = os.path.expanduser('~/.enemies-of-carlotta')
	cp = ConfigParser.ConfigParser()
	cp.add_section("list")
	cp.set("list", "subscription", "free")
	cp.set("list", "posting", "free")
        cp.read(os.path.join(EOC_DOTDIR,
                             self.listname,
                             'config'))
        return cp

    def _editConfig(self, **kw):
        # TODO going too much under the hood
        cp = self._getConfig()

        for k,v in kw.items():
            cp.set("list", k, v)

        EOC_DOTDIR = os.environ.get('EOC_DOTDIR', None)
        if EOC_DOTDIR is None:
            EOC_DOTDIR = os.path.expanduser('~/.enemies-of-carlotta')
        filename = os.path.join(EOC_DOTDIR,
                                self.listname,
                                'config')
        f = file('%s.tmp' % filename, 'w')
        cp.write(f)
        f.close()
        os.rename('%s.tmp' % filename, filename)

    def getSubscription(self):
        cp = self._getConfig()
	return cp.get("list", "subscription")

    def getPosting(self):
        cp = self._getConfig()
	return cp.get("list", "posting")

    def getMailOnSubscriptionChanges(self):
        cp = self._getConfig()
	r = cp.get("list", "mail-on-subscription-changes")
        return r == 'yes'

    def getMailOnForcedUnsubscribe(self):
        cp = self._getConfig()
	r = cp.get("list", "mail-on-forced-unsubscribe")
        return r == 'yes'

    def _edit(self, **kw):
        rawEdit = {}
        for var, iniName in [
            ('mailOnSubscriptionChanges',
             'mail-on-subscription-changes'),
            ('mailOnForcedUnsubscribe',
             'mail-on-forced-unsubscribe'),
            ]:
            val = kw.pop(var, None)
            if val is not None:
                if val:
                    val = 'yes'
                else:
                    val = 'no'
                rawEdit[iniName] = val
        if rawEdit:
            self._editConfig(**rawEdit)

        args = []
        for var in ['subscription', 'posting']:
            val = kw.pop(var, None)
            if val is not None:
                args.extend(['--%s' % var, val])
        if kw:
            raise RuntimeError, 'Unhandled eoc configuration items: %r' % kw

        if args:
            args.insert(0, '--edit')
            return self.runEoc(*args)

    def edit(self, **kw):
        return defer.maybeDeferred(self._edit, **kw)

    def destroy(self):
        return self.runEoc('--destroy')

    def getOwners(self):
        cp = self._getConfig()
	return cp.get("list", "owners").split()

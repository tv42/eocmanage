import os, sets
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
    executable = kwargs.pop('executable', None)
    if executable is None:
        executable = 'enemies-of-carlotta'
    reactor.spawnProcess(p,
                         executable=executable,
                         args=(executable,)+tuple(args),
                         **kwargs)
    def _cb((out, err, code)):
        if code != 0:
            raise EocFailed, (code, err)
        return out
    d.addCallback(_cb)
    return d

class EocSite(object):
    #TODO move runEoc, dotdir, asUser etc under this

    eocDotDir = None
    asUser = None

    def __init__(self, **kw):
        asUser = kw.pop('asUser', None)
        if asUser is not None:
            self.asUser = asUser

        eocDotDir = kw.pop('eocDotDir', None)
        if eocDotDir is not None:
            self.eocDotDir = eocDotDir

        super(EocSite, self).__init__(**kw)

    def create(self, name, owners):
        def listem():
            for o in owners:
                yield '--owner'
                yield o
        return _runEoc('--create',
                       '--name', name,
                       *list(listem()))

    def listLists(self):
        d = _runEoc('--show-lists')
        def _cb(s):
            return s.splitlines()
        d.addCallback(_cb)
        return d

    def getList(self, listname):
        ml = MailingList(self, listname)
        return ml

class MailingList(object):
    """Please do not instantiate directly, use anEocSite.getList(listname)."""
    def __init__(self, site, listname):
        self.site = site
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

    _CFG_BOOLEANS = sets.ImmutableSet(['mail-on-subscription-changes',
                                       'mail-on-forced-unsubscribe'])

    def _cfgSerialize(self, item, value):
        if item in self._CFG_BOOLEANS:
            if value:
                return 'yes'
            else:
                return 'no'
        else:
            return value

    def _cfgUnserialize(self, item, value):
        if item in self._CFG_BOOLEANS:
            if value == 'yes':
                return True
            else:
                return False
        else:
            return value

    def getConfig(self, *items):
        d = _runEoc('--',
                    self.listname,
                    'get',
                    executable='eocmanage-config',
                    *items)
        def _cb(output, items):
            values = output.splitlines()
            if len(values) != len(items):
                raise RuntimeError('Config result does not match requested items %r: %r' % (items, output))

            values = [self._cfgUnserialize(item, value)
                      for item, value in zip(items, values)]

            if len(values) == 1:
                return values[0]
            else:
                return values
        d.addCallback(_cb, items)
        return d

    def setConfig(self, **kw):
        args = []
        for k,v in kw.items():
            if '=' in k:
                raise RuntimeError('Invalid configuration item: %r' % k)
            v = self._cfgSerialize(k, v)
            args.append('%s=%s' % (k, v))
        d = _runEoc('--',
                    self.listname,
                    'set',
                    executable='eocmanage-config',
                    *args)
        return d

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

    def __edit_ini(self, kw):
        """Note: mutates kw, it's not a **kwargs."""
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
            return self.setConfig(**rawEdit)

    def __edit_other(self, kw):
        """Note: mutates kw, it's not a **kwargs."""
        args = []
        for var in ['subscription', 'posting']:
            val = kw.pop(var, None)
            if val is not None:
                args.extend(['--%s' % var, val])

        if args:
            args.insert(0, '--edit')
            return self.runEoc(*args)

    def edit(self, **kw):
        d = defer.maybeDeferred(self.__edit_ini, kw)
        def _cb1(dummy, kw):
            return defer.maybeDeferred(self.__edit_other, kw)
        d.addCallback(_cb1, kw)
        def _cbFinal(dummy, kw):
            if kw:
                raise RuntimeError, 'Unhandled eoc configuration items: %r' % kw
        d.addCallback(_cbFinal, kw)
        return d

    def destroy(self):
        return self.runEoc('--destroy')

    def getOwners(self):
        d = self.getConfig('owners')
        def _cb(owners):
            return owners.split()
        d.addCallback(_cb)
        return d

from zope.interface import implements
from nevow import inevow, static
from eocmanage import common

class _MockLogin(object):
    implements(inevow.IResource)
    def renderHTTP(self, ctx):
        return 'Nothing here.'
    def locateChild(self, ctx, segments):
        address = '/'.join(segments)
        sess = inevow.ISession(ctx)
        sess.setComponent(common.IAuthenticatedEmailAddress, address)
        return static.Data('You are know authenticated as %s' % address,
                           'text/plain'), []

class MockAuth(object):
    """
    A unit testing helper that allows anyone to pretend they are who
    they please, with no real authentication.

    DO NOT USE IN PRODUCTION SYSTEMS!
    """
    implements(inevow.IResource)

    child_login = _MockLogin()

    def renderHTTP(self, ctx):
        return 'Nothing here.'

    def locateChild(self, ctx, segments):
        child = getattr(self, 'child_%s' % segments[0], None)
        if child is None:
            return child
        else:
            return child, segments[1:]

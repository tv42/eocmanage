from zope.interface import Interface
import string, email.Utils, time
from twisted.internet import defer
from twisted.web import http
from nevow import context, compy, inevow, tags
from formless import annotate

class EmailAddress(annotate.String):
    required = True
    requiredFailMessage = 'Please enter an email address.'

    allowedSpecials = '@.+-'
    def _checkMailAddress(self, val):
        for c in val:
            if c not in (string.ascii_letters
                         +string.digits
                         +self.allowedSpecials):
                raise annotate.InputError, (
                    "Please only use characters a-zA-Z0-9 and %r in email addresses"
                    % self.allowedSpecials)

    def coerce(self, *a, **kw):
        val = super(EmailAddress, self).coerce(*a, **kw)
        realname, address = email.Utils.parseaddr(val)
        if not address:
            raise annotate.InputError, self.requiredFailMessage
        if ('@' not in address or address.endswith('@')):
            raise annotate.InputError, "Please include a domain in the email address"
        if address.count('@') != 1:
            raise annotate.InputError, "Please include a valid hostname in the email address"
        if address.startswith('@'):
            raise annotate.InputError, "Please include a local part in the email address"

        self._checkMailAddress(address)
        return address

def render_if(ctx, data):
    r=ctx.tag.allPatterns(str(bool(data)))
    return ctx.tag.clear()[r]

class IEmailAddress(Interface):
    pass

COOKIE_KEY = 'eocmanage_email'

def rememberEmail(ctx, address):
    remembered = IEmailAddress(ctx)
    if remembered != address:
        request = inevow.IRequest(ctx)
        expires = http.datetimeToString(time.time() + 60*60*24*365)
        request.addCookie(COOKIE_KEY, address,
                          path="/", #TODO path="/%s" % '/'.join(request.prepath),
                          ##TODO secure=False,
                          expires=expires)

def _remembered(ctx):
    """
    Try to get a remembered email address from context.

    - authenticated users are recognized
    - addresses stored in a cookie are recognized,
      but verified to be validly formatted

    @return: email address as string, or empty string for
    nothing remembered.

    (Cannot use None as nothing remembered, as that has special
    meaning to the adapter machinery.)
    """

    authenticated = IAuthenticatedEmailAddress(ctx)
    if authenticated:
        return authenticated
    request = inevow.IRequest(ctx)
    try:
        unsafe = request.getCookie(COOKIE_KEY)
    except KeyError:
        return ''
    try:
        address = EmailAddress().coerce(unsafe, None)
    except annotate.InputError:
        return ''
    except annotate.ValidateError:
        return ''
    return address

compy.registerAdapter(_remembered,
                      context.RequestContext,
                      IEmailAddress)

class IAuthenticatedEmailAddress(Interface):
    pass

def _authenticated(ctx):
    sess = inevow.ISession(ctx)
    addr = sess.getComponent(IAuthenticatedEmailAddress)
    # None is special, need to return something else for "not known".
    if addr is None:
        return ''
    return addr
compy.registerAdapter(_authenticated,
                      context.RequestContext,
                      IAuthenticatedEmailAddress)

ADMINS = ['4dmin@example.com', 'oldbeard@example.net'] #TODO unhardcode

class ICurrentList(Interface):
    pass
# None is special, need to return something else for "not known".
compy.registerAdapter(lambda _: '',
                      context.WebContext,
                      ICurrentList)

def isAdmin(ctx):
    address = IAuthenticatedEmailAddress(ctx)
    return address in ADMINS

def render_ifAdmin(self, ctx, data):
    return render_if(ctx, isAdmin(ctx))

def isOwner(ctx):
    address = IAuthenticatedEmailAddress(ctx)
    if not address:
        return False
    ml = ICurrentList(ctx)
    if ml == '':
        return False
    d = ml.getOwners()
    def _cb(owners, address):
        return address in owners
    d.addCallback(_cb, address)
    return d

def render_ifOwner(self, ctx, data):
    d = defer.maybeDeferred(isAdmin, ctx)
    def _gotAdmin(isAdm, ctx):
        if isAdm:
            return True
        else:
            return isOwner(ctx)
    d.addCallback(_gotAdmin, ctx)

    def _gotResult(r, ctx):
        return render_if(ctx, r)
    d.addCallback(_gotResult, ctx)
    return d

def render_statusmessage(self, ctx, data):
    try:
        status = inevow.IStatusMessage(ctx)
    except compy.CannotAdapt:
        return ctx.tag
    return ctx.tag.clear()[tags.div(class_='statusmessage')[status]]

def statusPrefix(orig, msg):
    if orig:
        msg = '%s: %s' % (msg, orig)
    return '%s.' % msg

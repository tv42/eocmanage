from zope.interface import Interface
import string, email.Utils
from nevow import context, compy, inevow
from formless import annotate
from eocmanage import eocinterface

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

#TODO get from cookie or session
# None is special, need to return something else for "not known".
compy.registerAdapter(lambda _: '',
                      context.WebContext,
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

class ICurrentListName(Interface):
    pass
# None is special, need to return something else for "not known".
compy.registerAdapter(lambda _: '',
                      context.WebContext,
                      ICurrentListName)

def isAdmin(ctx):
    address = IAuthenticatedEmailAddress(ctx)
    return address in ADMINS

def render_ifAdmin(self, ctx, data):
    return render_if(ctx, isAdmin(ctx))

def isOwner(ctx):
    address = IAuthenticatedEmailAddress(ctx)
    if not address:
        return False
    listname = ICurrentListName(ctx)
    if not listname:
        return False
    thelist = eocinterface.MailingList(listname)
    owners = thelist.getOwners()
    return address in owners

def render_ifOwner(self, ctx, data):
    return render_if(ctx, isAdmin(ctx) or isOwner(ctx))

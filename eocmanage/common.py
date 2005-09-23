import string, email.Utils
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

def render_ifAdmin(self, ctx, data):
    return render_if(ctx, True) #TODO unhardcode

def render_ifOwner(self, ctx, data):
    return render_if(ctx, True) #TODO unhardcode

from twisted.trial.util import wait
import os, shutil, errno
from eocmanage import eocinterface

# Everything in this file would need to go through sudo,
# except we never use real sudo for testing, and these
# things are _only_ used for testing. Never use any of
# this code outside test environments.

def getSite():
    asUser = os.environ.get('MOCKSUDO_WANT_TO_USER', None)
    site = eocinterface.EocSite(asUser=asUser)
    return site

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
    site = getSite()
    d = site.create(name, owners)
    wait(d)

def _line(f, line, msg=None):
    if msg is None:
        msg = "Line does not match"
    got = f.readline()
    assert got.endswith('\n'), "Line must end in newline: %r" % got
    got = got[:-1]
    assert got == line, "%s: got %r, wanted %r" % (msg, got, line)

def _eoc_confirm_subunsub_accept(subunsub, name, address):
    assert subunsub in ['subscribe', 'unsubscribe']
    assert '@' in name
    assert not name.startswith('.')
    assert '@' in address
    local, domain = name.split('@', 1)

    filename = os.path.join('dot-eoc',
                            'sent-mail',
                            '1')
    f = file(filename)

    _line(f, repr([
        '-oi', '-f',
        '%s-ignore@%s' % (local, domain),
        address,
        ]),
        "Arguments to sendmail do not match")
    _line(f, '')
    _line(f, "From: %s-help@%s" % (local, domain))
    _line(f, "To: %s" % address)

    replyto = f.readline()
    assert replyto.startswith("Reply-To: %s-" % local), \
           "Not a Reply-To line: %r" % replyto
    assert replyto.endswith("@%s\n" % domain), \
           "Wrong domain in Reply-To: %r" % replyto
    command = replyto[len("Reply-To: %s-" % local):-len("@%s\n" % domain)]

    if subunsub == 'subscribe':
        what = 'subscription'
    else:
        what = 'UNsubscription'
    _line(f, "Subject: Please confirm %s to %s" % (what, name))

    f.close()
    os.unlink(filename)

    # now reply to the confirmation request
    site = getSite()
    l = site.getList(name)
    env = {}
    env.update(os.environ)
    env['SENDER'] = 'not-same-as-before@example.com'
    d = l.messageToEoc(command=command,
                       message='Just do it.',
                       env=env)
    wait(d)

    # eoc has sent us a welcome message, eat it
    filename = os.path.join('dot-eoc',
                            'sent-mail',
                            '1')
    f = file(filename)

    _line(f, repr(['-oi', '-f',
                   '%s-ignore@%s' % (local, domain),
                   address]),
          "Arguments to sendmail do not match")
    _line(f, '')
    _line(f, "From: %s-help@%s" % (local, domain))
    _line(f, "To: %s" % address)
    if subunsub == 'subscribe':
        what = 'Welcome to'
    else:
        what = 'Goodbye from'
    _line(f, "Subject: %s %s" % (what, name))
    _line(f, "")

    f.close()
    os.unlink(filename)

def eoc_confirm_sub_accept(name, address):
    """
    Ensure list name has sent a subscription confirmation message to
    address, and confirm it.
    """
    return _eoc_confirm_subunsub_accept('subscribe', name, address)

def eoc_is_subscriber(name, address, want):
    assert '@' in name
    assert not name.startswith('.')
    site = getSite()
    l = site.getList(name)
    d = l.list()
    subscribers = wait(d)
    got = address in subscribers
    assert str(got) == str(want), "%r is subscriber: %s, wanted %s" % (
        address, got, want)


def eoc_confirm_unsub_accept(name, address):
    """
    Ensure list name has sent an unsubscription confirmation message
    to address, and confirm it.
    """
    return _eoc_confirm_subunsub_accept('unsubscribe', name, address)

__all__ = ['eoc_destroy',
           'eoc_create',
           'eoc_confirm_sub_accept',
           'eoc_confirm_unsub_accept',
           'eoc_is_subscriber',
           ]

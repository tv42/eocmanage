from twisted.trial.util import wait
import os, shutil, errno, re
from eocmanage import eocinterface

# Everything in this file would need to go through sudo,
# except we never use real sudo for testing, and these
# things are _only_ used for testing. Never use any of
# this code outside test environments.

def getSite(**kw):
    asUser = os.environ.get('MOCKSUDO_WANT_TO_USER', None)
    kw.setdefault('asUser', asUser)
    site = eocinterface.EocSite(**kw)
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
    from_ = f.readline()
    assert from_ in [
        # eoc v1.0.x
        "From: %s-help@%s\n" % (local, domain),
        # eoc v1.2.x
        "From: EoC <%s-help@%s>\n" % (local, domain),
        ], "Invalid From line: %r" % from_ 
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

    while True:
        line = f.readline()
        assert line, 'EOF before MIME separator.'
        if line.startswith(' - - - - - - - -'):
            # eoc 1.0.x
            break
        elif re.search('^--[0-9a-f]{32}/[0-9a-f]{32}$', line):
            # eoc 1.2.x
            # find second boundary
            while True:
                line = f.readline()
                assert line, 'EOF before second MIME separator.'
                if re.search('^--[0-9a-f]{32}/[0-9a-f]{32}$', line):
                    break
            _line(f, 'Content-type: message/rfc822')
            _line(f, 'Content-disposition: inline; filename=original.txt')
            break

    _line(f, '')
    _line(f, '')
    _line(f, '')

    _line(f, 'A request to %s the address %s' % (subunsub, address))
    if subunsub == 'subscribe':
        direction = 'to'
    else:
        direction = 'from'
    _line(f, '%s the mailing list %s' % (direction, name))
    line = f.readline()
    assert line.startswith('was received on ')
    line = f.readline()
    assert line.startswith('by the web application at ')
    line = f.readline()
    assert line.startswith('from the web client ')

    line = f.readline()
    if re.search('^--[0-9a-f]{32}/[0-9a-f]{32}--', line):
        # eoc 1.2.x
        pass
    elif line == '\n':
        # eoc 1.0.x
        pass
    else:
        assert line == '', 'Last line should be empty: %r' % line

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
    from_ = f.readline()
    assert from_ in [
        # eoc v1.0.x
        "From: %s-help@%s\n" % (local, domain),
        # eoc v1.2.x
        "From: EoC <%s-help@%s>\n" % (local, domain),
        ], "Invalid From line: %r" % from_ 
    _line(f, "To: %s" % address)
    if subunsub == 'subscribe':
        what = 'Welcome to'
    else:
        what = 'Goodbye from'
    _line(f, "Subject: %s %s" % (what, name))
    line = f.readline()
    if line == 'Content-type: text/plain; charset=us-ascii\n':
        # eoc 1.2.x
        _line(f, "")
    elif line == '\n':
        # eoc 1.0.x
        pass
    else:
        assert line == '', 'Header should end now: %r' % line

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

def eoc_set_config(name, variable, value):
    assert '@' in name
    assert not name.startswith('.')
    site = getSite()
    l = site.getList(name)
    d = l.setConfig(**{variable: value})
    r = wait(d)

__all__ = ['eoc_destroy',
           'eoc_create',
           'eoc_confirm_sub_accept',
           'eoc_confirm_unsub_accept',
           'eoc_is_subscriber',
           'eoc_set_config',
           ]

import os, time
from twisted.internet import defer
from nevow import inevow, loaders, rend, url, flat
from formless import iformless, annotate, webform
from eocmanage import zebra, common, i18n
from eocmanage.i18n import _
from eocmanage.common import EmailAddress

class MailingListForUser(rend.Fragment):
    def bind_subscribe(self, ctx):
        return annotate.MethodBinding(
            name='requestSubscribe',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('ctx', annotate.Context()),
                    annotate.Argument('address',
                                      EmailAddress(label=_('Address'))),
                    ],
                                      label=_('Request Subscription')),
            action=_('Subscribe'))

    def getRequestData(self, ctx):
        request = inevow.IRequest(ctx)
        return {
            'listname': self.original.listname,
            'date': time.strftime('%F %T %Z'),
            'uri': request.URLPath(),
            'clientIP': request.getClientIP(),
            }

    def requestSubscribe(self, ctx, address):
        common.rememberEmail(ctx, address)
        data = self.getRequestData(ctx)
        data['address'] = address
        message = """

A request to subscribe the address %(address)s
to the mailing list %(listname)s
was received on %(date)s
by the web application at %(uri)s
from the web client %(clientIP)s.
""" % data
        d = self.original.requestSubscribe(address, message)
        d.addCallback(common.statusPrefix,
                      _('Subscription confirmation request sent to %s') % address)
        return d

    def bind_unsubscribe(self, ctx):
        return annotate.MethodBinding(
            name='requestUnsubscribe',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('ctx', annotate.Context()),
                    annotate.Argument('address',
                                      EmailAddress(label=_('Address'))),
                    ],
                                      label=_('Request Unsubscription')),
            action=_('Unsubscribe'))

    def requestUnsubscribe(self, ctx, address):
        common.rememberEmail(ctx, address)
        data = self.getRequestData(ctx)
        data['address'] = address
        message = """

A request to unsubscribe the address %(address)s
from the mailing list %(listname)s
was received on %(date)s
by the web application at %(uri)s
from the web client %(clientIP)s.
""" % data
        d = self.original.requestUnsubscribe(address, message)
        d.addCallback(common.statusPrefix,
                      _('Unsubscription confirmation request sent to %s') %
                      address)
        return d

class MailingListForOwner(rend.Fragment):
    def bind_subscribe(self, ctx):
        return annotate.MethodBinding(
            name='subscribe',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('ctx', annotate.Context()),
                    annotate.Argument('address',
                                      EmailAddress(label=_('Address'))),
                    ],
                                      label=_('Subscribe Without Confirmation')),
            action=_('Add subscriber to list'))

    def subscribe(self, ctx, address):
        common.rememberEmail(ctx, address)
        d = self.original.subscribe(address)
        d.addCallback(common.statusPrefix, _('Subscribed %s') % address)
        return d

    def bind_unsubscribe(self, ctx):
        return annotate.MethodBinding(
            name='unsubscribe',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('ctx', annotate.Context()),
                    annotate.Argument('address',
                                      EmailAddress(label=_('Address'))),
                    ],
                                      label=_('Unsubscribe Without Confirmation')),
            action=_('Remove subscriber from list'))

    def unsubscribe(self, ctx, address):
        common.rememberEmail(ctx, address)
        d = self.original.unsubscribe(address)
        d.addCallback(common.statusPrefix, _('Unsubscribed %s') % address)
        return d

    EDIT_RADIO_LABELS = {
        'free': _('Free'),
        'moderated': _('Moderated'),
        'auto': _('Automatic'),
        }
    def stringifyToLabel(self, val):
        return self.EDIT_RADIO_LABELS.get(val, val)

    def bind_edit(self, ctx):
        return annotate.MethodBinding(
            name='edit',
            typeValue=annotate.Method(arguments=[
            annotate.Argument('ctx', annotate.Context()),
            annotate.Argument('subscription',
                              annotate.Radio(choices=['free',
                                                      'moderated'],
                                             stringify=self.stringifyToLabel,
                                             label=_('Subscription'))),
            annotate.Argument('posting',
                              annotate.Radio(choices=['free',
                                                      'auto',
                                                      'moderated'],
                                             stringify=self.stringifyToLabel,
                                             label=_('Posting'))),
            annotate.Argument('mail-on-subscription-changes',
                              annotate.Boolean(
            label=_('Notify owners on subscription changes'))),
            annotate.Argument('mail-on-forced-unsubscribe',
                              annotate.Boolean(
            label=_('Notify owners on forced unsubscribe'))),
            annotate.Argument('description',
                              annotate.String(null='',
                                              label=_('Description'))),
            ],
                                      label=_('Edit')),
            action=_('Edit'))

    def edit(self, ctx, **kw):
        d = self.original.getConfig('subscription', 'posting',
                                    'mail-on-subscription-changes',
                                    'mail-on-forced-unsubscribe',
                                    'description')
        d.addCallback(self.__edit, ctx, **kw)
        return d

    def __edit(self, cfg, ctx, **kw):
        old = {}
        (old['subscription'],
         old['posting'],
         old['mail-on-subscription-changes'],
         old['mail-on-forced-unsubscribe'],
         old['description']) = cfg

        for k,v in kw.items():
            oldVal = old.get(k, None)
            if (oldVal is not None
                and oldVal == v):
                # not changed
                del kw[k]

        if not kw:
            return _('Settings not changed.')

        def status(kw, old):
            keys = kw.keys()
            keys.sort()

            for k in keys:
                # TODO can't do _('foo %s bar') % _('quux'),
                # so we flatten things manually

                oldVal = old.get(k, None)
                if oldVal is not None:
                    oldVal = flat.ten.flatten(self.stringifyToLabel(oldVal),
                                              ctx)

                newVal = kw.get(k, None)
                if newVal is not None:
                    newVal = flat.ten.flatten(self.stringifyToLabel(newVal),
                                              ctx)

                # TODO translate/humanfriendlify k

                yield _('changed %(key)s from %(old)s to %(new)s') % {
                    'key': k,
                    'old': oldVal,
                    'new': newVal,
                    }

        def commaify(iterable):
            """Put add commas to sequence to separate multiple rounds."""
            iterable = iter(iterable)
            try:
                first = iterable.next()
            except StopIteration:
                return
            yield first
            for item in iterable:
                yield ', '
                yield item

        d = self.original.edit(**kw)
        d.addCallback(common.statusPrefix,
                      _('Edited settings: '),
                      commaify(status(kw, old)))
        return d

class MailingListForAdmin(rend.Fragment):
    def bind_destroy(self, ctx):
        return annotate.MethodBinding(
            name='destroy',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('ctx', annotate.Context()),
                    ],
                                      label=_('Destroy')),
            action=_('Destroy'))

    def destroy(self, ctx):
        u = url.URL.fromContext(ctx)
        request = inevow.IRequest(ctx)
        request.setComponent(iformless.IRedirectAfterPost, u.curdir())
        d = self.original.destroy()
        d.addCallback(common.statusPrefix, _('Destroyed list %s') % self.original.listname)
        return d

class WebMailingList(rend.Page):
    docFactory = loaders.xmlfile('list.html',
                                 templateDir=os.path.split(os.path.abspath(__file__))[0])


    def __init__(self, *a, **kw):
        rend.Page.__init__(self, *a, **kw)
        self.remember(self.original, common.ICurrentList)

    def data_name(self, ctx, data):
        return self.original.listname

    def configurable_user(self, ctx):
        return MailingListForUser(self.original)

    def render_form_user(self, ctx, data):
        address = common.IEmailAddress(ctx)
        bindingDefaults = {}
        bindingDefaults.setdefault('subscribe', {})
        bindingDefaults.setdefault('unsubscribe', {})
        if not address:
            d = defer.succeed(bindingDefaults)
        else:
            # TODO want __contains__, not iteration of everything
            d=self.original.list()
            def _gotMembers(subs, bindingDefaults):
                if address not in subs:
                    bindingDefaults['subscribe']['address'] = address
                else:
                    bindingDefaults['unsubscribe']['address'] = address
                return bindingDefaults
            d.addCallback(_gotMembers, bindingDefaults)

        def _gotDefaults(bindingDefaults, ctx):
            return ctx.tag[
                webform.renderForms('user',
                                    bindingDefaults=bindingDefaults,
                                    ),
                ]
        d.addCallback(_gotDefaults, ctx)
        return d

    def configurable_owner(self, ctx):
        return MailingListForOwner(self.original)

    def render_form_owner(self, ctx, data):
        d = self.original.getConfig('subscription',
                                    'posting',
                                    'mail-on-subscription-changes',
                                    'mail-on-forced-unsubscribe',
                                    'description')

        def _cb(cfg, ctx):
            bindingDefaults = {}
            bindingDefaults.setdefault('edit', {})
            bindingDefaults.setdefault('subscribe', {})
            bindingDefaults.setdefault('unsubscribe', {})
            (bindingDefaults['edit']['subscription'],
             bindingDefaults['edit']['posting'],
             bindingDefaults['edit']['mail-on-subscription-changes'],
             bindingDefaults['edit']['mail-on-forced-unsubscribe'],
             bindingDefaults['edit']['description'],
             ) = cfg

            return ctx.tag[
                webform.renderForms('owner',
                                    bindingDefaults=bindingDefaults,
                                    ),
                ]
        d.addCallback(_cb, ctx)
        return d

    def configurable_admin(self, ctx):
        return MailingListForAdmin(self.original)

    def render_form_admin(self, ctx, data):
        return ctx.tag[
            webform.renderForms('admin'),
            ]

    def data_list(self, ctx, data):
        return self.original.list()

    render_if = lambda self,ctx,data: common.render_if(ctx,data)
    render_ifOwner = common.render_ifOwner
    render_ifAdmin = common.render_ifAdmin

    render_zebra = zebra.zebra()
    render_statusmessage = common.render_statusmessage

    def data_description(self, ctx, data):
        return self.original.getConfig('description')

    render_i18n = i18n.render()


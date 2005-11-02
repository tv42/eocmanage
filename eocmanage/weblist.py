import os
from twisted.internet import defer
from nevow import inevow, loaders, rend, url
from formless import iformless, annotate, webform
from eocmanage import zebra, common
from eocmanage.common import EmailAddress

class MailingListForUser(rend.Fragment):
    def bind_subscribe(self, ctx):
        return annotate.MethodBinding(
            name='requestSubscribe',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('ctx', annotate.Context()),
                    annotate.Argument('address', EmailAddress()),
                    ]),
            action='Subscribe')

    def requestSubscribe(self, ctx, address):
        common.rememberEmail(ctx, address)
        d = self.original.requestSubscribe(address)
        d.addCallback(common.statusPrefix,
                      'Subscription confirmation request sent to %s' % address)
        return d

    def bind_unsubscribe(self, ctx):
        return annotate.MethodBinding(
            name='requestUnsubscribe',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('ctx', annotate.Context()),
                    annotate.Argument('address', EmailAddress()),
                    ]),
            action='Unsubscribe')

    def requestUnsubscribe(self, ctx, address):
        common.rememberEmail(ctx, address)
        d = self.original.requestUnsubscribe(address)
        d.addCallback(common.statusPrefix,
                      'Unsubscription confirmation request sent to %s' %
                      address)
        return d

class MailingListForOwner(rend.Fragment):
    def bind_subscribe(self, ctx):
        return annotate.MethodBinding(
            name='subscribe',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('ctx', annotate.Context()),
                    annotate.Argument('address', EmailAddress()),
                    ]),
            action='Subscribe')

    def subscribe(self, ctx, address):
        common.rememberEmail(ctx, address)
        d = self.original.subscribe(address)
        d.addCallback(common.statusPrefix, 'Subscribed %s' % address)
        return d

    def bind_unsubscribe(self, ctx):
        return annotate.MethodBinding(
            name='unsubscribe',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('ctx', annotate.Context()),
                    annotate.Argument('address', EmailAddress()),
                    ]),
            action='Unsubscribe')

    def unsubscribe(self, ctx, address):
        common.rememberEmail(ctx, address)
        d = self.original.unsubscribe(address)
        d.addCallback(common.statusPrefix, 'Unsubscribed %s' % address)
        return d

    def bind_edit(self, ctx):
        return annotate.MethodBinding(
            name='edit',
            typeValue=annotate.Method(arguments=[
            annotate.Argument('subscription',
                              annotate.Radio(choices=['free',
                                                      'moderated'])),
            annotate.Argument('posting',
                              annotate.Radio(choices=['free',
                                                      'auto',
                                                      'moderated'])),
            annotate.Argument('mail-on-subscription-changes',
                              annotate.Boolean()),
            annotate.Argument('mail-on-forced-unsubscribe',
                              annotate.Boolean()),
            ]),
            action='Edit')

    def edit(self, **kw):
        d = self.original.getConfig('subscription', 'posting',
                                    'mail-on-subscription-changes',
                                    'mail-on-forced-unsubscribe')
        d.addCallback(self.__edit, **kw)
        return d

    def __edit(self, cfg, **kw):
        old = {}
        (old['subscription'],
         old['posting'],
         old['mail-on-subscription-changes'],
         old['mail-on-forced-unsubscribe']) = cfg

        for k,v in kw.items():
            oldVal = old.get(k, None)
            if (oldVal is not None
                and oldVal == v):
                # not changed
                del kw[k]

        if not kw:
            return 'Settings not changed.'

        def status(kw, old):
            keys = kw.keys()
            keys.sort()
            for k in keys:
                yield 'changed %(key)s from %(old)s to %(new)s' % {
                    'key': k,
                    'old': old.get(k, None),
                    'new': kw.get(k, None),
                    }
        d = self.original.edit(**kw)
        d.addCallback(common.statusPrefix, 'Edited settings: %(edits)s' % {
            'edits': ', '.join(status(kw, old)),
            })
        return d

class MailingListForAdmin(rend.Fragment):
    def bind_destroy(self, ctx):
        return annotate.MethodBinding(
            name='destroy',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('ctx', annotate.Context()),
                    ]),
            action='Destroy')

    def destroy(self, ctx):
        u = url.URL.fromContext(ctx)
        request = inevow.IRequest(ctx)
        request.setComponent(iformless.IRedirectAfterPost, u.curdir())
        d = self.original.destroy()
        d.addCallback(common.statusPrefix, 'Destroyed list %s' % self.original.listname)
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
                                    'mail-on-forced-unsubscribe')

        def _cb(cfg, ctx):
            bindingDefaults = {}
            bindingDefaults.setdefault('edit', {})
            bindingDefaults.setdefault('subscribe', {})
            bindingDefaults.setdefault('unsubscribe', {})
            (bindingDefaults['edit']['subscription'],
             bindingDefaults['edit']['posting'],
             bindingDefaults['edit']['mail-on-subscription-changes'],
             bindingDefaults['edit']['mail-on-forced-unsubscribe'],
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

    render_ifOwner = common.render_ifOwner
    render_ifAdmin = common.render_ifAdmin

    render_zebra = zebra.zebra()
    render_statusmessage = common.render_statusmessage


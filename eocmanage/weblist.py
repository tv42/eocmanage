import os
from zope.interface import implements
from nevow import inevow, loaders, rend, tags, url
from formless import iformless, annotate, webform
from eocmanage import eocinterface, zebra
from eocmanage.common import EmailAddress

class MailingListForUser(eocinterface.MailingList, rend.Fragment):
    def bind_subscribe(self, ctx):
        return annotate.MethodBinding(
            name='subscribe',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('address', EmailAddress()),
                    ]),
            action='Subscribe')
    def bind_unsubscribe(self, ctx):
        return annotate.MethodBinding(
            name='unsubscribe',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('address', EmailAddress()),
                    ]),
            action='Unsubscribe')

class MailingListForOwner(eocinterface.MailingList, rend.Fragment):
    def bind_edit(self, ctx):
        return [
            ('subscription', annotate.Radio(choices=['free',
                                                     'moderated'])),
            ('posting', annotate.Radio(choices=['free',
                                                'auto',
                                                'moderated'])),
            ]

class MailingListForAdmin(eocinterface.MailingList, rend.Fragment):
    def bind_destroy(self, ctx):
        return [('ctx', annotate.Context())]

    def destroy(self, ctx):
        u = url.URL.fromContext(ctx)
        request = inevow.IRequest(ctx)
        request.setComponent(iformless.IRedirectAfterPost, u.parentdir())
        d = eocinterface.MailingList.destroy(self)
        return d

class WebMailingList(rend.Page):
    docFactory = loaders.xmlfile('list.html',
                                 templateDir=os.path.split(os.path.abspath(__file__))[0])


    def __init__(self, listname, *a, **kw):
        self.listname = listname
        rend.Page.__init__(self, *a, **kw)

    def data_name(self, ctx, data):
        return self.listname

    def configurable_user(self, ctx):
        return MailingListForUser(self.listname)

    def render_form_user(self, ctx, data):
        return ctx.tag[
            webform.renderForms('user'),
            ]

    def configurable_owner(self, ctx):
        return MailingListForOwner(self.listname)

    def render_form_owner(self, ctx, data):
        d = self.locateConfigurable(ctx, 'owner')
        def _cb(cf, ctx):
            bindingDefaults = {}
            bindingDefaults.setdefault('edit', {})
            bindingDefaults['edit']['subscription'] = cf.getSubscription()
            bindingDefaults['edit']['posting'] = cf.getPosting()
            return ctx.tag[
                webform.renderForms('owner',
                                    bindingDefaults=bindingDefaults,
                                    ),
                ]
        d.addCallback(_cb, ctx)
        return d

    def configurable_admin(self, ctx):
        return MailingListForAdmin(self.listname)

    def render_form_admin(self, ctx, data):
        return ctx.tag[
            webform.renderForms('admin'),
            ]

    def data_list(self, ctx, data):
        return eocinterface.MailingList(self.listname).list()

    def render_if(self, ctx, data): #TODO share
        r=ctx.tag.allPatterns(str(bool(data)))
        return ctx.tag.clear()[r]

    def render_ifOwner(self, ctx, data):
        return self.render_if(ctx, True) #TODO unhardcode, share

    render_zebra = zebra.zebra()

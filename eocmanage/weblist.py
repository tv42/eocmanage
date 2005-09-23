import os
from zope.interface import implements
from nevow import inevow, loaders, rend, tags, url
from formless import iformless, annotate, webform
from eocmanage import eocinterface
from eocmanage.common import EmailAddress

class IList(annotate.TypedInterface):
    def subscribe(self, address=EmailAddress()):
        pass
    subscribe = annotate.autocallable(subscribe)

    def unsubscribe(self, address=EmailAddress()):
        pass
    unsubscribe = annotate.autocallable(unsubscribe)

    def edit(self,
             subscription=annotate.Radio(choices=['free',
                                                  'moderated']),
             posting=annotate.Radio(choices=['free',
                                             'auto',
                                             'moderated']),
             ):
        pass
    edit = annotate.autocallable(edit)

    def destroy(self,
                ctx=annotate.Context()):
        pass
    destroy = annotate.autocallable(destroy)

class WebMailingList(eocinterface.MailingList,
                     rend.Page):
    implements(IList)
    docFactory = loaders.xmlfile('list.html',
                                 templateDir=os.path.split(os.path.abspath(__file__))[0])


    def __init__(self, listname, *a, **kw):
        eocinterface.MailingList.__init__(self, listname)
        rend.Page.__init__(self, *a, **kw)

    def data_name(self, ctx, data):
        return self.listname

    def render_form(self, ctx, data):
        formDefaults = ctx.locate(iformless.IFormDefaults)
        methodDefaults = formDefaults.getAllDefaults('edit')
        methodDefaults['subscription'] = self.getSubscription()
        methodDefaults['posting'] = self.getPosting()
        return webform.renderForms()

    def data_list(self, ctx, data):
        return self.list()

    def destroy(self, ctx):
        u = url.URL.fromContext(ctx)
        request = inevow.IRequest(ctx)
        request.setComponent(iformless.IRedirectAfterPost, u.parentdir())
        d = eocinterface.MailingList.destroy(self)
        return d

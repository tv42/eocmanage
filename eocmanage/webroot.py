import os
from zope.interface import implements
from nevow import rend, loaders, static
from formless import annotate, webform
from eocmanage import weblist, eocinterface, zebra
from eocmanage.common import EmailAddress

class EocManage(rend.Page):
    addSlash = True
    docFactory = loaders.xmlfile('main.html',
                                 templateDir=os.path.split(os.path.abspath(__file__))[0])


    child__style = static.File(os.path.join(os.path.split(os.path.abspath(__file__))[0],
                                            'style'))

    def __init__(self, *a, **kw):
        super(EocManage, self).__init__(*a, **kw)
        self.putChild('_freeform.css', webform.defaultCSS)

    def childFactory(self, ctx, name):
        if name.startswith('_'):
            return None
        elif '@' not in name:
            return None
        else:
            return weblist.WebMailingList(name)

    def data_list(self, ctx, data):
        return eocinterface.listLists()

    def render_form(self, ctx, data):
        return ctx.tag[webform.renderForms()]

    def _createFailed(self, reason, name):
        reason.trap(eocinterface.EocFailed)
        raise annotate.ValidateError({'name': reason.getErrorMessage()},
                                     formErrorMessage='Eoc failed',
                                     partialForm={'name': name})

    def bind_create(self, ctx):
        return annotate.MethodBinding(
            name='create',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('name', EmailAddress()),
                    ]),
            action='Create')

    def create(self, name):
        d = eocinterface.create(name, ['TODO'])
        d.addErrback(self._createFailed, name)
        return d

    def render_if(self, ctx, data): #TODO share
        r=ctx.tag.allPatterns(str(bool(data)))
        return ctx.tag.clear()[r]

    def render_ifAdmin(self, ctx, data):
        return self.render_if(ctx, True) #TODO unhardcode, share

    render_zebra = zebra.zebra()

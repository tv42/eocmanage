import os
from nevow import rend, loaders, static
from formless import annotate, webform
from eocmanage import weblist, eocinterface, zebra, common
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
            ml = self.original.getList(name)
            d = ml.exists()
            def cb(exists, ml):
                if exists:
                    return weblist.WebMailingList(ml)
                else:
                    return None
            d.addCallback(cb, ml)
            return d

    def data_list(self, ctx, data):
        return self.original.listLists()

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
        d = self.original.create(name, ['TODO'])
        d.addCallback(common.statusPrefix, 'Created list %s' % name)
        d.addErrback(self._createFailed, name)
        return d

    render_ifAdmin = common.render_ifAdmin

    render_zebra = zebra.zebra()
    render_statusmessage = common.render_statusmessage

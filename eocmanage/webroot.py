import os
from nevow import rend, loaders, static
from formless import annotate, webform
from eocmanage import weblist, eocinterface, zebra, common, i18n
from eocmanage.i18n import _
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
        d = self.original.listLists()
        def _cb(addresses):
            for address in addresses:
                ml = self.original.getList(address)
                d = ml.getConfig('description')
                yield {'address': address,
                       'description': d,
                       }
        d.addCallback(_cb)
        return d

    def render_form(self, ctx, data):
        return ctx.tag[webform.renderForms()]

    def _createFailed(self, reason, name):
        reason.trap(eocinterface.EocFailed)
        raise annotate.ValidateError({'name': reason.getErrorMessage()},
                                     formErrorMessage=_('Eoc failed'),
                                     partialForm={'name': name})

    def bind_create(self, ctx):
        return annotate.MethodBinding(
            name='create',
            typeValue=annotate.Method(arguments=[
                    annotate.Argument('name', EmailAddress(label=_('List address'))),
                    ],
                                      label=_('Create')),
            action=_('Create a New List'))

    def create(self, name):
        d = self.original.create(name, [self.original.getCommandAddress(name, 'ignore')])
        d.addCallback(common.statusPrefix, _('Created list %s') % name)
        d.addErrback(self._createFailed, name)
        return d

    render_if = lambda self,ctx,data: common.render_if(ctx,data)
    render_ifAdmin = common.render_ifAdmin

    render_zebra = zebra.zebra()
    render_statusmessage = common.render_statusmessage

    def data_adminPublicAddress(self, ctx, data):
        return self.original.adminPublicAddress

    render_i18n = i18n.render()

from zope.interface import implements
from nevow import rend, loaders, static, util, inevow
from formless import annotate, webform, iformless
from eocmanage import weblist, eocinterface, zebra, common, i18n, skin
from eocmanage.i18n import _
from eocmanage.common import EmailAddress

class EocManageFragment(rend.Fragment):
    docFactory = loaders.xmlfile(
        util.resource_filename('eocmanage', 'main.html'),
        pattern='thecontent')

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

    def data_isAdmin(self, ctx, data):
        address = common.IAuthenticatedEmailAddress(ctx)
        if not address:
            return False

        d = self.original.getAdminAddresses()
        def cb(admins, address):
            return address in admins
        d.addCallback(cb, address)
        return d

    render_zebra = zebra.zebra()
    render_statusmessage = common.render_statusmessage

    def data_adminPublicAddress(self, ctx, data):
        return self.original.getAdminPublicAddress()

    render_i18n = i18n.render()

class EocManage(object):
    implements(skin.ISkinnable,
               inevow.IRenderer,
               iformless.IConfigurableFactory)

    addSlash = True

    title = _('Overview of Mailing Lists')

    stylesheets = [
        '_freeform.css',
        '_style/eocmanage.css',
        ]

    def __init__(self, **kw):
        self.site = kw.pop('site')
        super(EocManage, self).__init__(**kw)

    def locateChild(self, ctx, segments):
        if segments[0] == '_style':
            return (static.File(util.resource_filename(
                'eocmanage.webroot', 'style')),
                    segments[1:])
        elif segments[0] == '_freeform.css':
            return webform.defaultCSS, segments[1:]
        elif segments[0].startswith('_'):
            return None, ()
        elif '@' not in segments[0]:
            return None, ()
        else:
            ml = self.site.getList(segments[0])
            d = ml.exists()
            def cb(exists, ml):
                if exists:
                    return weblist.WebMailingList(list=ml), segments[1:]
                else:
                    return None, ()
            d.addCallback(cb, ml)
            return d

    def rend(self, ctx, data):
        return EocManageFragment(self.site)

    def locateConfigurable(self, ctx, name):
        if name == '':
            return EocManageFragment(self.site)


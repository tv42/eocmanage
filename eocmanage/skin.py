from zope.interface import Interface, Attribute
from twisted.internet import defer
from twisted.python import components
from nevow import rend, loaders, tags, util, inevow
from formless import iformless

class ISkinnable(Interface):
    """
    A skinnable web application.

    Anything implementing ISkinnable must be
    adaptable to:

    - inevow.IRenderer: the actual content of the application

    - iformless.IConfigurableFactory: for formless integration

    ISkinnable does not inherit these in order to allow using adapters
    instead of having to directly provide the interfaces.

    """

    title = Attribute("""
    Title of the application.

    May be displayed in HTML <title> tag or some other header.
    """)

    stylesheets = Attribute("""
    List of filenames to include as CSS stylesheets.
    """)

    def locateChild(ctx, segments):
        """See nevow.inevow.IResource.locateChild"""
        pass

class DefaultSkin(rend.Page):
    docFactory = loaders.xmlfile(
        util.resource_filename('eocmanage', 'skin-default.html'))

    def __init__(self, *a, **kw):
        super(DefaultSkin, self).__init__(*a, **kw)
        self.addSlash = getattr(self.original, 'addSlash', False)

    def render_title(self, ctx, data):
        return ctx.tag.clear()[self.original.title]

    def render_head(self, ctx, data):
        def links(l):
            for filename in l:
                yield tags.link(rel="stylesheet",
                                type="text/css",
                                href=filename)
        return ctx.tag.clear()[links(self.original.stylesheets)]

    def render_content(self, ctx, data):
        return ctx.tag.clear()[self.original]

    def locateConfigurable(self, ctx, name):
        cf = iformless.IConfigurableFactory(self.original)
        return cf.locateConfigurable(ctx, name)

    def locateChild(self, ctx, segments):
        result = super(DefaultSkin, self).locateChild(ctx, segments)
        if result != rend.NotFound:
            return result
        locateChild = getattr(self.original, 'locateChild', lambda *a,**kw: (None, ()))
        d = defer.maybeDeferred(locateChild, ctx, segments)
        def cb((res, segs)):
            if (res is not None
                and ISkinnable.providedBy(res)):
                res = self.__class__(res)
            return res, segs
        d.addCallback(cb)
        return d

components.registerAdapter(DefaultSkin, ISkinnable, inevow.IResource)

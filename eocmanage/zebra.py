from nevow import compy, inevow

class IZebraStyle(compy.Interface):
    """Marker interface for zebra."""
    pass

def zebra(styles=['zebra-odd', 'zebra-even']):
    """
    Provide alternating background colors for e.g. zebra tables.

    @param styles: Two or more CSS class names to iterate.

    Use like this::

      render_zebra = weave.zebra()

      <table>
        <tr nevow:render="zebra"><td>foo</td></tr>
        <tr nevow:render="zebra"><td>bar</td></tr>
        <tr nevow:render="zebra"><td>baz</td></tr>
      </table>
    """
    styles = list(styles)
    def f(self, ctx, data):
        request = inevow.IRequest(ctx)
        state = IZebraStyle(request, styles)
        r = ctx.tag(class_="%s" % state[0])
        request.setComponent(IZebraStyle, state[1:]+state[:1])

        return r
    return f

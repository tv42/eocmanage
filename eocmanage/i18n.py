from nevow.i18n import Translator
from nevow.i18n import render as _render

_ = Translator(domain='eocmanage')

def render(**kw):
    kw.setdefault('translator', _)
    return _render(**kw)

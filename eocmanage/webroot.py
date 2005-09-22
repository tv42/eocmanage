import os
from zope.interface import implements
from nevow import rend, loaders
from formless import annotate, webform
from eocmanage import weblist, eocinterface
from eocmanage.common import EmailAddress

class IMain(annotate.TypedInterface):
    def create(self, name=EmailAddress()):
        #TODO verify we can handle it?
        pass
    create = annotate.autocallable(create)

class EocManage(rend.Page):
    implements(IMain)
    addSlash = True
    docFactory = loaders.xmlfile('main.html',
                                 templateDir=os.path.split(os.path.abspath(__file__))[0])


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
        return webform.renderForms()

    def create(self, name):
        return eocinterface.create(name,
                                   ['TODO'])

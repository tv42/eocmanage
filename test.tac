from twisted.application import service, strports
from nevow import appserver

from eocmanage import webroot

site = appserver.NevowSite(webroot.EocManage())
site.resource.addSlash = True

application = service.Application("examples")
svc = strports.service("8080", site)
svc.setServiceParent(application)

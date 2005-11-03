from twisted.application import service, strports
from nevow import appserver, inevow, i18n

from eocmanage import webroot, eocinterface
from eocmanage.test.util import webutil, listutil

eocSite = listutil.getSite(adminPublicAddress='listmaster@example.com')
root = webroot.EocManage(eocSite)
root.child_mockauth = webutil.MockAuth()
#root.remember(['fi'], inevow.ILanguages)

site = appserver.NevowSite(root)
site.resource.addSlash = True

site.remember(i18n.I18NConfig(localeDir='build/locale'))


application = service.Application("examples")
svc = strports.service("8080", site)
svc.setServiceParent(application)

############################################################################
import sys, trace
class Coverage(service.Service):
    def startService(self):

        # begin monkey patch --------------------------- 
        def find_executable_linenos(filename):
            """Return dict where keys are line numbers in the line number table."""
            #assert filename.endswith('.py') # YOU BASTARDS
            try:
                prog = open(filename).read()
                prog = '\n'.join(prog.splitlines()) + '\n'
            except IOError, err:
                sys.stderr.write("Not printing coverage data for %r: %s\n" % (filename, err))
                sys.stderr.flush()
                return {}
            code = compile(prog, filename, "exec")
            strs = trace.find_strings(filename)
            return trace.find_lines(code, strs)

        trace.find_executable_linenos = find_executable_linenos
        # end monkey patch ------------------------------

        service.Service.startService(self)
        self.tracer = trace.Trace(count=1, trace=0)
        sys.settrace(self.tracer.globaltrace)

    def stopService(self):
        sys.settrace(None)
        results = self.tracer.results()
        results.write_results(show_missing=1,
                              summary=False,
                              coverdir='coverage')
        service.Service.stopService(self)

svc = Coverage()
#svc.setServiceParent(application)
############################################################################

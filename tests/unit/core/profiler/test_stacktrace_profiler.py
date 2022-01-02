import threading
import pytest

from flask import request
from werkzeug.routing import Rule

from flask_monitoringdashboard.core.cache import init_cache
from flask_monitoringdashboard.core.profiler import StacktraceProfiler


@pytest.mark.usefixtures('request_context')
def test_after_run(endpoint, config):
    def my_func():
        print("VERY NICE FUNCTION")

    setattr(my_func, "original", my_func)
    config.app.url_map.add(Rule('/', endpoint=endpoint.name))
    config.app.view_functions[endpoint.name] = my_func
    init_cache()
    request.environ['REMOTE_ADDR'] = '127.0.0.1'
    current_thread = threading.current_thread().ident
    ip = request.environ['REMOTE_ADDR']
    thread = StacktraceProfiler(current_thread, endpoint, ip, group_by=None)
    thread._keeprunning = False
    thread.run()

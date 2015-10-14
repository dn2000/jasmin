import logging
import pickle
import time
from logging.handlers import TimedRotatingFileHandler
from twisted.spread import pb
from jasmin.tools.eval import CompiledNode

LOG_CATEGORY = "jasmin-interceptor"

class InterceptorPB(pb.Avatar):
    def setConfig(self, InterceptorPBConfig):
        self.config = InterceptorPBConfig

        # Set up a dedicated logger
        self.log = logging.getLogger(LOG_CATEGORY)
        if len(self.log.handlers) != 1:
            self.log.setLevel(self.config.log_level)
            handler = TimedRotatingFileHandler(filename=self.config.log_file,
                when = self.config.log_rotate)
            formatter = logging.Formatter(self.config.log_format, self.config.log_date_format)
            handler.setFormatter(formatter)
            self.log.addHandler(handler)
            self.log.propagate = False

        self.log.info('Interceptor configured and ready.')

    def setAvatar(self, avatar):
        if type(avatar) is str:
            self.log.info('Authenticated Avatar: %s' % avatar)
        else:
            self.log.info('Anonymous connection')

        self.avatar = avatar

    def perspective_run(self, pyCode, routable):
        "Will execute pyCode with the routable argument"
        routable = pickle.loads(routable)
        smpp_status = 0

        try:
            self.log.debug('Running [%s]' % pyCode)
            self.log.debug('... with routable with pdu: %s' % routable.pdu)
            node = CompiledNode().get(pyCode)
            glo = {'routable': routable, 'smpp_status': smpp_status}

            # Run script and measure execution time
            start = time.clock()
            eval(node, {}, glo)
            end = time.clock()
        except Exception, e:
            self.log.error('Executing script on routable (from:%s, to:%s) returned: %s' % (
                routable.pdu.params['source_addr'],
                routable.pdu.params['destination_addr'],
                '%s: %s' % (type(e), e)
            ))
            return False
        else:
            delay = end - start
            if self.config.log_slow_script >= 0 and delay >= self.config.log_slow_script:
                self.log.warn('Execution delay [%ss] for script [%s].' % (delay, pyCode))

            if glo['smpp_status'] == 0:
                return pickle.dumps(glo['routable'])
            else:
                return glo['smpp_status']

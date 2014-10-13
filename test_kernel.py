from IPython.kernel.zmq.kernelbase import Kernel
import logging
from do_complete import Parser
import pprint


__version__ = '0.1'


class TestKernel(Kernel):
    implementation = 'test_kernel'
    implementation_version = __version__
    language = 'python'
    language_version = __version__
    banner = ''

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self.log.setLevel(logging.INFO)
        identifier_regex = r'[^\d\W]\w*'
        function_call_regex = r'([^\d\W][\w\.]*)\([^\)\()]*\Z'
        magic_prefixes = dict(magic='%', shell='!', help='?')
        magic_suffixes = dict(help='?')
        self.parser = Parser(identifier_regex, function_call_regex, magic_prefixes, magic_suffixes)

    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        if not code.strip():
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

        output = pprint.pformat(self.parser.parse_code(code))

        if not silent:
            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)


        return {'status': 'ok', 'execution_count': self.execution_count,
                'payload': [], 'user_expressions': {}}

    def do_complete(self, code, cursor_pos):

        # TODO: do something here
        start = 0
        end = 0
        matches = []

        return {'matches': matches, 'cursor_start': start,
                'cursor_end': end, 'metadata': dict(),
                'status': 'ok'}

if __name__ == '__main__':
    from IPython.kernel.zmq.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=TestKernel)

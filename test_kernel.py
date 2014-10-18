from IPython.kernel.zmq.kernelbase import Kernel
import logging
import pprint


__version__ = '0.2'


import re
import os


def _listdir(root):
    "List directory 'root' appending the path separator to subdirs."
    res = []
    root = os.path.expanduser(root)
    try:
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                name += os.sep
            res.append(name)
    except:
        pass  # no need to report invalid paths
    return res


def _complete_path(path=None):
    """Perform completion of filesystem path.
    http://stackoverflow.com/questions/5637124/tab-completion-in-pythons-raw-input
    """
    if not path or path == '.':
        return _listdir('.')
    dirname, rest = os.path.split(path)
    tmp = dirname if dirname else '.'
    res = [p for p in _listdir(tmp) if p.startswith(rest)]
    # more than one match, or single match which does not exist (typo)
    if len(res) > 1 or not os.path.exists(path):
        return res
    # resolved to a single directory, so return list of files below it
    if os.path.isdir(path):
        return [p for p in _listdir(path)]
    # exact file match terminates this completion
    return [path + ' ']


class Parser(object):

    def __init__(self, identifier_regex, function_call_regex, magic_prefixes,
                 magic_suffixes):
        self.identifier_regex = identifier_regex
        self.func_call_regex = function_call_regex + '\Z'
        self.magic_prefixes = magic_prefixes
        self.magic_suffixes = magic_suffixes
        self._default_regex = r'[^\d\W]\w*'

    def parse_code(self, code, start=0, end=-1):

        if end == -1:
            end = len(code)
        end = min(len(code), end)

        start = min(start, end)
        start = max(0, start)

        info = dict(code=code, magic=dict())

        info['magic'] = self.parse_magic(code[:end])

        id_regex = re.compile('(\{0}+{1}\Z|{2}\Z|\Z)'.format(
            self.magic_prefixes['magic'], self._default_regex,
            self.identifier_regex), re.UNICODE)

        info['lines'] = lines = code[start:end].splitlines()
        info['line_num'] = line_num = len(lines)

        info['line'] = line = lines[-1]
        info['column'] = col = len(lines[-1])

        obj = re.search(id_regex, line).group()

        full_obj = obj

        if obj:
            full_line = code.splitlines()[line_num - 1]
            rest = full_line[col:]
            match = re.match(id_regex, rest)
            if match:
                full_obj = obj + match.group()

        func_call = re.search(self.func_call_regex, line)
        if func_call and not obj:
            info['help_obj'] = func_call.groups()[0]
            info['help_col'] = line.index(obj) + len(obj)
            info['help_pos'] = end - len(line) + col
        else:
            info['help_obj'] = full_obj
            info['help_col'] = col
            info['help_pos'] = end

        info['obj'] = obj
        info['full_obj'] = full_obj

        info['start'] = end - len(obj)
        info['end'] = end
        info['pre'] = code[:start]
        info['mid'] = code[start: end]
        info['post'] = code[end:]

        info['path_matches'] = self.get_path_matches(info)
        return info

    def parse_magic(self, code):
        # find magic characters - help overrides any others
        info = {}
        prefixes = self.magic_prefixes
        suffixes = self.magic_suffixes

        id_regex = '|'.join([self._default_regex, self.identifier_regex])

        pre_magics = {}
        for (name, prefix) in prefixes.items():
            if name == 'shell':
                regex = r'(\%s+)( *)(%s)' % (prefix, id_regex)
            else:
                regex = r'(\%s+)(%s)' % (prefix, id_regex)
            match = re.search(regex, code, re.UNICODE)
            if match:
                pre_magics[name] = match.groups()

        post_magics = {}
        for (name, suffix) in suffixes.items():
            regex = r'(%s)(\%s+)' % (id_regex, suffix)
            match = re.search(regex, code, re.UNICODE)
            if match:
                post_magics[name] = match.groups()

        types = ['none', 'line', 'cell', 'sticky']

        if 'help' in pre_magics:
            info['name'] = 'help'
            pre, obj = pre_magics['help']
            info['type'] = types[len(pre)]
            info['index'] = code.index(pre + obj)

        elif 'help' in post_magics:
            info['name'] = 'help'
            obj, suf = post_magics['help']
            info['type'] = types[len(suf)]
            info['index'] = code.index(obj + suf)

        elif 'magic' in pre_magics:
            pre, obj = pre_magics['magic']
            info['type'] = types[len(pre)]
            info['name'] = obj
            info['index'] = code.index(pre + obj) + len(pre + obj)

        elif 'shell' in pre_magics:
            info['name'] = 'shell'
            pre, ws, obj = pre_magics['shell']
            info['type'] = types[len(pre)]
            info['index'] = code.index(pre + ws + obj) + len(pre + ws)

        else:
            return info

        info['rest'] = code[info['index']:].strip()

        if info['rest']:
            lines = info['rest'].splitlines()
            info['args'] = lines[0].strip()
            info['code'] = '\n'.join(lines[1:])
        else:
            info['args'] = ''
            info['code'] = ''
        return info

    def get_path_matches(self, info):
        """Get a list of matching paths.

        There are 3 types of matches:
        - start character and no quotes
        - quote mark followed by start character
        - single "word"
        """
        full_regex = r'([a-zA-Z/\.~][^\'"]*)\Z'
        full_regex = r'[\'"]{0}|{0}'.format(full_regex)
        single_regex = r'([a-zA-Z/\.~][^ ]*)\Z'

        line = info['line']
        obj = info['obj']

        full_path = re.search(full_regex, line)
        single_path = re.search(single_regex, line)

        matches = []

        if full_path:
            full_path = full_path.group()
            matches += _complete_path(full_path)

            if len(full_path) > len(obj) and ' ' in full_path:
                offset = len(full_path) - len(obj)
                if not obj:
                    offset -= 1
                matches = [m[offset:] for m in matches]

        if single_path:
            single_path = single_path.group()
            matches += _complete_path(single_path)

            if single_path.startswith('.'):
                new = []
                for m in matches:
                    if m.startswith('.'):
                        new.append(m[1:])
                    else:
                        new.append(m)
                matches = new

        if line.endswith('/'):
            matches = ['/' + m for m in matches]

        return list(set(matches))


class TestKernel(Kernel):
    implementation = 'test_kernel'
    implementation_version = __version__
    language = 'test'
    language_version = __version__
    banner = ''

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self.log.setLevel(logging.INFO)
        identifier_regex = r'[^\d\W]\w*'
        function_call_regex = r'([^\d\W][\w\.]*)\([^\)\()]*'
        magic_prefixes = dict(magic='%', shell='!', help='?')
        magic_suffixes = dict(help='?')
        self.parser = Parser(identifier_regex, function_call_regex,
                             magic_prefixes, magic_suffixes)

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        if not code.strip():
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

        output = pprint.pformat(self.parser.parse_code(code.strip()))

        if not silent:
            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)

        return {'status': 'ok', 'execution_count': self.execution_count,
                'payload': [], 'user_expressions': {}}

    def do_complete(self, code, cursor_pos):

        info = self.parser.parse_code(code)

        # TODO: add jedi parsing here

        matches = info['path_matches']

        return {'matches': matches, 'cursor_start': info['start'],
                'cursor_end': info['end'], 'metadata': dict(),
                'status': 'ok'}

if __name__ == '__main__':
    from IPython.kernel.zmq.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=TestKernel)

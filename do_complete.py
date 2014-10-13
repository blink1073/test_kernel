
"""
Completions should be case-sensitive

There are three potential objects:
- the token we are in the middle of
- partial version of that token
- the prior token representing a function call

For completions, use the partial object
For do_help, use the full token or the function call token

"""
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
        self.func_call_regex = function_call_regex
        self.magic_prefixes = magic_prefixes
        self.magic_suffixes = magic_suffixes
        self._default_regex = r'[^\d\W]\w*'

    def parse_code(self, code, start=0, end=-1):

        if not code:
            return

        if end == -1:
            end = len(code)
        end = min(len(code), end)

        start = min(start, end)
        start = max(0, start)

        info = dict(code=code, start=start, end=end, pre=code[:start],
                    mid=code[start:end], post=code[end:], magic=dict(),
                    complete_obj='', help_obj='')

        info['magic'] = self.parse_magic(code[:end])

        id_regex = re.compile('(\{0}+{1}|{2})'.format(
            self.magic_prefixes['magic'], self._default_regex,
            self.identifier_regex), re.UNICODE)

        tokens = re.split(id_regex, code[:end], re.UNICODE)

        if not tokens:
            return info

        info['lines'] = lines = code[start:end].splitlines()
        info['line_num'] = line_num = len(lines)

        info['line'] = line = lines[-1]
        info['column'] = col = len(lines[-1])

        tokens = re.findall(id_regex, line)
        if tokens and line.endswith(tokens[-1]):
            obj = tokens[-1]
        else:
            obj = ''

        full_obj = obj

        if obj:
            full_line = code.splitlines()[line_num - 1]
            rest = full_line[col:]
            match = re.match(id_regex, rest)
            if match:
                full_obj = obj + match.group()

        func_call = re.findall(self.func_call_regex, line)
        if func_call and not obj:
            info['help_obj'] = func_call[-1]
            info['help_col'] = line.index(obj) + len(obj)
            info['help_pos'] = end - len(line) + col
        else:
            info['help_obj'] = full_obj
            info['help_col'] = col
            info['help_pos'] = end

        info['obj'] = obj
        info['full_obj'] = full_obj

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


def test_parser():
    identifier_regex = r'[^\d\W]\w*'
    function_call_regex = r'([^\d\W][\w\.]*)\([^\)\()]*\Z'
    magic_prefixes = dict(magic='%', shell='!', help='?')
    magic_suffixes = dict(help='?')
    p = Parser(identifier_regex, function_call_regex, magic_prefixes,
               magic_suffixes)

    info = p.parse_code('import nump')
    assert info['help_obj'] == info['obj'] == 'nump'

    assert p.parse_code('%python impor', 0, 10)['magic']['name'] == 'python'
    assert p.parse_code('oct(a,')['help_obj'] == 'oct'
    assert p.parse_code('! ls')['magic']['name'] == 'shell'

    info = p.parse_code('%help %lsmagic', 0, 10)
    assert info['help_obj'] == '%lsmagic'
    assert info['obj'] == '%lsm'

    info = p.parse_code('%%python\nprint("hello, world!",')
    assert info['help_obj'] == 'print'

    info = p.parse_code('%lsmagic')
    assert info['help_obj'] == '%lsmagic'


def test_scheme_parser():
    identifier_regex = r'[^\d\W]\w*'
    function_call_regex = r'\(([^\d\W][\w\.]*)[^\)\()]*\Z'
    magic_prefixes = dict(magic='%', shell='!', help='?')
    magic_suffixes = dict(help='?')
    p = Parser(identifier_regex, function_call_regex, magic_prefixes,
               magic_suffixes)

    info = p.parse_code('(oct a b ')
    assert info['help_obj'] == 'oct'


def test_path_completions():
    if not os.name == 'nt':
        code = '/usr/bi'
        assert 'bin/' in _complete_path(code)
    code = '~/.bashr'
    assert '.bashrc' in _complete_path(code)
    for f in os.listdir('.'):
        if os.path.isdir(f):
            assert f + os.sep in _complete_path('.')
        else:
            assert f in _complete_path('.')

if __name__ == '__main__':
    test_parser()
    test_scheme_parser()
    test_path_completions()

    # TODO: adjust how these are used by the kernel and affected magics

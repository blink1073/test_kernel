
from test_kernel import Parser
import os

IDENTIFIER_REGEX = r'[^\d\W]\w*'
FUNC_CALL_REGEX = r'([^\d\W][\w\.]*)\([^\)\()]*\Z'
MAGIC_PREFIXES = dict(magic='%', shell='!', help='?')
MAGIC_SUFFIXES = dict(help='?')


def test_parser():
    p = Parser(IDENTIFIER_REGEX, FUNC_CALL_REGEX, MAGIC_PREFIXES,
               MAGIC_SUFFIXES)

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
    function_call_regex = r'\(([^\d\W][\w\.]*)[^\)\()]*\Z'
    p = Parser(IDENTIFIER_REGEX, function_call_regex, MAGIC_PREFIXES,
               MAGIC_PREFIXES)

    info = p.parse_code('(oct a b ')
    assert info['help_obj'] == 'oct'


def test_path_completions():
    p = Parser(IDENTIFIER_REGEX, FUNC_CALL_REGEX, MAGIC_PREFIXES,
               MAGIC_SUFFIXES)

    if not os.name == 'nt':
        code = '/usr/bi'
        assert 'bin/' in p.parse_code(code)['path_matches']
    code = '~/.bashr'
    assert '.bashrc' in p.parse_code(code)['path_matches']
    print(p.parse_code('.')['path_matches'])
    for f in os.listdir('.'):
        if os.path.isdir(f):
            if f.startswith('.'):
                f = f[1:]
            assert f + os.sep in p.parse_code('.')['path_matches']
        else:
            if f.startswith('.'):
                f = f[1:]
            assert f in p.parse_code('.')['path_matches']

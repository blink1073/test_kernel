
from test_kernel import Parser

identifier_regex = r'[^\d\W]\w*'
function_call_regex = r'([^\d\W][\w\.]*)\([^\)\()]*'
magic_prefixes = dict(magic='%', shell='!', help='?')
magic_suffixes = dict(help='?')
p = Parser(identifier_regex, function_call_regex,
           magic_prefixes, magic_suffixes)
print(p.parse_code('%hello %python'))

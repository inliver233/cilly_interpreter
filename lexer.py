'''
Cilly Lexer
'''

def error(src, msg):
    raise Exception(f'{src} : {msg}')

def mk_tk(tag, val=None):
    return [tag, val]

def tk_tag(t):
    return t[0]

def tk_val(t):
    return t[1]

def make_str_reader(s, err):
    cur = None
    pos = -1
    
    def peek(p=0):
        if pos + p >= len(s):
            return 'eof'
        else:
            return s[pos + p]
        
    def match(c):
        if c != peek():
            err(f'期望{c}, 实际{peek()}')
            
        return next()
    
    def next():
        nonlocal pos, cur
        
        old = cur
        pos = pos + 1
        if pos >= len(s):
            cur = 'eof'
        else:
            cur = s[pos]
            
        return old
    
    next()
    return peek, match, next

cilly_op1 = [
    '(',')','{','}',',',';',
    '+','-','*','/','%',
]

cilly_op2 = {
    '>': '>=',
    '<': '<=',
    '=': '==',
    '!': '!=',
    '&': '&&',
    '|': '||',
}

cilly_keywords = [
    'var','print','if','else', 'while','break','continue','return','fun',
    'true', 'false', 'null', 'define',
]

def cilly_lexer(prog):
    
    def err(msg):
        error('cilly lexer', msg)
        
    peek, match, next = make_str_reader(prog, err)
    
    def program():
        r = []
        
        while True:
            skip_ws()
            if peek() == 'eof':
                break
            
            r.append( token() )
        
        return r
    
    def skip_ws():
        while peek() in [' ', '\t','\r','\n']:
            next()
            
    def token():
        
        c = peek()
        
        if is_digit(c):
            return num()
        
        if c == '"':
            return string()
        
        if c == '_' or is_alpha(c):
            return id()
        
        if c in cilly_op1 :
            next()
            return mk_tk(c)
        
    
        if c in cilly_op2:
            next()
            if peek() == cilly_op2[c][1]:
                next()
                return mk_tk(cilly_op2[c])
            else:
                return mk_tk(c)
        
        err(f'非法字符{c}')
    
    def is_digit(c):
        return c >= '0' and c <= '9'
    
    def num():
        r = ''
        
        while is_digit(peek()):
            r = r + next()
            
        if peek() == '.':
            r = r + next()
            
            while is_digit(peek()):
                r = r + next()
                
        return mk_tk('num', float(r) if '.' in r else int(r))
    
    def string():
        match('"')
        
        r = ''
        while peek() != '"' and peek() != 'eof':
            r = r + next()
            
        match('"')
        
        return mk_tk('str', r)

    def is_alpha(c):
        return (c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z')
    
    def is_digit_alpha__(c):
        return c == '_' or is_digit(c) or is_alpha(c)
    
    def id():
        r = '' + next()
        
        while is_digit_alpha__(peek()):
            r = r + next()
            
        if r in cilly_keywords:
            return mk_tk(r)
        
        return mk_tk('id', r)
    
            
    return program()

__all__ = ['cilly_lexer', 'mk_tk', 'tk_tag', 'tk_val', 'error']
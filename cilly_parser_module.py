'''
cilly 语法

program : statement* EOF

statement
    : define_statement
    | assign_statement
    | print_statement
    | if_statement
    | while_statement
    | continue_statement
    | break_statement
    | return_statement
    | block_statement
    | expr_statement
    ;
    
define_statement
    : 'var' ID '=' expr ';'
    ;
    
assign_statement
    : ID '=' expr ';'
    ;
    
print_statement
    : 'print' '(' args? ')' ';'
    ;
    
args : expr (',' expr)* ;

if_statement
    : 'if' '(' expr ')' statement ('else' statement)?
    ;
    
while_statement
    : 'while' '(' expr ')' statement
    ;
    
continue_statement
    : 'continue' ';'
    ;
    
break_statement
    : 'break' ';'
    ;
    
return_statement
    : 'return' expr? ';'
    ;
    
block_statement
    : '{' statement* '}'
    ;
    
expr_statement:
    : expr ';'
    
expr
    : id | num | string | 'true' | 'false' | 'null'
    | '(' expr ')'
    | ('-' | '!') expr
    | expr ('+' | '-' | '*' | '/' | '==' | '!=' | '>' | '>=' | '<' | '<=' | '&&' | '||') expr
    | 'fun' '(' params? ')' block_statement
    | expr '(' args? ')'
    ;

表达式实现
方法1：改造文法

expr: logic_expr
logic_expr : rel_expr ('&&' rel_expr)*
rel_expr : add_expr ('>' add_expr)*
add_expr : mul_expr ('+' mul_expr)*
mul_expr : unary ('*' unary)*
unary : factor | '-' unary
factor : id | num | ....

方法2： pratt解析

   1     +    2
     30    40
     
   1     *    2
     50     60
     
   1  +   2   *  3
        40  50
        
   1  +   2  +   3
       40   30
comment : '#' 非换行符号 '\r'? '\n'
    
cilly 词法
program : token* 'eof'

token
    : id | num | string
    | 'true' | 'false' | 'null'
    | 'var' | 'if' | 'else' | 'while' | 'continue' | 'break' | 'return' | 'fun'
    | '(' | ')' | '{' | '}' | ','
    | '=' | '=='
    | '+' | '-' | '*' | '/'
    | '!' | '!='
    | '>' | '>='
    | '<' | '<='
    | '&&' | '||'
    ;
    
num : [0-9]+ ('.' [0-9]*)? 
string : '"' char* '"'
char : 不是双引号的字符
ws : (' ' | '\r' | '\n' | '\t)+

 
'''

from lexer import *

EOF = mk_tk('eof')

def make_token_reader(ts, err):
    pos = -1
    cur = None
    
    def peek(p=0):
        if pos + p >= len(ts):
            return 'eof'
        else:
            return tk_tag(ts[pos + p])
        
    def match(t):
        if peek() != t:
            err(f'期望{t},实际为{cur}')
            
        return next()
    
    def next():
        nonlocal pos, cur
        
        old = cur
        pos = pos + 1
        
        if pos >= len(ts):
            cur = EOF
        else:
            cur = ts[pos]
            
        return old
    next()
    
    return peek, match, next
        
def cilly_parser(tokens):
    def err(msg):
        error('cilly parser',  msg)
        
    peek, match, next = make_token_reader(tokens, err)
    
    def program():
        
        r = []
        
        while peek() != 'eof':
            r.append( statement() )
            
        return ['program', r]
    
    def statement():
        t = peek()

        if t == 'define':
            return define_stat(is_define=True)

        if t == 'var':
            return define_stat()
        
        if t == 'id' and peek(1) == '=':
            return assign_stat()
        
        if t == 'print':
            return print_stat()
        
        if t == 'if':
            return if_stat()
        
        if t == 'while':
            return while_stat()
        
        if t == 'break':
            return break_stat()
        
        if t == 'continue':
            return continue_stat()
        
        if t == 'return':
            return return_stat()
        
        if t == '{':
            return block_stat()
        
        return expr_stat()
    
    def define_stat(is_define=False):
        if is_define:
            match('define')
        else:
            match('var')
        
        id = tk_val ( match('id') )
        
        match('=')
        
        e = expr()
        
        match(';')
        
        return ['define', id, e]
    
    def assign_stat():
        id = tk_val( match('id') )
        
        match('=')
        
        e = expr()
        
        match(';')
        
        return ['assign', id, e]
    
    def print_stat():
        match('print')
        match('(')
        
        if peek() == ')':
            alist = []
        else:
            alist = args()
            
        match(')')
        match(';')
        
        return ['print', alist]
    
    def args():
        
        r = [expr()]
        
        while peek() == ',':
            match(',')
            r.append( expr() )
            
        return r
    
    def if_stat(): # if ( expr ) statement (else statment)?
        match('if')
        match('(')
        cond = expr()
        match(')')
        
        true_stat = statement()
        
        if peek() == 'else':
            match('else')
            false_stat = statement()
        else:
            false_stat = None
        return ['if', cond , true_stat, false_stat]
    
    def while_stat():
        match('while')
        match('(')
        cond = expr()
        match(')')
        body = statement()
        
        return ['while', cond, body]
    
    def continue_stat():
        match('continue')
        match(';')
        
        return ['continue']
    
    def break_stat():
        match('break')
        match(';')
        return ['break']
    
    def return_stat():
        match('return')
        
        if peek() != ';':
            e = expr()
        else:
            e = None
            
        match(';')
        
        return ['return', e]
    
    def block_stat():
        match('{')
        
        r = []
        
        while peek() != '}':
            r.append( statement() )
            
        match('}')
        return ['block', r]
        
    def expr_stat():
        e = expr()
        match(';')
        
        return ['expr_stat', e]
    
    def literal(bp=0):
        return next()
    
    def unary(bp):
        op = tk_tag( next() )
        e = expr(bp)
        
        return ['unary', op, e]
    
    def fun_expr(bp=0):
        match('fun')
        match( '(' )
        if peek() == ')':
            plist = []
        else:
            plist = params()
            
        match(')')
        body = block_stat()
        
        return ['fun', plist, body]
    
    def params():
        r = [ tk_val( match('id') )]
        
        while peek() == ',':
            match(',')
            r.append ( tk_val( match('id') ) )
            
        return r
    
    def parens(bp=0):
        match('(')
        
        e = expr()
        
        match(')')
        
        return e
    
    op1 = {
        'id': (100, literal),
        'num': (100, literal),
        'str': (100, literal),
        'true': (100, literal),
        'false': (100, literal),
        'null': (100, literal),
        '-': (85, unary),
        '!': (85, unary),
        'fun': (98, fun_expr),
        '(': (100, parens),
        
    }
    
    def get_op1_parser(t):
        if t not in op1:
            err(f'非法token: {t}')
            
        return op1[t]
    def binary(left, bp):
        
        op = tk_tag( next() )
        
        right = expr(bp)
        
        return ['binary', op, left, right]
    
    def call(fun_expr, bp=0):
        match('(')
        if peek() != ')':
            alist = args()
        else:
            alist = []
        match(')')
        return ['call', fun_expr, alist]
    
    op2 = {
        '*': (80, 81, binary),
        '/': (80, 81, binary),
        '%': (80, 81, binary),
        '+': (70, 71, binary),
        '-': (70, 71, binary),
        '>': (60, 61, binary),
        '>=': (60, 61, binary),
        '<': (60, 61, binary),
        '<=': (60, 61, binary),
        '==': (50, 51, binary),
        '!=': (50, 51, binary),
        '&&': (40, 41, binary),
        '||': (30, 31, binary),
        '(': (90, 91, call),
    }
    
    def get_op2_parser(t):
        if t not in op2:
            return (0,0,None)
        else:
            return op2[t]
            
    def expr(bp = 0):
        r_bp, parser = get_op1_parser( peek() )
        left = parser(r_bp)
        
        while True:
            l_bp, r_bp, parser = get_op2_parser( peek() )
            if parser == None or l_bp <= bp:
                break
            
            left = parser(left, r_bp)
        
        return left
    
    return program()



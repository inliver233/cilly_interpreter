from lexer import error

from vm import (
    mk_num,
    LOAD_CONST, LOAD_NULL, LOAD_TRUE, LOAD_FALSE, LOAD_VAR, STORE_VAR,
    PRINT_ITEM, PRINT_NEWLINE, JMP, JMP_TRUE, JMP_FALSE, POP,
    ENTER_SCOPE, LEAVE_SCOPE, CALL, RETURN, RETURN_VALUE, CALL_PRIMITIVE,
    UNARY_NEG, UNARY_NOT,
    BINARY_ADD, BINARY_SUB, BINARY_MUL, BINARY_DIV, BINARY_MOD, BINARY_POW,
    BINARY_EQ, BINARY_NE, BINARY_LT, BINARY_GE
)

# CillyCompiler class
class CillyCompiler:
    def __init__(self):
        self.code = []
        self.consts = []
        self.scopes = [[]]  # 初始作用域
        self.all_scopes = [self.scopes[0]]
        self.functions = []  # 函数表 [{name, params, entry_point, id}]
        self.current_function = None  # 当前正在编译的函数
        self.break_stack = []  # break语句跳转地址
        self.continue_stack = []  # continue语句跳转地址
        self.primitives = [] # 外部函数
        self.__init_visitors()

    def err(self, msg):
        error('cilly vm compiler', msg)

    def add_const(self, c):
        for i in range(len(self.consts)):
            if self.consts[i] == c:
                return i
        self.consts.append(c)
        return len(self.consts) - 1

    def get_next_emit_addr(self):
        return len(self.code)

    def emit(self, opcode, operand1=None, operand2=None):
        addr = self.get_next_emit_addr()
        self.code.append(opcode)
        if operand1 is not None:
            self.code.append(operand1)
        if operand2 is not None:
            self.code.append(operand2)
        return addr

    def backpatch(self, addr, operand1=None, operand2=None):
        if operand1 is not None:
            self.code[addr + 1] = operand1
        if operand2 is not None:
            self.code[addr + 2] = operand2

    def define_var(self, name):
        scope = self.scopes[-1]
        for i in range(len(scope)):
            if scope[i] == name:
                self.err(f'已定义变量: {name}')
        scope.append(name)
        return len(scope) - 1

    def lookup_var(self, name):
        for scope_i in range(len(self.scopes)):
            scope = self.scopes[-scope_i - 1]
            for index in range(len(scope)):
                if scope[index] == name:
                    return scope_i, index
        for func_id, func in enumerate(self.functions):
            if func["name"] == name:
                return -1, func_id
        
        if name in self.primitives:
            return -2, self.primitives.index(name)

        self.err(f'未定义变量：{name}')

    def first_pass(self, node):
        if node[0] == 'define':
            _, name, expr = node
            if expr[0] == 'fun':
                _, params, body = expr
                func_id = len(self.functions)
                self.functions.append({
                    "name": name,
                    "params": params,
                    "entry_point": -1,
                    "id": func_id
                })
        elif node[0] == 'program' or node[0] == 'block':
            _, statements = node
            for stmt in statements:
                self.first_pass(stmt)

    def compile(self, ast, primitives=[]):
        self.primitives = primitives
        self.first_pass(ast)
        self.visit(ast)
        return self.code, self.consts, self.all_scopes, self.functions

    def compile_program(self, node):
        _, statements = node
        self.visit(['block', statements])

    def compile_expr_stat(self, node):
        _, e = node
        self.visit(e)
        self.emit(POP)

    def compile_print(self, node):
        _, args = node
        for a in args:
            self.visit(a)
            self.emit(PRINT_ITEM)
        self.emit(PRINT_NEWLINE)

    def compile_literal(self, node):
        tag = node[0]
        if tag == 'null':
            self.emit(LOAD_NULL)
        elif tag == 'true':
            self.emit(LOAD_TRUE)
        elif tag == 'false':
            self.emit(LOAD_FALSE)
        elif tag in ['num', 'str']:
            index = self.add_const(node)
            self.emit(LOAD_CONST, index)

    def compile_unary(self, node):
        _, op, e = node
        self.visit(e)
        if op == '-':
            self.emit(UNARY_NEG)
        elif op == '!':
            self.emit(UNARY_NOT)
        else:
            self.err(f'非法一元运算符：{op}')

    def compile_binary(self, node):
        _, op, e1, e2 = node
        if op == '&&':
            self.visit(e1)
            addr1 = self.emit(JMP_FALSE, -1)
            self.visit(e2)
            addr2 = self.emit(JMP, -1)
            self.backpatch(addr1, self.get_next_emit_addr())
            self.emit(LOAD_FALSE)
            self.backpatch(addr2, self.get_next_emit_addr())
            return
        if op == '||':
            self.visit(e1)
            addr1 = self.emit(JMP_TRUE, -1)
            self.visit(e2)
            addr2 = self.emit(JMP, -1)
            self.backpatch(addr1, self.get_next_emit_addr())
            self.emit(LOAD_TRUE)
            self.backpatch(addr2, self.get_next_emit_addr())
            return
        if op in ['>', '<=']:
            self.visit(e2)
            self.visit(e1)
            if op == '>':
                self.emit(BINARY_LT)
            else:
                self.emit(BINARY_GE)
            return
        self.visit(e1)
        self.visit(e2)
        if op == '+': self.emit(BINARY_ADD)
        elif op == '-': self.emit(BINARY_SUB)
        elif op == '*': self.emit(BINARY_MUL)
        elif op == '/': self.emit(BINARY_DIV)
        elif op == '%': self.emit(BINARY_MOD)
        elif op == '^': self.emit(BINARY_POW)
        elif op == '==': self.emit(BINARY_EQ)
        elif op == '!=': self.emit(BINARY_NE)
        elif op == '<': self.emit(BINARY_LT)
        elif op == '>=': self.emit(BINARY_GE)
        else: self.err(f'非法二元运算符：{op}')

    def compile_if(self, node):
        _, cond, true_s, false_s = node
        self.visit(cond)
        addr1 = self.emit(JMP_FALSE, -1)
        self.visit(true_s)
        if false_s == None:
            self.backpatch(addr1, self.get_next_emit_addr())
        else:
            addr2 = self.emit(JMP, -1)
            self.backpatch(addr1, self.get_next_emit_addr())
            self.visit(false_s)
            self.backpatch(addr2, self.get_next_emit_addr())

    def compile_while(self, node):
        _, cond, body = node
        loop_start = self.get_next_emit_addr()
        self.visit(cond)
        exit_jmp = self.emit(JMP_FALSE, -1)
        old_break = self.break_stack
        old_continue = self.continue_stack
        self.break_stack = [exit_jmp]
        self.continue_stack = [loop_start]
        self.visit(body)
        self.emit(JMP, loop_start)
        loop_end = self.get_next_emit_addr()
        self.backpatch(exit_jmp, loop_end)
        self.break_stack = old_break
        self.continue_stack = old_continue

    def compile_break(self, node):
        if not self.break_stack:
            self.err("break语句必须在循环内部")
        self.emit(JMP, -1)
        self.break_stack.append(self.get_next_emit_addr() - 1)

    def compile_continue(self, node):
        if not self.continue_stack:
            self.err("continue语句必须在循环内部")
        self.emit(JMP, self.continue_stack[-1])

    def compile_block(self, node):
        _, statements = node
        new_scope = []
        self.scopes.append(new_scope)
        self.all_scopes.append(new_scope)
        addr = self.emit(ENTER_SCOPE, -1)
        for s in statements:
            self.visit(s)
        self.emit(LEAVE_SCOPE)
        self.backpatch(addr, len(self.scopes[-1]))
        self.scopes.pop()

    def compile_define(self, node):
        _, name, expr = node
        if expr[0] == 'fun':
            _, params, body = expr
            func_id = None
            for i, func in enumerate(self.functions):
                if func["name"] == name:
                    func_id = i
                    break
            if func_id is None:
                func_id = len(self.functions)
                self.functions.append({
                    "name": name, "params": params,
                    "entry_point": -1, "id": func_id
                })
            skip_addr = self.emit(JMP, -1)
            entry_point = self.get_next_emit_addr()
            self.functions[func_id]["entry_point"] = entry_point
            prev_function = self.current_function
            prev_scopes = self.scopes
            self.current_function = func_id
            param_scope = []
            self.scopes = [param_scope]
            self.all_scopes.append(param_scope)
            for param in params:
                self.define_var(param)
            self.visit(body)
            if len(self.code) == 0 or (self.code[-1] != RETURN and self.code[-1] != RETURN_VALUE):
                self.emit(RETURN)
            self.scopes = prev_scopes
            self.current_function = prev_function
            self.backpatch(skip_addr, self.get_next_emit_addr())
            index = self.define_var(name)
            self.emit(LOAD_CONST, self.add_const(mk_num(func_id)))
            self.emit(STORE_VAR, 0, index)
        else:
            self.visit(expr)
            index = self.define_var(name)
            self.emit(STORE_VAR, 0, index)

    def compile_assign(self, node):
        _, name, expr = node
        self.visit(expr)
        scope_i, index = self.lookup_var(name)
        if scope_i == -1:
            self.err(f'不能给函数名赋值: {name}')
        self.emit(STORE_VAR, scope_i, index)

    def compile_id(self, node):
        _, name = node
        scope_i, index = self.lookup_var(name)
        if scope_i == -1:
            self.emit(LOAD_CONST, self.add_const(mk_num(index)))
        else:
            self.emit(LOAD_VAR, scope_i, index)

    def compile_fun(self, node):
        self.err("匿名函数暂不支持")

    def compile_return(self, node):
        _, expr = node
        if self.current_function is None:
            self.err("return语句必须在函数内部")
        if expr is not None:
            self.visit(expr)
            self.emit(RETURN_VALUE)
        else:
            self.emit(RETURN)

    def compile_call(self, node):
        _, func_expr, args = node
        if func_expr[0] == 'id':
            _, name = func_expr
            func_id = None
            for i, func in enumerate(self.functions):
                if func.get("name") == name:
                    func_id = i
                    break
            if func_id is not None:
                for arg in reversed(args):
                    self.visit(arg)
                self.emit(CALL, func_id)
                return

            scope_i, prim_index = self.lookup_var(name)
            if scope_i == -2:
                for arg in reversed(args):
                    self.visit(arg)
                const_index = self.add_const(['str', name])
                self.emit(CALL_PRIMITIVE, const_index)
                return

        self.err(f'不支持的函数调用: {node}')

    def visit(self, node):
        tag = node[0]
        if tag not in self.visitors:
            self.err(f'非法ast节点: {tag}')
        v = self.visitors[tag]
        v(node)

    def __init_visitors(self):
        self.visitors = {
            'program': self.compile_program, 'expr_stat': self.compile_expr_stat,
            'print': self.compile_print, 'if': self.compile_if,
            'while': self.compile_while, 'break': self.compile_break,
            'continue': self.compile_continue, 'define': self.compile_define,
            'assign': self.compile_assign, 'block': self.compile_block,
            'unary': self.compile_unary, 'binary': self.compile_binary,
            'id': self.compile_id, 'fun': self.compile_fun,
            'return': self.compile_return, 'call': self.compile_call,
            'num': self.compile_literal, 'str': self.compile_literal,
            'true': self.compile_literal, 'false': self.compile_literal,
            'null': self.compile_literal,
        }

# cilly_vm_compiler function
def cilly_vm_compiler(ast, primitives=[]):
    compiler = CillyCompiler()
    return compiler.compile(ast, primitives)
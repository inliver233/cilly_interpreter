from lexer import error

# --- Migrated from cilly_parser_module.py (via compile.py) ---

def mk_num(i):
    return ['num', i]

def mk_str(s):
    return ['str', s]

def mk_proc(params, body, env):
    return ['proc', params, body, env]

def mk_primitive_proc(f):
    return ['primitive', f]

TRUE = ['bool', True]
FALSE = ['bool', False]

def mk_bool(b):
    return TRUE if b else FALSE

NULL = ['null', None]

def val(v):
    return v[1]

# --- Migrated from compile.py & yufa.py ---

# Bytecode definitions
LOAD_CONST = 1
LOAD_NULL = 2
LOAD_TRUE = 3
LOAD_FALSE = 4
LOAD_VAR = 5
STORE_VAR = 6
PRINT_ITEM = 7
PRINT_NEWLINE = 8
JMP = 9
JMP_TRUE = 10
JMP_FALSE = 11
POP = 12
ENTER_SCOPE = 13
LEAVE_SCOPE = 14
CALL = 15
RETURN = 16
RETURN_VALUE = 17
CALL_PRIMITIVE = 18
UNARY_NEG = 101
UNARY_NOT = 102
BINARY_ADD = 111
BINARY_SUB = 112
BINARY_MUL = 113
BINARY_DIV = 114
BINARY_MOD = 115
BINARY_POW = 116
BINARY_EQ = 117
BINARY_NE = 118
BINARY_LT = 119
BINARY_GE = 120

# OPS_NAME dictionary
OPS_NAME = {
    LOAD_CONST: ('LOAD_CONST', 2),
    LOAD_NULL: ('LOAD_NULL', 1),
    LOAD_TRUE: ('LOAD_TRUE', 1),
    LOAD_FALSE: ('LOAD_FALSE', 1),
    LOAD_VAR: ('LOAD_VAR', 3),
    STORE_VAR: ('STORE_VAR', 3),
    PRINT_ITEM: ('PRINT_ITEM', 1),
    PRINT_NEWLINE: ('PRINT_NEWLINE', 1),
    POP: ('POP', 1),
    ENTER_SCOPE: ('ENTER_SCOPE', 2),
    LEAVE_SCOPE: ('LEAVE_SCOPE', 1),
    JMP: ('JMP', 2),
    JMP_TRUE: ('JMP_TRUE', 2),
    JMP_FALSE: ('JMP_FALSE', 2),
    CALL: ('CALL', 2),
    RETURN: ('RETURN', 1),
    RETURN_VALUE: ('RETURN_VALUE', 1),
    CALL_PRIMITIVE: ('CALL_PRIMITIVE', 2),
    UNARY_NEG: ('UNARY_NEG', 1),
    UNARY_NOT: ('UNARY_NOT', 1),
    BINARY_ADD: ('BINARY_ADD', 1),
    BINARY_SUB: ('BINARY_SUB', 1),
    BINARY_MUL: ('BINARY_MUL', 1),
    BINARY_DIV: ('BINARY_DIV', 1),
    BINARY_MOD: ('BINARY_MOD', 1),
    BINARY_POW: ('BINARY_POW', 1),
    BINARY_EQ: ('BINARY_EQ', 1),
    BINARY_NE: ('BINARY_NE', 1),
    BINARY_LT: ('BINARY_LT', 1),
    BINARY_GE: ('BINARY_GE', 1),
}

# --- Migrated from yufa.py ---

class Stack:
    def __init__(self):
        self.stack = []
        self.push_count = 0
        self.pop_count = 0
        self.max_depth = 0

    def push(self, v):
        self.stack.append(v)
        self.push_count += 1
        self.max_depth = max(self.max_depth, len(self.stack))

    def pop(self):
        self.pop_count += 1
        return self.stack.pop()

    def top(self):
        return self.stack[-1]

    def empty(self):
        return len(self.stack) == 0

    def get_stats(self):
        return {
            'push_count': self.push_count,
            'pop_count': self.pop_count,
            'current_depth': len(self.stack),
            'max_depth': self.max_depth
        }

class CillyVM:
    def __init__(self, code, consts, scopes, functions=None, primitives=None, signals=None):
        self.code = code
        self.consts = consts
        self.scopes = list(scopes) # Get a mutable copy
        self.functions = functions if functions is not None else []
        self.primitives = primitives if primitives is not None else {}
        self.signals = signals if signals is not None else {}
        
        self.stack = Stack()
        self.call_stack = Stack()
        self.active_scopes = list(scopes)
        self.pc = 0

        self.ops = {
            LOAD_CONST: self.load_const, LOAD_NULL: self.load_null, LOAD_TRUE: self.load_true,
            LOAD_FALSE: self.load_false, LOAD_VAR: self.load_var, STORE_VAR: self.store_var,
            ENTER_SCOPE: self.enter_scope, LEAVE_SCOPE: self.leave_scope,
            PRINT_ITEM: self.print_item, PRINT_NEWLINE: self.print_newline, POP: self.pop_proc,
            JMP: self.jmp, JMP_TRUE: self.jmp_true, JMP_FALSE: self.jmp_false,
            CALL: self.call_proc, RETURN: self.return_proc, RETURN_VALUE: self.return_value_proc,
            CALL_PRIMITIVE: self.call_primitive_proc,
            UNARY_NEG: self.unary_op, UNARY_NOT: self.unary_op, BINARY_ADD: self.binary_op,
            BINARY_SUB: self.binary_op, BINARY_MUL: self.binary_op, BINARY_DIV: self.binary_op,
            BINARY_MOD: self.binary_op, BINARY_POW: self.binary_op, BINARY_EQ: self.binary_op,
            BINARY_NE: self.binary_op, BINARY_LT: self.binary_op, BINARY_GE: self.binary_op,
        }

    def err(self, msg):
        error('cilly vm', msg)

    def push(self, v):
        self.stack.push(v)

    def pop(self):
        return self.stack.pop()

    def load_const(self, pc):
        index = self.code[pc + 1]
        v = self.consts[index]
        self.push(v)
        return pc + 2

    def load_null(self, pc):
        self.push(NULL)
        return pc + 1

    def load_true(self, pc):
        self.push(TRUE)
        return pc + 1

    def load_false(self, pc):
        self.push(FALSE)
        return pc + 1

    def load_var(self, pc):
        scope_i = self.code[pc + 1]
        if scope_i >= len(self.active_scopes):
            self.err(f'作用域索引超出访问: {scope_i}')
        scope = self.active_scopes[-scope_i - 1]
        index = self.code[pc + 2]
        if index >= len(scope):
            self.err(f'load_var变量索引超出范围:{index}')
        self.push(scope[index])
        return pc + 3

    def store_var(self, pc):
        scope_i = self.code[pc + 1]
        if scope_i >= len(self.active_scopes):
            self.err(f'作用域索引超出访问: {scope_i}')
        scope = self.active_scopes[-scope_i - 1]
        index = self.code[pc + 2]
        if index >= len(scope):
            scope.extend([NULL] * (index - len(scope) + 1))
        scope[index] = self.pop()
        return pc + 3

    def enter_scope(self, pc):
        var_count = self.code[pc + 1]
        scope = [NULL for _ in range(var_count)]
        self.active_scopes.append(scope)
        return pc + 2

    def leave_scope(self, pc):
        self.active_scopes.pop()
        return pc + 1

    def print_item(self, pc):
        v = val(self.pop())
        print(v, end=' ')
        return pc + 1

    def print_newline(self, pc):
        print('')
        return pc + 1

    def pop_proc(self, pc):
        self.pop()
        return pc + 1

    def jmp(self, pc):
        return self.code[pc + 1]

    def jmp_true(self, pc):
        target = self.code[pc + 1]
        return target if self.pop() == TRUE else pc + 2

    def jmp_false(self, pc):
        target = self.code[pc + 1]
        return target if self.pop() == FALSE else pc + 2

    def unary_op(self, pc):
        v = val(self.pop())
        opcode = self.code[pc]
        if opcode == UNARY_NEG: self.push(mk_num(-v))
        elif opcode == UNARY_NOT: self.push(mk_bool(not v))
        else: self.err(f'非法一元opcode: {opcode}')
        return pc + 1

    def binary_op(self, pc):
        v2 = val(self.pop())
        v1 = val(self.pop())
        opcode = self.code[pc]
        if   opcode == BINARY_ADD: self.push(mk_num(v1 + v2))
        elif opcode == BINARY_SUB: self.push(mk_num(v1 - v2))
        elif opcode == BINARY_MUL: self.push(mk_num(v1 * v2))
        elif opcode == BINARY_DIV: self.push(mk_num(v1 / v2))
        elif opcode == BINARY_MOD: self.push(mk_num(v1 % v2))
        elif opcode == BINARY_POW: self.push(mk_num(v1 ** v2))
        elif opcode == BINARY_EQ:  self.push(mk_bool(v1 == v2))
        elif opcode == BINARY_NE:  self.push(mk_bool(v1 != v2))
        elif opcode == BINARY_LT:  self.push(mk_bool(v1 < v2))
        elif opcode == BINARY_GE:  self.push(mk_bool(v1 >= v2))
        else: self.err(f'非法二元opcode:{opcode}')
        return pc + 1

    def call_proc(self, pc):
        func_id = self.code[pc + 1]
        if self.functions is None or func_id >= len(self.functions):
            self.err(f'非法函数ID: {func_id}')
        func = self.functions[func_id]
        params = func.get("params", [])
        
        func_scope_names = None
        for s in self.scopes:
             if set(s) == set(params):
                 func_scope_names = s
                 break
        
        func_scope = [NULL] * len(func_scope_names)
        for i in range(len(params)):
             param_value = self.pop()
             func_scope[i] = param_value

        self.call_stack.push((pc + 2, self.active_scopes))
        self.active_scopes = self.active_scopes + [func_scope]
        return func["entry_point"]

    def return_proc(self, pc):
        if self.call_stack.empty(): self.err('函数返回栈为空')
        return_addr, prev_scopes = self.call_stack.pop()
        self.active_scopes = prev_scopes
        self.push(NULL)
        return return_addr

    def return_value_proc(self, pc):
        if self.call_stack.empty(): self.err('函数返回栈为空')
        return_value = self.pop()
        return_addr, prev_scopes = self.call_stack.pop()
        self.active_scopes = prev_scopes
        self.push(return_value)
        return return_addr

    def call_primitive_proc(self, pc):
        const_i = self.code[pc + 1]
        prim_name = val(self.consts[const_i])

        if prim_name not in self.signals:
            self.err(f"未知的 primitive 信号: {prim_name}")

        signal = self.signals[prim_name]

        # 从 PyQt 文档中获取参数数量的方法不如 inspect 直观，
        # 我们假设信号的签名与预期的 turtle 函数匹配。
        # 这是一个基于约定的方法，比运行时反射更简单。
        # 例如，forward_signal = pyqtSignal(float) 将有一个参数。
        # 我们将根据函数名硬编码参数数量。
        arg_counts = {
            "forward": 1, "backward": 1, "left": 1, "right": 1,
            "penup": 0, "pendown": 0, "pencolor": 1, "pensize": 1,
            "reset": 0, "speed": 1
        }
        num_args = arg_counts.get(prim_name, 0)

        args = [val(self.pop()) for _ in range(num_args)]
        args.reverse()

        # 发出信号而不是直接调用函数
        signal.emit(*args)

        # Primitive 调用在我们的模型中不返回值到 VM 栈上
        self.push(NULL)

        return pc + 2

    def get_opcode_proc(self, opcode):
        if opcode not in self.ops:
            self.err(f'非法opcode: {opcode}')
        return self.ops[opcode]

    def run(self):
        while self.pc < len(self.code):
            opcode = self.code[self.pc]
            proc = self.get_opcode_proc(opcode)
            self.pc = proc(self.pc)
        
        if not self.stack.empty():
            print("\nValues left on stack:")
            while not self.stack.empty():
                print(val(self.stack.pop()), end=' ')
            print()
            
        stats = self.stack.get_stats()
        print("\nStack Statistics:")
        print(f"Push operations: {stats['push_count']}")
        print(f"Pop operations: {stats['pop_count']}")
        print(f"Current stack depth: {stats['current_depth']}")
        print(f"Maximum stack depth: {stats['max_depth']}")

def cilly_vm(code, consts, scopes, functions=None, primitives=None, signals=None):
    vm = CillyVM(code, consts, scopes, functions, primitives, signals)
    vm.run()

def cilly_vm_dis(code, consts, all_scopes):
    def err(msg):
        error('cilly vm disassembler', msg)
    
    output = []
    pc = 0
    
    # Simulate the scope stack for disassembly
    dis_scopes = []
    if all_scopes:
        dis_scopes.append(all_scopes[0])
    
    next_scope_ptr = 1

    while pc < len(code):
        opcode = code[pc]
        name, size = OPS_NAME.get(opcode, (f'UNKNOWN {opcode}', 1))
        
        line = f'{pc:04d}\t{name}'

        if opcode == ENTER_SCOPE:
            if next_scope_ptr < len(all_scopes):
                dis_scopes.append(all_scopes[next_scope_ptr])
                next_scope_ptr += 1
            line += f' {code[pc + 1]}'

        elif opcode == LEAVE_SCOPE:
            if len(dis_scopes) > 1:
                dis_scopes.pop()

        elif opcode == LOAD_CONST:
            index = code[pc + 1]
            v = consts[index]
            line += f' {index} ({v})'

        elif opcode in [LOAD_VAR, STORE_VAR]:
            relative_scope_i = code[pc + 1]
            var_i = code[pc + 2]
            var_name = "???"
            try:
                target_scope = dis_scopes[-relative_scope_i - 1]
                var_name = target_scope[var_i]
            except IndexError:
                var_name = "Error:OOB"
            line += f' {relative_scope_i} {var_i} ({var_name})'

        elif opcode == CALL_PRIMITIVE:
            const_i = code[pc + 1]
            prim_name = consts[const_i]
            line += f' {const_i} ({val(prim_name)})'

        else:
            if size > 1:
                line += f' {code[pc + 1]}'
            if size > 2:
                line += f' {code[pc + 2]}'
        
        output.append(line)
        pc += size
        
    return "\n".join(output)
import json

class CillyToJsTranspiler:
    def __init__(self):
        self.js_code = ""
        self.indent_level = 0

    def transpile(self, ast):
        # The parser already returns a 'program' node: ['program', statements]
        # So we can directly visit the AST
        return self.visit(ast)

    def visit(self, node):
        node_type = node[0]
        method_name = f'translate_{node_type}'
        method = getattr(self, method_name, self.generic_visit)
        return method(node)

    def generic_visit(self, node):
        raise Exception(f'No translate_{node[0]} method for {node}')

    def _indent(self):
        return '    ' * self.indent_level

    def translate_program(self, node):
        # node[1] is a list of statements. Iterate over them.
        statements = []
        for statement in node[1]:
            statements.append(self.visit(statement))
        return ";\n".join(statements) + (";" if statements else "")

    def translate_statements(self, node):
        statements = []
        for statement in node[1]:
            statements.append(self._indent() + self.visit(statement))
        return ";\n".join(statements)

    def translate_num(self, node):
        return str(node[1])

    def translate_string(self, node):
        return json.dumps(node[1])

    def translate_id(self, node):
        return node[1]

    def translate_binary(self, node):
        _, op, left, right = node
        # Cilly's '==' and '!=' are 'eq' and 'ne'
        if op == 'eq':
            op = '==='
        elif op == 'ne':
            op = '!=='
        
        left_js = self.visit(left)
        right_js = self.visit(right)
        
        # Handle Cilly's 'and' and 'or' which are keywords in JS
        if op == 'and':
            op = '&&'
        elif op == 'or':
            op = '||'
            
        return f"({left_js} {op} {right_js})"

    def translate_unary(self, node):
        _, op, expr = node
        expr_js = self.visit(expr)
        if op == 'neg':
            return f"(-{expr_js})"
        # Cilly's 'not'
        elif op == 'not':
            return f"(!{expr_js})"
        return f"{op}{expr_js}"

    def translate_assign(self, node):
        _, var_name, expr = node
        expr_js = self.visit(expr)
        # This is for re-assignment, so no 'let'
        return f"{var_name} = {expr_js}"

    def translate_if(self, node):
        _, condition, then_branch, else_branch = node
        condition_js = self.visit(condition)
        
        then_code = self.visit(then_branch)
        
        js = f"if ({condition_js}) {{\n"
        self.indent_level += 1
        js += f"{then_code}\n"
        self.indent_level -= 1
        js += self._indent() + "}"
        
        if else_branch:
            js += " else {\n"
            self.indent_level += 1
            js += f"{self.visit(else_branch)}\n"
            self.indent_level -= 1
            js += self._indent() + "}"
            
        return js

    def translate_while(self, node):
        _, condition, body = node
        condition_js = self.visit(condition)
        
        js = f"while ({condition_js}) {{\n"
        self.indent_level += 1
        js += f"{self.visit(body)}\n"
        self.indent_level -= 1
        js += self._indent() + "}"
        return js

    def translate_define(self, node):
        # Handles both variable and function definitions
        if len(node) == 4: # Function: ['define', name, params, body]
            _, name, params, body = node
            params_js = ", ".join(params)
            
            # The body of a function is a 'statements' node
            body_js = self.visit(body)

            js = f"function {name}({params_js}) {{\n"
            self.indent_level += 1
            js += f"{body_js}\n"
            self.indent_level -= 1
            js += self._indent() + "}"
            return js
        else: # Variable: ['define', name, value]
            _, name, value_node = node
            value_js = self.visit(value_node)
            return f"var {name} = {value_js}"

    def translate_call(self, node):
        _, func_expr, args = node

        # If func_expr is an identifier node, extract the name
        if isinstance(func_expr, list) and func_expr[0] == 'id':
            func_name = func_expr[1]
        else:
            # For more complex expressions, visit them
            func_name = self.visit(func_expr)

        # A simple way to handle primitive calls like turtle
        if func_name in ['forward', 'backward', 'left', 'right', 'color', 'pen_down', 'pen_up']:
             func_name = f"turtle.{func_name}"

        args_js = [self.visit(arg) for arg in args]
        return f"{func_name}({', '.join(args_js)})"

    def translate_print(self, node):
        _, args = node
        args_js = [self.visit(arg) for arg in args]
        return f"console.log({', '.join(args_js)})"

    def translate_block(self, node):
        # A block contains a list of statements
        # ['block', [stmt1, stmt2, ...]]
        statements = []
        for statement in node[1]:
            statements.append(self._indent() + self.visit(statement))
        return ";\n".join(statements)

    def translate_return(self, node):
        _, value_node = node
        if value_node is None:
            return "return"
        return f"return {self.visit(value_node)}"

    def translate_expr_stat(self, node):
        # Expression statement: ['expr_stat', expr]
        _, expr = node
        return self.visit(expr)

    def translate_continue(self, node):
        # Continue statement: ['continue']
        return "continue"

    def translate_break(self, node):
        # Break statement: ['break']
        return "break"

    def translate_fun(self, node):
        # Function expression: ['fun', params, body]
        _, params, body = node
        params_js = ", ".join(params)

        js = f"function({params_js}) {{\n"
        self.indent_level += 1
        js += f"{self.visit(body)}\n"
        self.indent_level -= 1
        js += self._indent() + "}"
        return js

    def translate_true(self, node):
        return "true"

    def translate_false(self, node):
        return "false"

    def translate_null(self, node):
        return "null"

    def translate_str(self, node):
        # String literal: ['str', value]
        return json.dumps(node[1])

# Helper function to be called from other modules
def cilly_to_js(ast):
    transpiler = CillyToJsTranspiler()
    return transpiler.transpile(ast)
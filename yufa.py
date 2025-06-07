import sys
from lexer import cilly_lexer, error
from cilly_parser_module import cilly_parser
from compile import cilly_vm_compiler
import turtle
from vm import CillyVM, cilly_vm_dis

turtle_primitives = {
    "forward": turtle.forward,
    "backward": turtle.backward,
    "left": turtle.left,
    "right": turtle.right,
    "penup": turtle.penup,
    "pendown": turtle.pendown,
    "pencolor": turtle.pencolor,
    "speed": turtle.speed,
}

def run_test(name, program, primitives=None):
    print(f"\n=== Testing {name} ===")
    print("Program:")
    print(program)
    
    ts = cilly_lexer(program)
    ast = cilly_parser(ts)
    
    primitive_names = list(primitives.keys()) if primitives else []
    code, consts, scopes, functions = cilly_vm_compiler(ast, primitive_names)
    
    print("\nDisassembly with variable names:")
    cilly_vm_dis(code, consts, scopes)
    
    print("\nActual output:")
    vm_instance = CillyVM(code, consts, scopes, functions, primitives)
    vm_instance.run()

# Test cases collection
tests = {
    "Basic Arithmetic": '''
print(1 + 2 * 3);
print(4 * 5);
''',
    "Variable Scoping": '''
var x1 = 100;
{
    var x1 = 200;
    {
        var x1 = 300;
        print("inner x1", x1);
    }
    print("middle x1", x1);
}
print("outer x1", x1);
''',
    "Conditional Statements": '''
if(1 > 2)
    print(3);
else
    print(4);

if(1 > 2 && 5 > 4)
    print(30);
else
    print(42);
''',
    "Variable Name Display": '''
var a = 100;
var b = 200;
var c = a + b * 5;
print(c);
''',
    "Mutual Recursion": '''
define odd = fun(n){
  if(n == 0)
    return false;
  else
   return even(n-1);
};
define even = fun(n) {
 if(n==0)
   return true;
 else
   return odd(n-1);
};

print("even(3)=", even(3));
print("odd(3)=", odd(3));
''',
    "Fern Turtle Graphics": '''
define fern = fun(len) {
    if(len > 5){
        forward(len);
        right(10);
        fern(len - 10);
        left(40);
        fern(len - 10);
        right(30);
        backward(len);
    }
};

pencolor("green");
left(90);
penup();
backward(200);
pendown();
fern(100);
'''
}

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'gui':
        print("Starting GUI mode...")
        from gui import main as run_gui
        run_gui()
    else:
        print("Running command-line tests (currently disabled). Use 'python yufa.py gui' to start the IDE.")

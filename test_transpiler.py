#!/usr/bin/env python3
"""
Test script to verify the transpiler fixes
"""

from lexer import cilly_lexer
from cilly_parser_module import cilly_parser
from transpiler import cilly_to_js

def test_transpiler(name, code):
    print(f"\n=== Testing {name} ===")
    print(f"Cilly code:\n{code}")
    
    try:
        # 1. Lexical analysis
        tokens = cilly_lexer(code)
        print(f"Tokens: {tokens}")
        
        # 2. Syntax analysis
        ast = cilly_parser(tokens)
        print(f"AST: {ast}")
        
        # 3. Transpile to JavaScript
        js_code = cilly_to_js(ast)
        print(f"JavaScript code:\n{js_code}")
        
        print("✅ Success!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Test cases from our test suite
test_cases = [
    ("Simple print", "print(42);"),
    ("Variable declaration", "var x = 10;"),
    ("Assignment", "var x = 5; x = 10;"),
    ("Arithmetic", "print(1 + 2 * 3);"),
    ("If statement", "if(1 > 0) print(1); else print(0);"),
    ("While loop", "var i = 0; while(i < 3) { print(i); i = i + 1; }"),
    ("Function definition", "define add = fun(a, b) { return a + b; };"),
    ("Boolean literals", "print(true); print(false); print(null);"),
]

# Also test all the built-in test cases from yufa.py
from yufa import tests
builtin_test_cases = list(tests.items())

if __name__ == "__main__":
    print("=== Testing Basic Cases ===")
    success_count = 0
    total_count = len(test_cases)

    for name, code in test_cases:
        if test_transpiler(name, code):
            success_count += 1

    print(f"\n=== Testing Built-in Cases ===")
    builtin_success = 0
    builtin_total = len(builtin_test_cases)

    for name, code in builtin_test_cases:
        if test_transpiler(name, code):
            builtin_success += 1

    total_success = success_count + builtin_success
    total_tests = total_count + builtin_total

    print(f"\n=== Final Summary ===")
    print(f"Basic tests: {success_count}/{total_count}")
    print(f"Built-in tests: {builtin_success}/{builtin_total}")
    print(f"Overall: {total_success}/{total_tests}")

    if total_success == total_tests:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed.")

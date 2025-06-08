# Cilly 编译器项目综合分析文档

## 1. 项目概述

本项目实现了一个功能相对完整的 Cilly 编程语言的工具链，包括一个编译器、一个字节码虚拟机 (VM)、一个源码转换器 (Transpiler) 以及一个集成了所有功能的图形化 IDE。

Cilly 语言是一种类 C 的脚本语言，支持变量定义、基本算术运算、条件语句 (`if/else`)、循环 (`while`)、函数定义与调用、作用域以及 `break` 和 `continue` 等控制流。

### 1.1. 核心编译流程 (Cilly -> VM)

项目的主要执行路径是将 Cilly 源代码编译成自定义的字节码，然后在一个基于栈的虚拟机上运行。这个过程可以分解为以下几个关键阶段：

1.  **词法分析 (Lexing)**: [`lexer.py`](lexer.py) 将源代码文本分解成一系列的词法单元 (Tokens)，例如 `var`, `identifier`, `number`, `+` 等。
2.  **语法分析 (Parsing)**: [`cilly_parser_module.py`](cilly_parser_module.py) 接收词法单元流，并根据 Cilly 的语法规则构建一个抽象语法树 (AST)。AST 是源代码程序结构的树状表示。
3.  **编译 (Compilation)**: [`compile.py`](compile.py) 遍历 AST，并将其编译成一个为自定义虚拟机设计的、扁平的字节码指令列表。
4.  **执行 (Execution)**: [`vm.py`](vm.py) 中实现的虚拟机加载并逐条执行字节码，通过操作数栈和作用域链完成计算，最终输出结果。

### 1.2. 源码转换流程 (Cilly -> JavaScript)

除了编译到字节码，项目还提供了将 Cilly 代码直接转换成 JavaScript 的能力，这使得 Cilly 代码可以在浏览器等 JS 环境中运行。

1.  **词法分析与语法分析**: 与编译流程的前两步相同，首先生成 AST。
2.  **转译 (Transpiling)**: [`transpiler.py`](transpiler.py) 遍历 AST，并将每个 AST 节点直接翻译成等效的 JavaScript 代码字符串，最终生成一个完整的 `.js` 文件。

### 1.3. 图形用户界面 (GUI)

[`gui.py`](gui.py) 使用 PyQt5 框架构建了一个强大的集成开发环境 (IDE)，它将上述所有功能整合在一起，为开发者提供了一个一站式的平台来编写、运行、调试和转译 Cilly 代码。

---
## 2. 文件结构与模块关系分析

本节详细介绍项目中每个核心 `.py` 文件的功能，并阐明它们之间的数据流和依赖关系。

### 2.1. 数据流与控制流

整个项目的核心数据流可以被清晰地描绘成一个管道 (Pipeline)：

**源代码 (String)**
   `|`
   `V`
**`lexer.py`**
   `|` -> (生成)
   `V`
**词法单元列表 (List of Tokens)**
   `|`
   `V`
**`cilly_parser_module.py`**
   `|` -> (生成)
   `V`
**抽象语法树 (AST)**
   `|`
   `+------------------+`
   `|`                `|`
   `V`                `V`
**`compile.py`**      **`transpiler.py`**
   `|` -> (生成)      `|` -> (生成)
   `V`                `V`
**字节码 (Bytecode)**   **JavaScript 代码 (String)**
   `|`
   `V`
**`vm.py`**
   `|` -> (执行并输出)
   `V`
**运行结果**

[`gui.py`](gui.py) 作为上层应用，协调并驱动了上述所有模块。而 [`yufa.py`](yufa.py) 则扮演了命令行下的测试驱动角色，同样串联了从词法分析到虚拟机执行的完整流程。

---

### 2.2. 各模块深度分析

#### 2.2.1. `lexer.py` - 词法分析器

*   **核心职责**: 将原始的 Cilly 源代码字符串分解为一系列离散的 **词法单元 (Tokens)**。它是编译流程的第一步，为后续的语法分析提供规范化的输入。
*   **关键输出**: 词法单元列表。每个词法单元是一个 Python 列表，格式为 `[tag, value]`。
    *   `tag`: 字符串，代表词法单元的类型，如 `'num'`, `'id'`, `'if'`, `'+'`。
    *   `value`: 词法单元的实际值，例如数字 `123` 或标识符 `'myVar'`。对于关键字和操作符，此值通常为 `None`。
*   **核心实现**:
    *   `cilly_lexer(prog)`: 模块的主函数，接收源代码字符串 `prog`，返回词法单元列表。
    *   `make_str_reader(...)`: 一个巧妙的辅助函数，通过闭包创建了一个字符流读取器，提供了 `peek()` (预读) 和 `next()` (前进) 的能力。
    *   `token()`: 词法分析的核心逻辑。它根据当前字符的类型（数字、字母、操作符等）分发到不同的处理函数（如 `num()`, `id()`）来生成一个完整的词法单元。

*   **代码示例**:
    ```python
    # lexer.py:152
    def id():
        r = '' + next() # 读取标识符的第一个字符
        # 持续读取字母、数字或下划线
        while is_digit_alpha__(peek()):
            r = r + next()
        # 检查是否为关键字
        if r in cilly_keywords:
            return mk_tk(r) # 返回关键字 Token
        # 否则，返回一个标识符 Token
        return mk_tk('id', r)
    ```
    这段代码展示了如何识别一个标识符，并区分它是普通变量名还是一个语言的关键字。

---

#### 2.2.2. `cilly_parser_module.py` - 语法分析器

*   **核心职责**: 接收 `lexer.py` 生成的词法单元流，并根据 Cilly 语言的语法规则将其构造成一个 **抽象语法树 (AST)**。
*   **关键输出**: AST。这是一个嵌套的列表结构，代表了代码的层次化语法结构。
    *   **示例**: Cilly 代码 `var x = 10;` 会被解析成 `['define', 'x', ['num', 10]]`。
*   **核心实现**:
    *   **递归下降 (Recursive Descent)**: 用于解析各种语句 (Statements)。例如，`if_stat()` 函数递归地调用 `expr()` 和 `statement()` 来解析 `if` 语句的条件和分支。
    *   **Pratt 解析 (Pratt Parsing)**: 一种先进的表达式解析技术，用于优雅地处理操作符的优先级和结合性。
        *   `op1` 和 `op2` 字典定义了不同操作符的“绑定力”和对应的解析函数。
        *   `expr(bp)` 函数是 Pratt 解析的核心，它根据操作符的绑定力来决定表达式的求值顺序。
    *   `cilly_parser(tokens)`: 模块的主入口，驱动整个解析过程。

*   **代码示例**:
    ```python
    # cilly_parser_module.py:256
    def if_stat(): # if ( expr ) statement (else statment)?
        match('if')
        match('(')
        cond = expr() # 递归调用 expr() 解析条件表达式
        match(')')
        
        true_stat = statement() # 递归调用 statement() 解析 then 分支
        
        if peek() == 'else':
            match('else')
            false_stat = statement() # 递归调用 statement() 解析 else 分支
        else:
            false_stat = None
        return ['if', cond , true_stat, false_stat] # 构建 AST 节点
    ```
    此函数清晰地展示了递归下降如何将 `if` 语句的语法结构映射到 AST 节点的构造过程中。

---

#### 2.2.3. `compile.py` - 字节码编译器

*   **核心职责**: 将语法分析器生成的 AST 遍历并编译成自定义虚拟机的 **字节码 (Bytecode)**。
*   **关键输出**: 一个元组 `(code, consts, scopes, functions)`，包含：
    *   `code`: 字节码指令列表（整数序列）。
    *   `consts`: 常量池。
    *   `scopes`: 包含所有作用域信息的列表。
    *   `functions`: 函数信息表。
*   **核心实现**:
    *   `CillyCompiler` 类: 封装了整个编译逻辑。
    *   **访问者模式 (Visitor Pattern)**: `visit(node)` 方法根据 AST 节点的类型（如 `'if'`, `'binary'`）动态调用对应的编译函数（如 `compile_if`, `compile_binary`）。
    *   **两遍扫描 (Two-Pass Compilation)**:
        1.  `first_pass()`: 第一遍扫描，专门用于收集所有函数定义，以便处理函数的前向引用和相互递归。
        2.  `compile()`/`visit()`: 第二遍扫描，进行实际的字节码生成。
    *   **回填 (Backpatching)**: `emit()` 先发出一个带有占位符的跳转指令，`backpatch()` 则在确定了真正的目标地址后，回来修改这个占位符。这是处理 `if`, `while` 等控制流的关键技术。

*   **代码示例**:
    ```python
    # compile.py:181
    def compile_if(self, node):
        _, cond, true_s, false_s = node
        self.visit(cond) # 编译条件表达式，结果会留在栈顶
        # 发出条件跳转指令，如果栈顶为 false，则跳转。
        # 目标地址 -1 是一个占位符。
        addr1 = self.emit(JMP_FALSE, -1) 
        
        self.visit(true_s) # 编译 then 分支
        
        addr2 = self.emit(JMP, -1) # then 分支结束后，无条件跳转到 if 语句末尾
        
        # 回填 addr1：如果条件为 false，就跳到这里 (else 分支的开始)
        self.backpatch(addr1, self.get_next_emit_addr()) 
        
        if false_s:
            self.visit(false_s) # 编译 else 分支
            
        # 回填 addr2：then 分支执行完后，跳到这里 (整个 if 语句的结束)
        self.backpatch(addr2, self.get_next_emit_addr())
    ```

---

#### 2.2.4. `vm.py` - 字节码虚拟机

*   **核心职责**: 解释并执行 `compile.py` 生成的字节码。
*   **核心架构**: 一个典型的 **基于栈的虚拟机**。
    *   `pc` (Program Counter): 指令指针，指向下一条要执行的指令。
    *   `stack`: 操作数栈，用于存放计算的中间值和结果。
    *   `call_stack`: 函数调用栈，用于管理函数调用时的上下文（返回地址、作用域链）。
    *   `active_scopes`: 运行时的作用域链，用于变量的查找和存储。
*   **核心实现**:
    *   `CillyVM` 类: 封装了虚拟机的状态和执行逻辑。
    *   **执行循环 (Fetch-Decode-Execute Cycle)**: `run()` 方法中的 `while` 循环是虚拟机的“心脏”。它不断地获取指令、解码指令、执行指令，并更新 `pc`。
    *   **指令分发**: `run()` 循环通过 `self.ops` 字典将操作码映射到具体的执行方法上，如 `LOAD_CONST` -> `self.load_const()`。
*   **辅助功能**:
    *   `cilly_vm_dis(...)`: 一个功能强大的 **反汇编器**。它可以将字节码翻译回人类可读的汇编助记符，并且能够利用作用域信息显示变量名，是调试的利器。

*   **代码示例**:
    ```python
    # vm.py:247
    def binary_op(self, pc):
        v2 = val(self.pop()) # 从操作数栈顶弹出右操作数
        v1 = val(self.pop()) # 从操作数栈顶弹出左操作数
        opcode = self.code[pc] # 获取当前的操作码
        
        # 根据具体的操作码执行计算
        if   opcode == BINARY_ADD: self.push(mk_num(v1 + v2))
        elif opcode == BINARY_SUB: self.push(mk_num(v1 - v2))
        # ... 其他二元操作
        
        # 将计算结果压回栈顶
        return pc + 1 # 指令指针前进
    ```
    这段代码完美诠释了基于栈的计算模式：从栈获取操作数，本地计算，结果压回栈。

---

#### 2.2.5. `transpiler.py` - Cilly 到 JavaScript 的源码转换器

*   **核心职责**: 将 Cilly 的 AST 直接翻译成等效的 JavaScript 源代码字符串。
*   **核心实现**:
    *   与编译器类似，同样采用 **访问者模式** 遍历 AST。
    *   `CillyToJsTranspiler` 类中的每一个 `translate_...` 方法都负责将一个 Cilly 的 AST 节点翻译成一段 JS 代码字符串。
    *   它维护一个 `indent_level` 来生成格式优美、带缩进的 JS 代码。
*   **翻译映射示例**:
    *   Cilly `print(a, b)` -> JS `console.log(a, b)`
    *   Cilly `if (x > 10) { ... }` -> JS `if (x > 10) { ... }`
    *   Cilly `define my_fun = fun(a, b) { ... }` -> JS `function my_fun(a, b) { ... }`

---

#### 2.2.6. `gui.py` - 集成开发环境 (IDE)

*   **核心职责**: 使用 PyQt5 框架，为用户提供一个统一的图形界面来与 Cilly 工具链进行交互。
*   **核心功能**:
    *   **多线程架构**: 将耗时的编译和执行任务放在单独的 `QThread` 中完成，避免 UI 冻结。
    *   **信号与槽机制**: 使用 PyQt 的信号与槽机制在工作线程和主 UI 线程之间安全地传递数据（如编译结果、错误信息）和指令（如绘图命令）。
    *   **视图分离**: 将代码编辑、编译输出、字节码、AST 等不同信息展示在不同的选项卡中，界面清晰。
    *   **Turtle 绘图集成**: 通过信号与槽，将 VM 中对 `turtle` 函数的调用巧妙地解耦并代理到前台的 `TurtleCanvas` 组件上，实现了后台计算驱动前台动画的优雅模式。
    *   **JS 转译与执行集成**: 集成了 `transpiler.py` 和 `node.js` 的调用，提供了 Cilly 与 JS 的对比验证功能。

---

#### 2.2.7. `yufa.py` - 测试驱动与主入口

*   **核心职责**:
    1.  作为项目在命令行模式下的主入口。
    2.  包含一个 `tests` 字典，定义了多个 Cilly 代码测试用例。
    3.  `run_test(...)` 函数串联了从词法分析到虚拟机执行的完整流程，并打印出中间结果（如反汇编代码）和最终输出，是进行单元测试和功能验证的核心。
    4.  当以 `python yufa.py gui` 方式运行时，它会启动 `gui.py` 中的 IDE。
# -*- coding: utf-8 -*-
import sys
import pprint
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPlainTextEdit, QPushButton, QTabWidget, QListWidget,
                             QSplitter, QTextBrowser, QFileDialog, QMessageBox, QGraphicsView, QGraphicsScene,
                             QTextEdit, QLabel, QFrame)
from PyQt5.QtCore import QObject, QThread, pyqtSignal, Qt, QSize, QRect, QPointF, QLineF, QTimer, QProcess
from PyQt5.QtGui import QFont, QPainter, QColor, QTextFormat, QPolygonF, QBrush, QPen
from math import sin, cos
import subprocess
import tempfile
import os

# 导入 Cilly 编译器模块
from lexer import cilly_lexer
from cilly_parser_module import cilly_parser
from compile import cilly_vm_compiler
from vm import CillyVM, cilly_vm_dis # 导入 CillyVM 类
from transpiler import cilly_to_js # 导入 Transpiler
from yufa import tests # 导入测试用例

class CompilerWorker(QObject):
    """
    在单独的线程中运行编译和执行流程，以避免冻结 GUI。
    """
    finished = pyqtSignal()
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    # 为 turtle 操作定义信号
    forward_signal = pyqtSignal(float)
    backward_signal = pyqtSignal(float)
    left_signal = pyqtSignal(float)
    right_signal = pyqtSignal(float)
    penup_signal = pyqtSignal()
    pendown_signal = pyqtSignal()
    pencolor_signal = pyqtSignal(str)
    pensize_signal = pyqtSignal(int)
    reset_signal = pyqtSignal()
    speed_signal = pyqtSignal(int) # 尽管是 no-op, 但为了完整性

    def __init__(self, code):
        super().__init__()
        self.code = code
        # 将信号映射到名称，以便 VM 可以通过名称查找它们
        self.signals = {
            "forward": self.forward_signal,
            "backward": self.backward_signal,
            "left": self.left_signal,
            "right": self.right_signal,
            "penup": self.penup_signal,
            "pendown": self.pendown_signal,
            "pencolor": self.pencolor_signal,
            "pensize": self.pensize_signal,
            "reset": self.reset_signal,
            "speed": self.speed_signal,
        }

    def run(self):
        """
        执行完整的编译和运行流程。
        """
        try:
            # 1. 词法分析
            tokens = cilly_lexer(self.code)

            # 2. 语法分析
            ast = cilly_parser(tokens)

            # 3. 编译（传入 primitive 的名字，这些名字将用于在 VM 中查找信号）
            primitive_names = list(self.signals.keys())
            bytecode, consts, scopes, functions = cilly_vm_compiler(ast, primitive_names)

            # 4. 反汇编
            disassembled_code = cilly_vm_dis(bytecode, consts, scopes)

            # 5. 虚拟机执行
            # 重定向 stdout 以捕获输出
            from io import StringIO
            old_stdout = sys.stdout
            redirected_output = sys.stdout = StringIO()

            # 实例化 VM，传入 signals 字典而不是原始函数
            vm_instance = CillyVM(bytecode, consts, scopes, functions, signals=self.signals)
            vm_instance.run()

            sys.stdout = old_stdout
            vm_output = redirected_output.getvalue()

            # 准备结果
            results = {
                "tokens": tokens,
                "ast": ast,
                "bytecode": disassembled_code,
                "output": vm_output
            }
            self.results_ready.emit(results)

        except Exception as e:
            import traceback
            self.error_occurred.emit(f"发生错误:\n{traceback.format_exc()}")
        finally:
            self.finished.emit()


class JavaScriptRunner(QObject):
    """
    在单独的线程中运行 JavaScript 代码。
    """
    finished = pyqtSignal()
    output_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, js_code):
        super().__init__()
        self.js_code = js_code

    def run(self):
        """
        执行 JavaScript 代码并返回输出。
        """
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(self.js_code)
                temp_file = f.name

            try:
                # 运行 Node.js
                result = subprocess.run(
                    ['node', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=10  # 10秒超时
                )

                if result.returncode == 0:
                    self.output_ready.emit(result.stdout)
                else:
                    self.error_occurred.emit(f"JavaScript 错误:\n{result.stderr}")

            except subprocess.TimeoutExpired:
                self.error_occurred.emit("JavaScript 执行超时 (10 秒)")
            except FileNotFoundError:
                self.error_occurred.emit("未找到 Node.js。请安装 Node.js 以运行 JavaScript 代码。")
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file)
                except:
                    pass

        except Exception as e:
            import traceback
            self.error_occurred.emit(f"运行 JavaScript 时出错:\n{traceback.format_exc()}")
        finally:
            self.finished.emit()


class CillyGUI(QMainWindow):
    """
    Cilly IDE 的主窗口。
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cilly 集成开发环境")
        self.setGeometry(100, 100, 1200, 800)

        # --- UI 组件 ---
        # 测试用例翻译映射
        self.test_case_translation = {
            "Basic Arithmetic": "基础算术",
            "Variable Scoping": "变量作用域",
            "Conditional Statements": "条件语句",
            "Variable Name Display": "变量名显示",
            "Mutual Recursion": "相互递归",
            "Fern Turtle Graphics": "海龟绘图：蕨类"
        }
        # 创建反向映射以便加载代码
        self.reverse_test_case_translation = {v: k for k, v in self.test_case_translation.items()}
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        # 分割器
        self.splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.splitter)

        # 左侧面板：测试用例
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.test_list_widget = QListWidget()
        self.left_layout.addWidget(self.test_list_widget)
        self.splitter.addWidget(self.left_panel)

        # 右侧面板：编辑器和输出
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        
        # 按钮布局
        self.button_layout = QHBoxLayout()
        self.run_button = QPushButton("运行 Cilly")
        self.transpile_button = QPushButton("转译为 JS")
        self.run_js_button = QPushButton("运行 JavaScript")
        self.compare_button = QPushButton("对比结果")
        self.button_layout.addWidget(self.run_button)
        self.button_layout.addWidget(self.transpile_button)
        self.button_layout.addWidget(self.run_js_button)
        self.button_layout.addWidget(self.compare_button)
        self.right_layout.addLayout(self.button_layout)

        # 选项卡
        self.tabs = QTabWidget()
        self.code_editor = CodeEditor() # 使用自定义的 CodeEditor
        self.output_console = QTextBrowser()
        self.token_view = QTextBrowser()
        self.ast_view = QTextBrowser()
        self.bytecode_view = QTextBrowser()
        self.js_view = QTextBrowser() # JS 代码视图
        self.js_output_view = QTextBrowser() # JS 输出视图
        self.compare_view = self.create_compare_view() # 对比视图

        self.tabs.addTab(self.code_editor, "代码编辑器")
        self.tabs.addTab(self.output_console, "Cilly 输出")
        self.tabs.addTab(self.js_view, "JavaScript 代码")
        self.tabs.addTab(self.js_output_view, "JavaScript 输出")
        self.tabs.addTab(self.compare_view, "对比结果")
        self.tabs.addTab(self.token_view, "词法单元")
        self.tabs.addTab(self.ast_view, "抽象语法树")
        self.tabs.addTab(self.bytecode_view, "字节码")
        
        self.right_layout.addWidget(self.tabs)
        self.splitter.addWidget(self.right_panel)

        # 设置分割器初始大小
        self.splitter.setSizes([200, 1000])

        # 绘图窗口
        self.drawing_view = TurtleCanvas()
        self.drawing_view.setWindowTitle("Cilly 绘图画布")
        self.drawing_view.setGeometry(200, 200, 800, 600)  # 设置更大的窗口尺寸

        # --- 初始化和连接 ---
        self.setup_editor()
        self.populate_test_cases()
        self.connect_signals()

        # 存储运行结果用于对比
        self.cilly_output = ""
        self.js_output = ""

    def setup_editor(self):
        """设置代码编辑器字体和行号。"""
        font = QFont()
        font.setFamily("Courier")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.code_editor.setFont(font)
        # 简单的行号实现可以后续添加

    def create_compare_view(self):
        """创建对比视图。"""
        compare_widget = QWidget()
        layout = QHBoxLayout(compare_widget)

        # 左侧：Cilly 输出
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_label = QLabel("Cilly 输出:")
        left_label.setStyleSheet("font-weight: bold; color: blue;")
        self.cilly_compare_output = QTextBrowser()
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.cilly_compare_output)

        # 右侧：JavaScript 输出
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_label = QLabel("JavaScript 输出:")
        right_label.setStyleSheet("font-weight: bold; color: green;")
        self.js_compare_output = QTextBrowser()
        right_layout.addWidget(right_label)
        right_layout.addWidget(self.js_compare_output)

        layout.addWidget(left_panel)
        layout.addWidget(right_panel)

        return compare_widget

    def populate_test_cases(self):
        """从 yufa.py 加载测试用例到列表中。"""
        for test_name_en in tests:
            # 使用翻译后的名称添加到列表
            test_name_cn = self.test_case_translation.get(test_name_en, test_name_en)
            self.test_list_widget.addItem(test_name_cn)

    def connect_signals(self):
        """连接所有信号和槽。"""
        self.run_button.clicked.connect(self.run_code)
        self.transpile_button.clicked.connect(self.transpile_code)
        self.run_js_button.clicked.connect(self.run_javascript)
        self.compare_button.clicked.connect(self.compare_results)
        self.test_list_widget.itemDoubleClicked.connect(self.load_test_case)

    def load_test_case(self, item):
        """加载选定的测试用例到编辑器。"""
        test_name_cn = item.text()
        # 使用反向映射找到原始的英文键
        test_name_en = self.reverse_test_case_translation.get(test_name_cn, test_name_cn)
        if test_name_en in tests:
            self.code_editor.setPlainText(tests[test_name_en])
            self.tabs.setCurrentWidget(self.code_editor)

    def transpile_code(self):
        """
        仅执行词法分析、语法分析和 JS 转换。
        """
        code = self.code_editor.toPlainText()
        if not code.strip():
            QMessageBox.warning(self, "警告", "代码编辑器为空。")
            return
            
        try:
            # 1. 词法分析
            tokens = cilly_lexer(code)

            # 2. 语法分析
            ast = cilly_parser(tokens)

            # 3. 转换为 JS
            js_code = cilly_to_js(ast)
            
            # 在 UI 中显示结果
            self.js_view.setText(js_code)
            self.token_view.setText(pprint.pformat(tokens))
            self.ast_view.setText(pprint.pformat(ast))
            self.tabs.setCurrentWidget(self.js_view)

        except Exception as e:
            import traceback
            self.output_console.setText(f"转译过程中发生错误:\n{traceback.format_exc()}")
            self.tabs.setCurrentWidget(self.output_console)

    def run_javascript(self):
        """运行 JavaScript 代码。"""
        js_code = self.js_view.toPlainText()
        if not js_code.strip():
            QMessageBox.warning(self, "警告", "没有可运行的 JavaScript 代码。请先转译 Cilly 代码。")
            return

        self.run_js_button.setEnabled(False)
        self.js_output_view.clear()

        # 创建并启动 JavaScript 运行线程
        self.js_thread = QThread()
        self.js_worker = JavaScriptRunner(js_code)
        self.js_worker.moveToThread(self.js_thread)

        # 连接信号
        self.js_thread.started.connect(self.js_worker.run)
        self.js_worker.finished.connect(self.js_thread.quit)
        self.js_worker.finished.connect(self.js_worker.deleteLater)
        self.js_thread.finished.connect(self.js_thread.deleteLater)
        self.js_worker.output_ready.connect(self.on_js_output_ready)
        self.js_worker.error_occurred.connect(self.on_js_error)

        self.js_thread.start()

    def on_js_output_ready(self, output):
        """JavaScript 运行成功时的处理。"""
        self.js_output = output
        self.js_output_view.setText(output)
        self.tabs.setCurrentWidget(self.js_output_view)
        self.run_js_button.setEnabled(True)

    def on_js_error(self, error_message):
        """JavaScript 运行出错时的处理。"""
        self.js_output = f"Error: {error_message}"
        self.js_output_view.setText(self.js_output)
        self.tabs.setCurrentWidget(self.js_output_view)
        self.run_js_button.setEnabled(True)

    def compare_results(self):
        """对比 Cilly 和 JavaScript 的运行结果。"""
        self.cilly_compare_output.setText(self.cilly_output)
        self.js_compare_output.setText(self.js_output)
        self.tabs.setCurrentWidget(self.compare_view)

    def run_code(self):
        """触发编译和执行流程。"""
        code = self.code_editor.toPlainText()
        if not code.strip():
            QMessageBox.warning(self, "警告", "代码编辑器为空。")
            return

        self.run_button.setEnabled(False)
        self.output_console.clear()
        self.token_view.clear()
        self.ast_view.clear()
        self.bytecode_view.clear()
        
        # 为绘图测试用例准备
        graphics_widget = None
        # 更可靠地检测绘图代码
        turtle_keywords = ["forward", "backward", "left", "right", "pencolor"]
        code_text = self.code_editor.toPlainText()
        if any(keyword in code_text for keyword in turtle_keywords):
             self.drawing_view.setup_turtle() # 重置并准备画布
             self.drawing_view.show()
             # graphics_widget is no longer passed to worker

        # 创建并启动工作线程
        self.thread = QThread()
        self.worker = CompilerWorker(code)
        self.worker.moveToThread(self.thread)

        # 连接信号到槽
        if any(keyword in code_text for keyword in turtle_keywords):
            self.worker.forward_signal.connect(self.drawing_view.forward)
            self.worker.backward_signal.connect(self.drawing_view.backward)
            self.worker.left_signal.connect(self.drawing_view.left)
            self.worker.right_signal.connect(self.drawing_view.right)
            self.worker.penup_signal.connect(self.drawing_view.penup)
            self.worker.pendown_signal.connect(self.drawing_view.pendown)
            self.worker.pencolor_signal.connect(self.drawing_view.pencolor)
            self.worker.pensize_signal.connect(self.drawing_view.pensize)
            self.worker.reset_signal.connect(self.drawing_view.setup_turtle)
            # self.worker.speed_signal.connect(...) # speed is a no-op

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.results_ready.connect(self.on_compilation_finished)
        self.worker.error_occurred.connect(self.on_compilation_error)

        self.thread.start()

    def on_compilation_finished(self, results):
        """当编译成功时更新 UI。"""
        self.token_view.setText(pprint.pformat(results["tokens"]))
        self.ast_view.setText(pprint.pformat(results["ast"]))
        self.bytecode_view.setText(results["bytecode"])
        self.cilly_output = results["output"]  # 保存 Cilly 输出用于对比
        self.output_console.setText(self.cilly_output)
        self.tabs.setCurrentWidget(self.output_console)
        self.run_button.setEnabled(True)

    def on_compilation_error(self, error_message):
        """当编译出错时更新 UI。"""
        self.cilly_output = error_message  # 保存错误信息用于对比
        self.output_console.setText(error_message)
        self.tabs.setCurrentWidget(self.output_console)
        self.run_button.setEnabled(True)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)

    def lineNumberAreaWidth(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(Qt.yellow).lighter(160)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), Qt.lightGray)
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(Qt.black)
                painter.drawText(0, int(top), self.lineNumberArea.width(), int(self.fontMetrics().height()),
                                 Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


class TurtleCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pen_is_down = True
        self.pen_color = QColor("black")
        self.pen_width = 1
        self.turtle = None
        self.drawing_speed = 50  # 毫秒延迟
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.process_animation_queue)
        self.animation_queue = []

        # 设置场景大小
        self.scene.setSceneRect(-400, -300, 800, 600)

    def setup_turtle(self):
        self.scene.clear()
        self.animation_queue.clear()
        self.animation_timer.stop()

        # 创建一个三角形代表 turtle
        self.turtle = self.scene.addPolygon(
            QPolygonF([QPointF(0, -10), QPointF(5, 5), QPointF(-5, 5)]),
            QPen(Qt.NoPen),
            QBrush(QColor("green"))
        )
        self.turtle.setPos(0, 0)
        self.turtle.setRotation(0) # 0 度是向上

        # 确保turtle可见
        self.centerOn(self.turtle)

    def process_animation_queue(self):
        if not self.animation_queue:
            self.animation_timer.stop()
            return

        action = self.animation_queue.pop(0)
        action()

        if self.animation_queue:
            self.animation_timer.start(self.drawing_speed)
        else:
            self.animation_timer.stop()

    def forward(self, distance):
        if not self.turtle: return

        # 添加到动画队列而不是立即执行
        def do_forward():
            rad = self.turtle.rotation() * 3.14159 / 180.0
            start_pos = self.turtle.pos()
            dx = -distance * sin(rad)
            dy = -distance * cos(rad)
            end_pos = QPointF(start_pos.x() + dx, start_pos.y() + dy)
            if self.pen_is_down:
                pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                self.scene.addLine(QLineF(start_pos, end_pos), pen)
            self.turtle.setPos(end_pos)

        self.animation_queue.append(do_forward)
        if not self.animation_timer.isActive():
            self.animation_timer.start(self.drawing_speed)

    def backward(self, distance):
        self.forward(-distance)

    def left(self, angle):
        if not self.turtle: return

        def do_left():
            self.turtle.setRotation(self.turtle.rotation() - angle)

        self.animation_queue.append(do_left)
        if not self.animation_timer.isActive():
            self.animation_timer.start(self.drawing_speed)

    def right(self, angle):
        if not self.turtle: return

        def do_right():
            self.turtle.setRotation(self.turtle.rotation() + angle)

        self.animation_queue.append(do_right)
        if not self.animation_timer.isActive():
            self.animation_timer.start(self.drawing_speed)

    def penup(self):
        def do_penup():
            self.pen_is_down = False

        self.animation_queue.append(do_penup)
        if not self.animation_timer.isActive():
            self.animation_timer.start(self.drawing_speed)

    def pendown(self):
        def do_pendown():
            self.pen_is_down = True

        self.animation_queue.append(do_pendown)
        if not self.animation_timer.isActive():
            self.animation_timer.start(self.drawing_speed)

    def pencolor(self, color_name):
        def do_pencolor():
            try:
                self.pen_color = QColor(color_name)
            except:
                print(f"警告: 无效的颜色名称 '{color_name}'")
                self.pen_color = QColor("black") # Fallback to black

        self.animation_queue.append(do_pencolor)
        if not self.animation_timer.isActive():
            self.animation_timer.start(self.drawing_speed)

    def pensize(self, width):
        def do_pensize():
            self.pen_width = int(width)

        self.animation_queue.append(do_pensize)
        if not self.animation_timer.isActive():
            self.animation_timer.start(self.drawing_speed)

    def reset(self):
        # This is connected to the reset_signal, which calls setup_turtle
        self.setup_turtle()


def main():
    app = QApplication(sys.argv)
    gui = CillyGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
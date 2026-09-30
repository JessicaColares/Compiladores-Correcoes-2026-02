import os
import subprocess
import shutil
import sys
import re
import time
import signal
from pathlib import Path
import csv

# Cores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_flush(msg, end='\n'):
    print(msg, end=end, flush=True)

class ExpressionGrader:
    ARQUIVOS_GERADOS_ANTLR = {
        'ExprLexer', 'ExprParser', 'ExprListener', 'ExprVisitor',
        'ExprBaseListener', 'ExprBaseVisitor',
    }

    def __init__(self, student_dir):
        self.student_dir = Path(student_dir)
        self.student_name = self.student_dir.name

    # ================================================================
    # DETECÇÃO DE LINGUAGEM
    # ================================================================
    def is_java_project(self):
        java_files = list(self.student_dir.glob("*.java"))
        py_main = self.find_main_py()
        return len(java_files) > 0 and py_main is None

    def find_java_main(self):
        for jf in self.student_dir.glob("*.java"):
            try:
                content = jf.read_text(errors='replace')
                if 'public static void main' in content:
                    match = re.search(r'(?:public\s+)?(?:class|interface)\s+(\w+)', content)
                    if match:
                        return match.group(1)
            except:
                pass
        return None

    # ================================================================
    # MÉTODOS PYTHON
    # ================================================================
    def find_main_py(self):
        py_files = list(self.student_dir.glob("*.py"))
        if not py_files:
            return None
        py_files = [
            f for f in py_files
            if f.stem not in self.ARQUIVOS_GERADOS_ANTLR
            and not f.stem.endswith('Listener')
            and not f.stem.endswith('Visitor')
        ]
        if not py_files:
            return None
        priority = ["main.py", "Main.py", "principal.py", "Principal.py",
                    "app.py", "run.py", "calc.py", "calculadora.py"]
        for pf in py_files:
            if pf.name in priority:
                return pf
        for pf in py_files:
            if 'listener' not in pf.name.lower() and 'visitor' not in pf.name.lower():
                return pf
        return py_files[0]

    def find_grammar_file(self):
        for f in self.student_dir.glob("*.g*"):
            if f.suffix in ['.g', '.g4']:
                return f
        return None

    #   v11: retorna só `missing` (sem aviso_visitor)
    def check_imports(self, main_py):
        """Verifica se os módulos importados no main.py existem na pasta do aluno"""
        try:
            content = main_py.read_text(encoding='utf-8-sig')
            imports = re.findall(r'^\s*(?:from\s+(\w+)\s+import|import\s+(\w+))',
                                 content, re.MULTILINE)
            ignorar = {'antlr4', 'sys', 'os', 're', 'math', 'io', 'typing',
                       'collections', 'functools', 'itertools', 'abc', 'enum',
                       'dataclasses', 'decimal', 'random', 'string', 'time',
                       'pathlib', 'subprocess', 'shutil', 'csv', 'json'}
            missing = []
            for imp in imports:
                modulo = imp[0] or imp[1]
                if not modulo or modulo in ignorar:
                    continue
                if not (self.student_dir / f"{modulo}.py").exists() \
                   and not (self.student_dir / modulo).exists():
                    missing.append(modulo)
            seen = set()
            return [m for m in missing if not (m in seen or seen.add(m))]
        except:
            return []

    def check_main_py_truncado(self, main_py):
        try:
            content = main_py.read_text(encoding='utf-8-sig').rstrip()
            content = content.lstrip('\ufeff')
            if not content:
                return "main.py está vazio"
            ultima = content.split('\n')[-1].strip()
            if ultima.endswith((':', '\\', '(', ',', '[')):
                return f"main.py incompleto (última linha: {ultima!r})"
            try:
                compile(content, str(main_py), 'exec')
            except IndentationError as e:
                return f"main.py incompleto (erro de indentação: {e.msg}, linha {e.lineno})"
            except SyntaxError as e:
                return f"main.py incompleto (erro de sintaxe: {e.msg}, linha {e.lineno})"
            return None
        except Exception as e:
            return f"Erro ao ler main.py: {e}"

    def check_programa_sem_input(self, main_py):
        try:
            content = main_py.read_text(encoding='utf-8-sig')
            content = content.lstrip('\ufeff')
            tem_lista = re.search(r'testes?\s*=\s*\[[^\]]*["\'][^"\']*["\'][^\]]*\]',
                                  content, re.DOTALL | re.IGNORECASE)
            tem_loop = re.search(r'for\s+\w+\s+in\s+testes?', content)
            tem_input = 'input(' in content
            tem_argv = 'sys.argv' in content
            if tem_lista and tem_loop and not tem_input and not tem_argv:
                return "Programa só roda testes fixos (não aceita input externo)"
            return None
        except:
            return None

    #   v11: ignora linhas de import e checa só o código
    def check_usa_visitor(self, main_py):
        """Verifica se o main.py realmente usa o padrão Visitor"""
        try:
            content = main_py.read_text(encoding='utf-8-sig')
            content = content.lstrip('\ufeff')

            # Remove linhas de import para evitar falsos positivos
            # (ex: "from antlr4.error.ErrorListener import ErrorListener")
            linhas_sem_import = []
            for linha in content.split('\n'):
                stripped = linha.strip()
                if stripped.startswith('import ') or stripped.startswith('from '):
                    continue
                linhas_sem_import.append(linha)
            codigo = '\n'.join(linhas_sem_import)

            usa_visitor = bool(re.search(r'\.visit\s*\(', codigo))
            usa_listener = bool(re.search(r'\.walk\s*\(', codigo)) or \
                           bool(re.search(r'walker\.walk\s*\(', codigo))

            if usa_listener and not usa_visitor:
                return "Usou Listener em vez de Visitor"
            if not usa_visitor:
                return "Programa não usa .visit() (esperado padrão Visitor)"
            return None
        except:
            return None

    # ================================================================
    # COMPILAÇÃO
    # ================================================================
    def compile_grammar(self, language="Python3"):
        grammar_file = self.find_grammar_file()
        if not grammar_file:
            return False, "Arquivo de gramática não encontrado"

        antlr_jar = self.student_dir / "antlr-4.13.2-complete.jar"
        if not antlr_jar.exists():
            return False, "ANTLR JAR não encontrado"

        try:
            cmd = ["java", "-jar", str(antlr_jar),
                   f"-Dlanguage={language}", "-visitor", "-listener",
                   str(grammar_file)]
            result = subprocess.run(cmd, cwd=self.student_dir,
                                    capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return False, f"Erro na compilação: {result.stderr}"
            return True, "Compilado com sucesso"
        except Exception as e:
            return False, f"Erro: {str(e)}"

    def compile_java_classes(self):
        java_files = list(self.student_dir.glob("*.java"))
        if not java_files:
            return False, "Nenhum arquivo .java encontrado"

        cp = f"antlr-4.13.2-complete.jar:{self.student_dir}"
        cmd = ["javac", "-cp", cp] + [f.name for f in java_files]

        try:
            result = subprocess.run(cmd, cwd=self.student_dir,
                                    capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                return False, f"Erro no javac: {result.stderr[:300]}"
            return True, "Classes compiladas com sucesso"
        except subprocess.TimeoutExpired:
            return False, "Timeout na compilação Java (>60s)"
        except Exception as e:
            return False, f"Erro: {str(e)}"

    # ================================================================
    # EXTRAÇÃO DE NÚMERO
    # ================================================================
    def extract_number(self, text):
        padroes = [
            r'(?:resultado|result|valor|value|saida|saída|output)\s*[:=]\s*([-+]?\d+\.?\d*)',
            r'[:=]\s*([-+]?\d+\.?\d*)\s*$',
            r'([-+]?\d+\.?\d*)\s*$',
        ]
        linhas = [l.strip() for l in text.strip().split('\n') if l.strip()]
        for linha in reversed(linhas):
            for p in padroes:
                m = re.search(p, linha, re.IGNORECASE)
                if m:
                    v = m.group(1)
                    return float(v) if '.' in v else int(v)
        for p in [r'[-+]?\d+\.\d+', r'[-+]?\d+']:
            ms = re.findall(p, text)
            if ms:
                v = ms[-1]
                return float(v) if '.' in v else int(v)
        return None

    def _classificar_erro_saida(self, output):
        if not output or not output.strip():
            return "Programa não produziu saída"
        m = re.search(r'(\w+(?:Error|Exception)):\s*(.+)', output)
        if m:
            return f"{m.group(1)}: {m.group(2).strip().split(chr(10))[0][:120]}"
        if re.search(r'[:=]\s*None\b', output):
            return "Programa retornou None"
        m = re.search(r'(?:erro|error|exception)\s*[:\-]?\s*(.+)', output, re.IGNORECASE)
        if m:
            return f"Programa reportou erro: {m.group(1).strip().split(chr(10))[0][:100]}"
        if "Traceback" in output or "Exception in thread" in output:
            linhas = [l.strip() for l in output.strip().split('\n') if l.strip()]
            return f"Exceção: {linhas[-1][:120]}" if linhas else "Exceção"
        if re.search(r'resultado\s*=', output, re.IGNORECASE):
            return "Programa imprimiu 'Resultado = ' mas valor não é numérico"
        if re.search(r'(?:digite|entre|informe|express)[^\n]{0,60}[?:>]\s*\w*$', output, re.IGNORECASE):
            return "Programa Incompleto (não processou a expressão)"
        if re.search(r'[=\-]{5,}', output) and not re.search(r'\d', output):
            return "Programa imprimiu banner mas não processou"
        return f"Saída sem número: {output[:100]!r}"

    # ================================================================
    # EXECUÇÃO PYTHON
    # ================================================================
    def detect_program_type(self, main_py):
        try:
            content = main_py.read_text(encoding='utf-8-sig')
            content = content.lstrip('\ufeff')
            n_inputs = content.count('input(')
            n_argv = content.count('sys.argv')
            if n_inputs > 0 and n_argv == 0:
                return "interativo"
            if 'FileStream' in content:
                return "arquivo"
            if n_argv > 0:
                return "argumento"
            if n_inputs > 0:
                return "interativo"
            return "argumento"
        except:
            return "desconhecido"

    def _read_output_with_timeout(self, process, timeout, check_interval=0.05):
        start = time.time()
        ultimo = time.time()
        output = ""
        ocioso_max = 1.5
        while time.time() - start < timeout:
            if process.poll() is not None:
                try:
                    b = b""
                    while True:
                        try:
                            c = os.read(process.stdout.fileno(), 4096)
                            if not c: break
                            b += c
                        except (OSError, ValueError): break
                    output += b.decode('utf-8', errors='replace')
                except: pass
                return output, process.returncode
            try:
                import select
                ready, _, _ = select.select([process.stdout], [], [], check_interval)
                if ready:
                    try:
                        cb = os.read(process.stdout.fileno(), 4096)
                        if cb:
                            output += cb.decode('utf-8', errors='replace')
                            ultimo = time.time()
                            if self.extract_number(output) is not None:
                                try:
                                    process.kill(); process.wait(timeout=0.5)
                                except: pass
                                return output, None
                    except (OSError, ValueError): pass
            except ImportError:
                time.sleep(check_interval)
            except: pass
            if time.time() - ultimo > ocioso_max:
                try:
                    process.kill(); process.wait(timeout=1)
                except: pass
                return output, "TIMEOUT_OCIOSO"
        try:
            process.kill(); process.wait(timeout=1)
        except: pass
        try:
            b = b""
            while True:
                try:
                    c = os.read(process.stdout.fileno(), 4096)
                    if not c: break
                    b += c
                except (OSError, ValueError): break
            output += b.decode('utf-8', errors='replace')
        except: pass
        return output, "TIMEOUT"

    def run_interactive_test(self, cmd, expression, timeout=3):
        process = None
        try:
            process = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, bufsize=0,
            )
            time.sleep(0.3)
            try:
                process.stdin.write((expression + '\n').encode('utf-8'))
                process.stdin.flush()
            except: pass
            output, status = self._read_output_with_timeout(process, timeout)
            if status == "TIMEOUT":
                if output and self.extract_number(output) is not None:
                    return output, "Programa travou em loop (timeout total)"
                return output, f"Timeout após {timeout}s"
            if status == "TIMEOUT_OCIOSO":
                return output if output else None, None
            return output if output else None, None
        except Exception as e:
            if process and process.poll() is None:
                try: process.kill(); process.wait()
                except: pass
            return None, f"Erro: {str(e)}"
        finally:
            if process and process.poll() is None:
                try: process.kill(); process.wait()
                except: pass

    def run_test_with_timeout(self, cmd, timeout=3):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.stdout + r.stderr, None
        except subprocess.TimeoutExpired:
            return None, f"Timeout após {timeout}s"
        except Exception as e:
            return None, f"Erro: {str(e)}"

    def run_test_python(self, expression, expected_value):
        main_py = self.find_main_py()
        if not main_py:
            return None, "Nenhum arquivo Python encontrado"
        original_dir = os.getcwd()
        os.chdir(self.student_dir)
        try:
            output = None
            method = None
            error = None
            ptype = self.detect_program_type(main_py)
            cmd = [sys.executable, str(main_py)]

            if ptype == "interativo":
                result_output, error = self.run_interactive_test(cmd, expression, timeout=3)
                if error:
                    return None, error
                if result_output is not None and self.extract_number(result_output) is not None:
                    output = result_output
                    method = "interativo"
                else:
                    if result_output:
                        return None, self._classificar_erro_saida(result_output)
                    return None, "Programa não produziu saída"
            else:
                try:
                    cmd_arg = [sys.executable, str(main_py), expression]
                    ro, error = self.run_test_with_timeout(cmd_arg, timeout=3)
                    if ro is not None and self.extract_number(ro) is not None:
                        output = ro; method = "argumento"
                except: pass
                if output is None or self.extract_number(output) is None:
                    try:
                        ro, error = self.run_interactive_test(cmd, expression, timeout=3)
                        if ro is not None and self.extract_number(ro) is not None:
                            output = ro; method = "interativo"
                    except: pass
                if output is None or self.extract_number(output) is None:
                    try:
                        cmd_arg = [sys.executable, str(main_py), f'"{expression}"']
                        ro, error = self.run_test_with_timeout(cmd_arg, timeout=3)
                        if ro is not None and self.extract_number(ro) is not None:
                            output = ro; method = "argumento_com_aspas"
                    except: pass

            if output is None:
                if error: return None, error
                return None, "Não foi possível executar o programa"

            if "ModuleNotFoundError" in output or "ImportError" in output:
                m = re.search(r"No module named '([\w\.]+)'", output)
                return None, f"Erro de importação: módulo '{m.group(1) if m else '?'}' não encontrado"

            rv = self.extract_number(output)
            if rv is None:
                return None, self._classificar_erro_saida(output)

            if isinstance(expected_value, float) or isinstance(rv, float):
                passed = abs(float(expected_value) - float(rv)) < 0.01
            else:
                passed = rv == expected_value
            return {"output": output.strip(), "result": rv, "expected": expected_value,
                    "passed": passed, "method": method}, None
        except Exception as e:
            return None, f"Erro geral: {str(e)}"
        finally:
            os.chdir(original_dir)

    # ================================================================
    # EXECUÇÃO JAVA
    # ================================================================
    def run_java_test(self, main_class, expression, timeout=5):
        cp = f"antlr-4.13.2-complete.jar:{self.student_dir}"
        cmd = ["java", "-cp", cp, main_class, expression]
        try:
            r = subprocess.run(cmd, cwd=self.student_dir,
                               capture_output=True, text=True, timeout=timeout)
            output = r.stdout + r.stderr
            return output, None
        except subprocess.TimeoutExpired:
            return None, f"Timeout após {timeout}s"
        except Exception as e:
            return None, f"Erro: {str(e)}"

    def run_test_java(self, main_class, expression, expected_value):
        output, error = self.run_java_test(main_class, expression)
        if output is None:
            return None, error or "Sem saída"
        if "Exception in thread" in output:
            m = re.search(r'([\w\.]+Exception|[\w\.]+Error):\s*(.+)', output)
            if m:
                return None, f"{m.group(1)}: {m.group(2).strip()[:120]}"
            return None, "Exceção Java"
        rv = self.extract_number(output)
        if rv is None:
            return None, self._classificar_erro_saida(output)
        if isinstance(expected_value, float) or isinstance(rv, float):
            passed = abs(float(expected_value) - float(rv)) < 0.01
        else:
            passed = rv == expected_value
        return {"output": output.strip(), "result": rv, "expected": expected_value,
                "passed": passed, "method": "java"}, None

    # ================================================================
    # AVALIAÇÃO
    # ================================================================
    def grade_student(self):
        print_flush(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
        print_flush(f"{Colors.BOLD}Avaliando: {self.student_name}{Colors.END}")
        print_flush(f"{Colors.CYAN}{'='*60}{Colors.END}")

        is_java = self.is_java_project()
        if is_java:
            return self._grade_java_student()
        else:
            return self._grade_python_student()

    def _grade_java_student(self):
        main_class = self.find_java_main()
        if not main_class:
            msg = "Atividade em Java, mas nenhuma classe com main() encontrada"
            print_flush(f"{Colors.RED}✗ {msg}{Colors.END}")
            self.update_nota_md_with_error(msg)
            return 0.0, {}

        print_flush(f"  Classe Java: {main_class}")

        grammar_file = self.find_grammar_file()
        if not grammar_file:
            print_flush(f"{Colors.RED}✗ Nenhum arquivo de gramática encontrado{Colors.END}")
            self.update_nota_md_with_error("Arquivo de gramática não encontrado")
            return 0.0, {}

        ok, msg = self.compile_grammar(language="Java")
        if not ok:
            print_flush(f"{Colors.RED}✗ {msg}{Colors.END}")
            self.update_nota_md_with_compilation_error(msg)
            return 0.0, {}
        print_flush(f"{Colors.GREEN}✓ Gramática compilada (Java){Colors.END}")

        ok, msg = self.compile_java_classes()
        if not ok:
            print_flush(f"{Colors.RED}✗ {msg}{Colors.END}")
            self.update_nota_md_with_error(msg)
            return 0.0, {}
        print_flush(f"{Colors.GREEN}✓ Classes Java compiladas{Colors.END}")

        tests = [
            ("(5*4)", 20), ("2 + 3", 5), ("abs(-10)", 10),
            ("-9/3", -3), ("3.5 * (2 + 1)", 10.5), ("-15 + 20", 5),
            ("(2^3)^2", 64), ("abs(fat(3))", 6), ("(2+3)*(4-1)", 15),
            ("fat(abs(-5))", 120),
        ]

        results = {}
        loop_detected = False
        print_flush(f"\n{Colors.BOLD}--- Executando Testes (Java) ---{Colors.END}")

        for i, (expression, expected) in enumerate(tests, 1):
            print_flush(f"\n{Colors.BOLD}Teste {i}:{Colors.END} {expression}")
            print_flush(f"  Esperado: {expected}")
            start = time.time()
            result, error = self.run_test_java(main_class, expression, expected)
            elapsed = time.time() - start
            if error and "Timeout" in error:
                loop_detected = True
                print_flush(f"  {Colors.YELLOW}⚠ TIMEOUT ({elapsed:.1f}s){Colors.END}")
            if result is None:
                erro_msg = error or "Sem saída"
                print_flush(f"  {Colors.RED}✗ Erro: {erro_msg}{Colors.END}")
                results[f"teste_{i}"] = {
                    "expression": expression, "expected": expected,
                    "passed": False, "score": 0.0, "obs": None,
                    "output": None, "result": None, "error": erro_msg,
                }
            else:
                passed = result["passed"]
                score = 1.0 if passed else 0.0
                status = f"{Colors.GREEN}✓ Passou{Colors.END}" if passed else f"{Colors.RED}✗ Falhou{Colors.END}"
                print_flush(f"  Resultado: {result['result']} - {status} ({elapsed:.1f}s)")
                print_flush(f"  Método: java")
                results[f"teste_{i}"] = {
                    "expression": expression, "expected": expected,
                    "passed": passed, "score": score, "obs": None,
                    "output": result["output"], "result": result["result"],
                    "method": "java", "error": None,
                }

        total = sum(r["score"] for r in results.values())
        print_flush(f"\n{Colors.BOLD}Nota final: {total:.1f}/10.0{Colors.END}")
        if loop_detected:
            print_flush(f"  {Colors.YELLOW}⚠ ALERTA: Timeouts detectados!{Colors.END}")
        self.update_nota_md(results)
        return total, results

    def _grade_python_student(self):
        main_py = self.find_main_py()
        if not main_py:
            print_flush(f"{Colors.RED}✗ Nenhum arquivo Python encontrado{Colors.END}")
            self.update_nota_md_with_error("Nenhum arquivo Python encontrado")
            return 0.0, {}

        print_flush(f"  Arquivo Python: {main_py.name}")

        # 1. Verifica se usa padrão Visitor
        erro_visitor = self.check_usa_visitor(main_py)
        if erro_visitor:
            print_flush(f"{Colors.RED}✗ {erro_visitor}{Colors.END}")
            self.update_nota_md_usou_listener(erro_visitor)
            return 0.0, {}

        # 2. Verifica se só roda testes fixos
        erro_sem_input = self.check_programa_sem_input(main_py)
        if erro_sem_input:
            print_flush(f"{Colors.RED}✗ {erro_sem_input}{Colors.END}")
            self.update_nota_md_with_error(erro_sem_input)
            return 0.0, {}

        # 3. Verifica se main.py está truncado
        erro_trunc = self.check_main_py_truncado(main_py)
        if erro_trunc:
            print_flush(f"{Colors.RED}✗ {erro_trunc}{Colors.END}")
            self.update_nota_md_with_error(erro_trunc)
            return 0.0, {}

        # 4. Verifica se tem gramática
        grammar_file = self.find_grammar_file()
        if not grammar_file:
            print_flush(f"{Colors.RED}✗ Nenhum arquivo de gramática encontrado{Colors.END}")
            self.update_nota_md_with_error("Arquivo de gramática não encontrado")
            return 0.0, {}

        # 5. Compila a gramática ANTES de checar imports
        ok, msg = self.compile_grammar(language="Python3")
        if not ok:
            print_flush(f"{Colors.RED}✗ {msg}{Colors.END}")
            self.update_nota_md_with_compilation_error(msg)
            return 0.0, {}
        print_flush(f"{Colors.GREEN}✓ Gramática compilada com sucesso{Colors.END}")

        # 6. Agora checa imports (os arquivos gerados já existem)
        missing = self.check_imports(main_py)
        if missing:
            msg = f"Módulos não encontrados: {', '.join(missing)}"
            print_flush(f"{Colors.RED}✗ {msg}{Colors.END}")
            self.update_nota_md_with_error(msg)
            return 0.0, {}

        tests = [
            ("(5*4)", 20), ("2 + 3", 5), ("abs(-10)", 10),
            ("-9/3", -3), ("3.5 * (2 + 1)", 10.5), ("-15 + 20", 5),
            ("(2^3)^2", 64), ("abs(fat(3))", 6), ("(2+3)*(4-1)", 15),
            ("fat(abs(-5))", 120),
        ]

        results = {}
        loop_detected = False
        print_flush(f"\n{Colors.BOLD}--- Executando Testes ---{Colors.END}")

        for i, (expression, expected) in enumerate(tests, 1):
            print_flush(f"\n{Colors.BOLD}Teste {i}:{Colors.END} {expression}")
            print_flush(f"  Esperado: {expected}")
            start = time.time()
            result, error = self.run_test_python(expression, expected)
            elapsed = time.time() - start
            if error and "Timeout" in error:
                loop_detected = True
                print_flush(f"  {Colors.YELLOW}⚠ TIMEOUT ({elapsed:.1f}s){Colors.END}")
            elif error and "loop" in error.lower():
                loop_detected = True
                print_flush(f"  {Colors.YELLOW}⚠ LOOP DETECTADO ({elapsed:.1f}s){Colors.END}")
            if result is None:
                erro_msg = error or "Sem saída / erro desconhecido"
                print_flush(f"  {Colors.RED}✗ Erro: {erro_msg}{Colors.END}")
                results[f"teste_{i}"] = {
                    "expression": expression, "expected": expected,
                    "passed": False, "score": 0.0, "obs": None,
                    "output": None, "result": None, "error": erro_msg,
                }
            else:
                passed = result["passed"]
                score = 1.0 if passed else 0.0
                status = f"{Colors.GREEN}✓ Passou{Colors.END}" if passed else f"{Colors.RED}✗ Falhou{Colors.END}"
                print_flush(f"  Resultado: {result['result']} - {status} ({elapsed:.1f}s)")
                print_flush(f"  Método: {result['method']}")
                results[f"teste_{i}"] = {
                    "expression": expression, "expected": expected,
                    "passed": passed, "score": score, "obs": None,
                    "output": result["output"], "result": result["result"],
                    "method": result["method"], "error": None,
                }

        total = sum(r["score"] for r in results.values())
        print_flush(f"\n{Colors.BOLD}Nota final: {total:.1f}/10.0{Colors.END}")
        if loop_detected:
            print_flush(f"  {Colors.YELLOW}⚠ ALERTA: Timeouts/loops detectados!{Colors.END}")
        self.update_nota_md(results)
        return total, results

    # ================================================================
    # NOTA.MD
    # ================================================================
    def update_nota_md_usou_listener(self, aviso_msg):
        """
        Usado quando o aluno usou Listener em vez de Visitor.
        Zera a nota, mas registra a mensagem nas Considerações.
        """
        nota_path = self.student_dir / "nota.md"
        original = nota_path.read_text(encoding='utf-8') if nota_path.exists() else ""

        obs = {}
        for i in range(1, 11):
            m = re.search(rf"### Teste {i}:\s*\n.*?\nObservação: (.*?)(?:\n|$)", original, re.DOTALL)
            obs[i] = m.group(1).strip() if m else "Valor esperado: [ver nota.md original]"

        content = "## Aceitação:\n\n"
        for i in range(1, 11):
            content += f"### Teste {i}:\nPonto: 0<br>\nObservação: {obs[i]}<br>\n\n"

        content += f"## Considerações:\n{aviso_msg}\n\n## Nota Final: 0.0\n"
        nota_path.write_text(content, encoding='utf-8')

    def update_nota_md_with_compilation_error(self, error_msg):
        nota_path = self.student_dir / "nota.md"
        original = nota_path.read_text(encoding='utf-8') if nota_path.exists() else ""
        obs = {}
        for i in range(1, 11):
            m = re.search(rf"### Teste {i}:\s*\n.*?\nObservação: (.*?)(?:\n|$)", original, re.DOTALL)
            obs[i] = m.group(1).strip() if m else "Valor esperado: [ver nota.md original]"
        content = "## Aceitação:\n\n"
        for i in range(1, 11):
            content += f"### Teste {i}:\nPonto: 0<br>\nObservação: {obs[i]} (erro: {error_msg})<br>\n\n"
        m = re.search(r"## Considerações:\s*\n(.*?)(?:\n## Nota Final:|$)", original, re.DOTALL)
        consideracoes = m.group(1).strip() if m else ""
        content += f"## Considerações:\n{consideracoes}\n\n## Nota Final: 0.0\n"
        nota_path.write_text(content, encoding='utf-8')

    def update_nota_md_with_error(self, error_msg):
        self.update_nota_md_with_compilation_error(error_msg)

    def update_nota_md(self, results):
        nota_path = self.student_dir / "nota.md"
        original = nota_path.read_text(encoding='utf-8') if nota_path.exists() else ""
        obs = {}
        for i in range(1, 11):
            m = re.search(rf"### Teste {i}:\s*\n.*?\nObservação: (.*?)(?:\n|$)", original, re.DOTALL)
            obs[i] = m.group(1).strip() if m else "Valor esperado: [ver nota.md original]"
        content = "## Aceitação:\n\n"
        for i in range(1, 11):
            key = f"teste_{i}"
            if key in results:
                r = results[key]
                o = obs.get(i, "Valor esperado: [ver nota.md original]")
                if r.get('error'):
                    e = r['error']
                    if "Timeout" in e: o = f"{o} (timeout detectado)"
                    elif "loop" in e.lower(): o = f"{o} (loop detectado)"
                    else: o = f"{o} (erro: {e})"
                content += f"### Teste {i}:\nPonto: {r['score']:.1f}<br>\nObservação: {o}<br>\n\n"
            else:
                content += f"### Teste {i}:\nPonto: 0<br>\nObservação: {obs.get(i, '?')}<br>\n\n"
        m = re.search(r"## Considerações:\s*\n(.*?)(?:\n## Nota Final:|$)", original, re.DOTALL)
        consideracoes = m.group(1).strip() if m else ""
        loops = any(r.get('error') and ("Timeout" in r['error'] or "loop" in r['error'].lower())
                    for r in results.values() if isinstance(r, dict))
        if loops:
            consideracoes += "\n\n⚠️ Foram detectados timeouts/loops em alguns testes."
        total = sum(r['score'] for r in results.values() if 'score' in r)
        content += f"## Considerações:\n{consideracoes}\n\n## Nota Final: {total:.1f}\n"
        nota_path.write_text(content, encoding='utf-8')


# ================================================================
# MAIN
# ================================================================
def main():
    base_dir = Path.cwd()
    print_flush(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print_flush(f"{Colors.BOLD}Corretor Automático - Atividade 03 (Expressões Visitor){Colors.END}")
    print_flush(f"{Colors.CYAN}{'='*60}{Colors.END}")

    antlr_jar = base_dir / "antlr-4.13.2-complete.jar"
    if not antlr_jar.exists():
        antlr_jar = base_dir.parent / "antlr-4.13.2-complete.jar"
    if not antlr_jar.exists():
        print_flush(f"{Colors.RED}✗ ANTLR JAR não encontrado!{Colors.END}")
        return
    print_flush(f"{Colors.GREEN}✓ ANTLR JAR encontrado: {antlr_jar.name}{Colors.END}")

    nota_modelo = base_dir / "nota.md"
    if not nota_modelo.exists():
        print_flush(f"{Colors.RED}✗ nota.md não encontrado!{Colors.END}")
        return
    print_flush(f"{Colors.GREEN}✓ nota.md encontrado{Colors.END}")

    try:
        r = subprocess.run(["javac", "-version"], capture_output=True, text=True, timeout=5)
        print_flush(f"{Colors.GREEN}✓ javac disponível{Colors.END}")
    except:
        print_flush(f"{Colors.YELLOW}⚠ javac não disponível (alunos Java não poderão ser corrigidos){Colors.END}")

    alunos_dir = base_dir / "Alunos"
    if not alunos_dir.exists():
        print_flush(f"{Colors.RED}✗ Pasta 'Alunos' não encontrada!{Colors.END}")
        return

    students = [d for d in alunos_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    if not students:
        print_flush(f"{Colors.YELLOW}Nenhum aluno encontrado.{Colors.END}")
        return

    print_flush(f"\nEncontrados {len(students)} alunos")

    print_flush(f"\n{Colors.BOLD}Copiando ANTLR JAR e nota.md...{Colors.END}")
    for i, sd in enumerate(students, 1):
        try:
            nome = sd.name[:40] + "..." if len(sd.name) > 40 else sd.name
            dest_antlr = sd / "antlr-4.13.2-complete.jar"
            antlr_st = f"{Colors.YELLOW}ANTLR✓{Colors.END}"
            if not dest_antlr.exists():
                shutil.copy(antlr_jar, dest_antlr)
                antlr_st = f"{Colors.GREEN}ANTLR+{Colors.END}"
            shutil.copy(nota_modelo, sd / "nota.md")
            print_flush(f"  [{i}/{len(students)}] {nome} - {antlr_st} | {Colors.GREEN}NOTA+{Colors.END}")
        except Exception as e:
            print_flush(f"  [{i}/{len(students)}] {Colors.RED}✗ {e}{Colors.END}")

    print_flush(f"\n{Colors.BOLD}Iniciando correção...{Colors.END}")
    results = {}
    total_loops = 0
    for i, sd in enumerate(students, 1):
        try:
            print_flush(f"\n[{i}/{len(students)}] ", end="")
            g = ExpressionGrader(sd)
            score, details = g.grade_student()
            results[sd.name] = {"score": score, "details": details}
            if details:
                for k, v in details.items():
                    if isinstance(v, dict) and v.get('error') and ("Timeout" in v['error'] or "loop" in v['error'].lower()):
                        total_loops += 1
        except Exception as e:
            print_flush(f"{Colors.RED}Erro: {e}{Colors.END}")
            results[sd.name] = {"score": 0.0, "details": {"error": str(e)}}

    csv_file = base_dir / "notas_finais.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["Aluno", "Nota Final", "Status", "Timeouts"])
        for aluno, data in sorted(results.items(), key=lambda x: x[1]['score'], reverse=True):
            score = data['score']
            status = "Aprovado" if score >= 6.0 else "Reprovado"
            loops = 0
            if data.get('details'):
                for k, v in data['details'].items():
                    if isinstance(v, dict) and v.get('error') and ("Timeout" in v['error'] or "loop" in v['error'].lower()):
                        loops += 1
            w.writerow([aluno, f"{score:.1f}", status, loops])

    print_flush(f"\n{Colors.CYAN}{'#'*80}{Colors.END}")
    print_flush(f"{Colors.BOLD}RELATÓRIO FINAL{Colors.END}")
    print_flush(f"{Colors.CYAN}{'#'*80}{Colors.END}\n")
    print_flush(f"{'ALUNO':<35} {'NOTA':<8} {'STATUS':<10} {'TIMEOUTS'}")
    print_flush("-" * 65)
    for aluno, data in sorted(results.items(), key=lambda x: x[1]['score'], reverse=True):
        score = data['score']
        status = "Aprovado" if score >= 6.0 else "Reprovado"
        c = Colors.GREEN if score >= 6.0 else Colors.RED
        loops = 0
        if data.get('details'):
            for k, v in data['details'].items():
                if isinstance(v, dict) and v.get('error') and ("Timeout" in v['error'] or "loop" in v['error'].lower()):
                    loops += 1
        print_flush(f"{aluno:<35} {score:<8.1f} {c}{status:<10}{Colors.END} {loops}")

    scores = [d['score'] for d in results.values()]
    if scores:
        print_flush(f"\n{Colors.BOLD}ESTATÍSTICAS{Colors.END}")
        print_flush(f"{'Média:':<35} {sum(scores)/len(scores):.1f}")
        print_flush(f"{'Maior:':<35} {max(scores):.1f}")
        print_flush(f"{'Menor:':<35} {min(scores):.1f}")
        print_flush(f"{'Aprovados:':<35} {sum(1 for s in scores if s >= 6.0)}/{len(scores)}")
        print_flush(f"{'Taxa:':<35} {sum(1 for s in scores if s >= 6.0)/len(scores)*100:.0f}%")
        print_flush(f"{'Total timeouts:':<35} {total_loops}")

    print_flush(f"\nCSV: {csv_file}")


if __name__ == "__main__":
    main()
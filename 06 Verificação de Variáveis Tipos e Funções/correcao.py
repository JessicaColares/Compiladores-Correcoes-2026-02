import os
import subprocess
import shutil
import sys
import re
from pathlib import Path
import csv

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


class MiniCGrader:
    def __init__(self, student_dir):
        self.student_dir = Path(student_dir)
        self.student_name = self.student_dir.name

    def find_main_py(self):
        py_files = list(self.student_dir.glob("*.py"))
        if not py_files:
            return None
        ARQUIVOS_ANTLR = {
            'MiniCLexer', 'MiniCParser', 'MiniCListener', 'MiniCVisitor',
            'MiniCBaseListener', 'MiniCBaseVisitor',
        }
        py_files = [
            f for f in py_files
            if f.stem not in ARQUIVOS_ANTLR
            and not f.stem.endswith('Listener')
            and not f.stem.endswith('Visitor')
        ]
        if not py_files:
            return None
        priority_names = ["main.py", "Main.py", "Principal.py", "principal.py",
                          "app.py", "run.py", "VisitanteMiniC2.py"]
        for py_file in py_files:
            if py_file.name in priority_names:
                return py_file
        return py_files[0]

    def find_main_java(self):
        java_files = list(self.student_dir.glob("*.java"))
        for java_file in java_files:
            if java_file.name == "Main.java":
                return java_file
            try:
                with open(java_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'public static void main' in content:
                        return java_file
            except:
                pass
        return None

    def find_grammar_file(self):
        for f in self.student_dir.glob("*.g*"):
            if f.suffix in ['.g', '.g4']:
                return f
        return None

    def compile_grammar(self):
        grammar_file = self.find_grammar_file()
        if not grammar_file:
            return False, "Arquivo de gramática não encontrado"
        antlr_jar = self.student_dir / "antlr-4.13.2-complete.jar"
        if not antlr_jar.exists():
            return False, "ANTLR JAR não encontrado"
        try:
            cmd = ["java", "-jar", str(antlr_jar),
                   "-Dlanguage=Python3", "-visitor", "-listener",
                   str(grammar_file)]
            result = subprocess.run(cmd, cwd=self.student_dir,
                                    capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return False, f"Erro na compilação: {result.stderr[:300]}"
            return True, "Compilado com sucesso"
        except subprocess.TimeoutExpired:
            return False, "Timeout na compilação (>30s)"
        except Exception as e:
            return False, f"Erro: {str(e)}"

    def compile_java_files(self):
        java_files = list(self.student_dir.glob("*.java"))
        if not java_files:
            return False, "Nenhum arquivo Java encontrado"
        antlr_jar = self.student_dir / "antlr-4.13.2-complete.jar"
        if not antlr_jar.exists():
            return False, "ANTLR JAR não encontrado"
        try:
            cmd = ["javac", "-cp", str(antlr_jar)] + [str(f) for f in java_files]
            result = subprocess.run(cmd, cwd=self.student_dir,
                                    capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                return False, f"Erro na compilação Java:\n{result.stderr[:300]}"
            return True, "Compilado com sucesso"
        except FileNotFoundError:
            return False, "javac não encontrado."
        except subprocess.TimeoutExpired:
            return False, "Timeout na compilação Java (>60s)"
        except Exception as e:
            return False, f"Erro: {str(e)}"

    def detect_program_type(self, main_py):
        try:
            with open(main_py, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'sys.argv' in content and 'FileStream' in content:
                    return "arquivo"
                if 'sys.argv' in content:
                    return "argumento"
                if 'input(' in content:
                    return "interativo"
                return "argumento"
        except:
            return "desconhecido"

    # 🔥 v3: detecção inteligente — sucesso explícito primeiro
    def _tem_erro_no_output(self, output):
        if not output:
            return False
        output_lower = output.lower()

        # Palavras que indicam SUCESSO explícito (não tem erro)
        success_keywords = [
            'nenhum erro', 'sem erro', 'no error', '0 erro', 'zero erro',
            'análise concluída sem erros', 'analise concluida sem erros',
            'análise semântica concluída: nenhum erro',
            'analise semantica concluida: nenhum erro',
            'programa é válido', 'programa e valido',
            'código está logicamente perfeito', 'codigo esta logicamente perfeito',
            'sucesso', '[sucesso]', '✔ análise', '✓ análise',
            'análise léxica e sintática de', 'analise lexica e sintatica de',
            'análise semântica concluída: nenhum', 'analise semantica concluida: nenhum',
            'análise concluída: nenhum', 'analise concluida: nenhum',
            'lista de erros: []',
        ]
        for kw in success_keywords:
            if kw in output_lower:
                return False

        # Palavras-chave de erro
        error_keywords = [
            'error', 'erro',
            'mismatched', 'extraneous', 'no viable', 'expecting',
            'missing', 'unexpected', 'unterminated',
            'não declarada', 'nao declarada',
            'não declarado', 'nao declarado',
            'declarada mais de uma vez', 'declarado mais de uma vez',
            'redeclara', 'redeclared',
            'incompatibilidade', 'incompatible',
            'incompatível', 'incompativel',
            'deveria ser', 'esperado', 'esperava',
            'número de argumentos', 'numero de argumentos',
            'argumentos da funcao', 'argumentos da função',
            'tipos dos argumentos', 'tipos dos parametros',
            'operandos', 'operador',
            'break fora', 'continue fora',
            'deve aparecer dentro', 'dentro de um laco', 'dentro de um laço',
            'dentro de um while',
            'semantic', 'semântico', 'semantico',
            'tipo encontrado', 'tipo esperado',
            'não definida', 'nao definida', 'não definido', 'nao definido',
            'undefined', 'undeclared', 'redeclaration',
        ]
        for kw in error_keywords:
            if kw in output_lower:
                return True
        return False

    def run_test(self, test_file):
        test_path = (Path.cwd() / "Testes" / test_file).resolve()
        if not test_path.exists():
            return f"Teste não encontrado: {test_file}", True

        main_py = self.find_main_py()
        main_java = self.find_main_java()
        if not main_py and not main_java:
            return "Nenhum arquivo Python ou Java encontrado", False

        original_dir = os.getcwd()
        os.chdir(self.student_dir)
        try:
            temp_test = self.student_dir / test_file
            shutil.copy(test_path, temp_test)

            output = None
            has_error = False

            if main_java:
                class_files = list(self.student_dir.glob("*.class"))
                if not class_files:
                    compiled, msg = self.compile_java_files()
                    if not compiled:
                        return f"Erro na compilação Java: {msg}", True
                class_name = main_java.stem
                cmd = ["java", "-cp",
                       f".:{str(self.student_dir / 'antlr-4.13.2-complete.jar')}",
                       class_name, test_file]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                output = result.stdout + result.stderr
                has_error = result.returncode != 0
            elif main_py:
                program_type = self.detect_program_type(main_py)
                cmd = [sys.executable, str(main_py), test_file]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                output = result.stdout + result.stderr
                has_error = result.returncode != 0
                if not output or "No such file" in output:
                    with open(temp_test, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    cmd = [sys.executable, str(main_py), content]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                    output = result.stdout + result.stderr
                    has_error = result.returncode != 0

            if self._tem_erro_no_output(output):
                has_error = True

            return output, has_error
        except subprocess.TimeoutExpired:
            return "Timeout (15s)", True
        except Exception as e:
            return f"Erro: {str(e)}", True
        finally:
            os.chdir(original_dir)
            try:
                if temp_test.exists():
                    temp_test.unlink()
            except:
                pass

    def grade_student(self):
        print_flush(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
        print_flush(f"{Colors.BOLD}Avaliando: {self.student_name}{Colors.END}")
        print_flush(f"{Colors.CYAN}{'='*60}{Colors.END}")

        main_py = self.find_main_py()
        main_java = self.find_main_java()
        if not main_py and not main_java:
            print_flush(f"{Colors.RED}✗ Nenhum arquivo Python ou Java encontrado{Colors.END}")
            self.update_nota_md_all_fail("Nenhum arquivo Python ou Java encontrado")
            return 0.0, {}

        if main_py:
            print_flush(f"  Arquivo Python: {main_py.name}")
        if main_java:
            print_flush(f"  Arquivo Java: {main_java.name}")

        grammar_file = self.find_grammar_file()
        if not grammar_file:
            print_flush(f"{Colors.RED}✗ Nenhum arquivo de gramática encontrado{Colors.END}")
            self.update_nota_md_all_fail("Arquivo de gramática não encontrado")
            return 0.0, {}

        print_flush(f"  Gramática: {grammar_file.name}")

        if main_py:
            print_flush(f"\n{Colors.BOLD}Compilando gramática (Python)...{Colors.END}")
            compiled, msg = self.compile_grammar()
            if not compiled:
                print_flush(f"{Colors.RED}✗ {msg}{Colors.END}")
                self.update_nota_md_all_fail(msg)
                return 0.0, {}
            print_flush(f"{Colors.GREEN}✓ {msg}{Colors.END}")

        if main_java:
            print_flush(f"\n{Colors.BOLD}Compilando arquivos Java...{Colors.END}")
            compiled, msg = self.compile_java_files()
            if not compiled:
                print_flush(f"{Colors.RED}✗ {msg}{Colors.END}")
                self.update_nota_md_all_fail(msg)
                return 0.0, {}
            print_flush(f"{Colors.GREEN}✓ {msg}{Colors.END}")

        # 🔥 v3: teste10 com tipo (Opção A)
        tests = [
            ('teste1.c', True, 'Variável não declarada'),
            ('teste2.c', True, 'Redeclaração de variável'),
            ('teste3.c', True, 'Número de argumentos'),
            ('teste4.c', True, 'Tipos dos argumentos'),
            ('teste5.c', True, 'Compatibilidade de tipos'),
            ('teste6.c', True, 'Operandos int'),
            ('teste7.c', True, 'char + int é erro (operador aritmético exige int)'),
            ('teste8.c', False, 'Válido (break/continue)'),
            ('teste9.c', True, 'Break/continue fora do while'),
            ('teste10.c', False, 'Válido (função com parâmetros tipados)'),
        ]

        results = {}
        print_flush(f"\n{Colors.BOLD}Executando testes...{Colors.END}")
        for i, (test_file, should_error, description) in enumerate(tests, 1):
            print_flush(f"\n  {Colors.BOLD}Teste {i}:{Colors.END} {test_file} ({description})")
            output, has_error = self.run_test(test_file)

            if should_error:
                passed = has_error
                score = 1.0 if passed else 0.0
            else:
                passed = not has_error
                score = 1.0 if passed else 0.0

            if passed:
                print_flush(f"    {Colors.GREEN}✓ Passou{Colors.END}")
            else:
                print_flush(f"    {Colors.RED}✗ Falhou{Colors.END}")
                if output and len(output) > 0:
                    output_preview = output[:300].replace('\n', ' ').strip()
                    print_flush(f"    Saída: {output_preview}...")

            results[f"teste_{i}"] = {
                "file": test_file,
                "should_error": should_error,
                "description": description,
                "passed": passed,
                "score": score,
                "output": output[:500] if output else "",
            }

        total_score = sum(r["score"] for r in results.values())
        print_flush(f"\n{Colors.BOLD}Nota final: {total_score:.1f}/10.0{Colors.END}")
        self.update_nota_md(results)
        return total_score, results

    def update_nota_md_all_fail(self, error_msg):
        nota_path = self.student_dir / "nota.md"
        if not nota_path.exists():
            print_flush(f"{Colors.YELLOW}⚠ nota.md não encontrado em {self.student_name}{Colors.END}")
            return
        with open(nota_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if "Ponto:" in line and not line.strip().startswith("##"):
                new_lines.append("Ponto: 0.0\n")
            elif "## Nota Final:" in line:
                new_lines.append("## Nota Final: 0.0\n")
            else:
                new_lines.append(line)
        with open(nota_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    def update_nota_md(self, results):
        nota_path = self.student_dir / "nota.md"
        if not nota_path.exists():
            print_flush(f"{Colors.YELLOW}⚠ nota.md não encontrado em {self.student_name}{Colors.END}")
            return
        with open(nota_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        test_index = 1
        for line in lines:
            if "Ponto:" in line and not line.strip().startswith("##"):
                if test_index <= 10:
                    key = f"teste_{test_index}"
                    if key in results:
                        r = results[key]
                        new_lines.append(f"Ponto: {r['score']:.1f}\n")
                        test_index += 1
                        continue
                new_lines.append(line)
            else:
                new_lines.append(line)

        total = sum(r['score'] for r in results.values() if 'score' in r)
        for i, line in enumerate(new_lines):
            if "## Nota Final:" in line:
                new_lines[i] = f"## Nota Final: {total:.1f}\n"
                break

        with open(nota_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)


def main():
    base_dir = Path.cwd()
    print_flush(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print_flush(f"{Colors.BOLD}Corretor Automático - Atividade 06 (Verificação de Variáveis, Tipos e Funções){Colors.END}")
    print_flush(f"{Colors.CYAN}{'='*60}{Colors.END}")

    try:
        import pexpect
        print_flush(f"{Colors.GREEN}✓ pexpect disponível{Colors.END}")
    except ImportError:
        print_flush(f"{Colors.YELLOW}⚠ pexpect não instalado (opcional){Colors.END}")

    javac_available = shutil.which('javac') is not None
    if not javac_available:
        print_flush(f"{Colors.YELLOW}⚠ javac não encontrado{Colors.END}")
    else:
        print_flush(f"{Colors.GREEN}✓ javac disponível{Colors.END}")

    antlr_jar = base_dir / "antlr-4.13.2-complete.jar"
    if not antlr_jar.exists():
        antlr_jar = base_dir.parent / "antlr-4.13.2-complete.jar"
    if not antlr_jar.exists():
        print_flush(f"{Colors.RED}✗ ANTLR JAR não encontrado!{Colors.END}")
        return
    print_flush(f"{Colors.GREEN}✓ ANTLR JAR: {antlr_jar.name}{Colors.END}")

    nota_modelo = base_dir / "nota.md"
    if not nota_modelo.exists():
        print_flush(f"{Colors.RED}✗ nota.md não encontrado!{Colors.END}")
        return
    print_flush(f"{Colors.GREEN}✓ nota.md encontrado{Colors.END}")

    testes_dir = base_dir / "Testes"
    if not testes_dir.exists():
        print_flush(f"{Colors.RED}✗ Pasta 'Testes' não encontrada!{Colors.END}")
        return
    print_flush(f"{Colors.GREEN}✓ Pasta 'Testes' encontrada{Colors.END}")

    alunos_dir = base_dir / "Alunos"
    if not alunos_dir.exists():
        print_flush(f"{Colors.RED}✗ Pasta 'Alunos' não encontrada!{Colors.END}")
        return

    students = [d for d in alunos_dir.iterdir()
                if d.is_dir() and not d.name.startswith('.')]
    if not students:
        print_flush(f"{Colors.YELLOW}Nenhum aluno encontrado.{Colors.END}")
        return

    print_flush(f"\nEncontrados {len(students)} alunos")

    # ============================================================
    # COPIA ANTLR JAR E NOTA.MD PARA CADA ALUNO (SEMPRE SOBRESCREVE)
    # ============================================================
    print_flush(f"\n{Colors.BOLD}Copiando ANTLR JAR e nota.md (sobrescrevendo)...{Colors.END}")

    antlr_copiados = 0
    antlr_ja_tinha = 0
    nota_copiados = 0

    for i, sd in enumerate(students, 1):
        try:
            nome_curto = sd.name[:40] + "..." if len(sd.name) > 40 else sd.name

            # ANTLR JAR: só copia se não existir
            dest_antlr = sd / "antlr-4.13.2-complete.jar"
            if dest_antlr.exists():
                antlr_ja_tinha += 1
                antlr_status = f"{Colors.YELLOW}ANTLR✓{Colors.END}"
            else:
                shutil.copy(antlr_jar, dest_antlr)
                antlr_copiados += 1
                antlr_status = f"{Colors.GREEN}ANTLR+{Colors.END}"

            # NOTA.MD: SEMPRE SOBRESCREVE (para alinhar com testes atualizados)
            shutil.copy(nota_modelo, sd / "nota.md")
            nota_copiados += 1
            nota_status = f"{Colors.GREEN}NOTA+{Colors.END}"

            print_flush(f"  [{i}/{len(students)}] {nome_curto} - {antlr_status} | {nota_status}")
        except Exception as e:
            print_flush(f"  [{i}/{len(students)}] {Colors.RED}✗ {e}{Colors.END}")

    print_flush(f"\n{Colors.GREEN}✓ Resumo:{Colors.END}")
    print_flush(f"  ANTLR: {antlr_copiados} copiados, {antlr_ja_tinha} já tinham")
    print_flush(f"  NOTA: {nota_copiados} copiados (SEMPRE sobrescritos)")

    # ============================================================
    # AVALIAÇÃO
    # ============================================================
    print_flush(f"\n{Colors.BOLD}Iniciando correção...{Colors.END}")
    print_flush(f"Timeout por teste: {Colors.BOLD}15 segundos{Colors.END}\n")

    results = {}
    for i, student_dir in enumerate(students, 1):
        try:
            print_flush(f"\n[{i}/{len(students)}] ", end="")
            grader = MiniCGrader(student_dir)
            score, details = grader.grade_student()
            results[student_dir.name] = {"score": score, "details": details}
        except Exception as e:
            print_flush(f"{Colors.RED}Erro ao avaliar {student_dir.name}: {e}{Colors.END}")
            results[student_dir.name] = {"score": 0.0, "details": {"error": str(e)}}

    # ============================================================
    # GERA CSV
    # ============================================================
    csv_file = base_dir / "notas_finais.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Aluno", "Nota Final", "Status"])
        for aluno, data in sorted(results.items(), key=lambda x: x[1]['score'], reverse=True):
            score = data['score']
            status = "Aprovado" if score >= 5.0 else "Reprovado"
            writer.writerow([aluno, f"{score:.1f}", status])

    # ============================================================
    # RELATÓRIO FINAL
    # ============================================================
    print_flush(f"\n{Colors.CYAN}{'#'*80}{Colors.END}")
    print_flush(f"{Colors.BOLD}RELATÓRIO FINAL{Colors.END}")
    print_flush(f"{Colors.CYAN}{'#'*80}{Colors.END}\n")

    print_flush(f"{'ALUNO':<40} {'NOTA':<8} {'STATUS':<10}")
    print_flush("-" * 60)

    for aluno, data in sorted(results.items(), key=lambda x: x[1]['score'], reverse=True):
        score = data['score']
        status = "Aprovado" if score >= 5.0 else "Reprovado"
        status_color = Colors.GREEN if score >= 5.0 else Colors.RED
        nome = aluno[:38] + ".." if len(aluno) > 40 else aluno
        print_flush(f"{nome:<40} {score:<8.1f} {status_color}{status:<10}{Colors.END}")

    scores = [data['score'] for data in results.values()]
    if scores:
        print_flush(f"\n{Colors.BOLD}ESTATÍSTICAS{Colors.END}")
        print_flush(f"{'Média:':<40} {sum(scores)/len(scores):.1f}")
        print_flush(f"{'Maior nota:':<40} {max(scores):.1f}")
        print_flush(f"{'Menor nota:':<40} {min(scores):.1f}")
        print_flush(f"{'Aprovados:':<40} {sum(1 for s in scores if s >= 5.0)}/{len(scores)}")
        print_flush(f"{'Taxa de aprovação:':<40} {sum(1 for s in scores if s >= 5.0)/len(scores)*100:.0f}%")

    print_flush(f"\nCSV: {csv_file}")


if __name__ == "__main__":
    main()
import os
import subprocess
import shutil
import sys
import re
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


class MiniCGrader:
    def __init__(self, student_dir):
        self.student_dir = Path(student_dir)
        self.student_name = self.student_dir.name
        self.antlr_jar = self.student_dir / "antlr-4.13.2-complete.jar"

    # ================================================================
    # BUSCA DE ARQUIVOS
    # ================================================================
    def find_grammar_file(self):
        """Encontra o arquivo de gramática (.g ou .g4)"""
        for f in self.student_dir.glob("*.g*"):
            if f.suffix in ['.g', '.g4']:
                return f
        return None

    def find_main_py(self):
        """Encontra o arquivo Python principal"""
        py_files = list(self.student_dir.glob("*.py"))

        # Filtra arquivos gerados pelo ANTLR
        ARQUIVOS_ANTLR = {
            'MiniCLexer', 'MiniCParser', 'MiniCListener', 'MiniCVisitor',
            'MiniCBaseListener', 'MiniCBaseVisitor',
            'ExprLexer', 'ExprParser', 'ExprListener', 'ExprVisitor',
            'ExprBaseListener', 'ExprBaseVisitor',
        }
        py_files = [
            f for f in py_files
            if f.stem not in ARQUIVOS_ANTLR
            and not f.stem.endswith('Listener')
            and not f.stem.endswith('Visitor')
        ]

        if not py_files:
            return None

        # Prioriza main.py, Main.py, principal.py, etc.
        priority = ["main.py", "Main.py", "principal.py", "Principal.py",
                    "app.py", "run.py", "minic.py", "parser.py"]
        for py_file in py_files:
            if py_file.name in priority:
                return py_file

        # Qualquer outro .py que não seja gerado pelo ANTLR
        return py_files[0] if py_files else None

    # ================================================================
    # COMPILAÇÃO
    # ================================================================
    def compile_grammar(self):
        """Compila a gramática com ANTLR"""
        grammar_file = self.find_grammar_file()
        if not grammar_file:
            return False, "Arquivo de gramática não encontrado"

        if not self.antlr_jar.exists():
            return False, "ANTLR JAR não encontrado na pasta do aluno"

        try:
            cmd = [
                "java", "-jar", str(self.antlr_jar),
                "-Dlanguage=Python3", "-visitor", "-listener",
                str(grammar_file)
            ]
            result = subprocess.run(cmd, cwd=self.student_dir,
                                    capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                return False, f"Erro na compilação: {result.stderr[:300]}"

            return True, "Compilado com sucesso"
        except subprocess.TimeoutExpired:
            return False, "Timeout na compilação (>60s)"
        except Exception as e:
            return False, f"Erro: {str(e)}"

    # ================================================================
    # EXECUÇÃO DE TESTES
    # ================================================================
    def run_test(self, test_file, test_type):
        """Executa um teste específico"""
        test_path = Path("Testes") / test_type / test_file
        if not test_path.exists():
            return f"Teste não encontrado: {test_path}", True

        main_py = self.find_main_py()
        if not main_py:
            return "Nenhum arquivo Python encontrado", True

        # Copia o teste para a pasta do aluno
        temp_test = self.student_dir / test_file
        try:
            shutil.copy(test_path, temp_test)
        except Exception as e:
            return f"Erro ao copiar teste: {e}", True

        original_dir = os.getcwd()
        try:
            os.chdir(self.student_dir)
            cmd = [sys.executable, str(main_py), str(temp_test)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            output = result.stdout + result.stderr

            # Detecta erro: returncode != 0 OU mensagem de erro no output
            # (muitos programas ANTLR imprimem erros no stdout mas retornam 0)
            tem_erro = (
                result.returncode != 0
                or "error" in output.lower()
                or "erro" in output.lower()
                or "exception" in output.lower()
                or "line " in output.lower() and ":" in output  # erros do ANTLR: "line X:Y ..."
            )
            return output, tem_erro
        except subprocess.TimeoutExpired:
            return "Timeout", True
        except Exception as e:
            return f"Erro: {str(e)}", True
        finally:
            os.chdir(original_dir)
            if temp_test.exists():
                try:
                    temp_test.unlink()
                except:
                    pass

    # ================================================================
    # AVALIAÇÃO
    # ================================================================
    def grade_student(self):
        """Avalia o aluno em todos os testes"""
        print_flush(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
        print_flush(f"{Colors.BOLD}Avaliando: {self.student_name}{Colors.END}")
        print_flush(f"{Colors.CYAN}{'='*60}{Colors.END}")

        # Encontra o arquivo principal
        main_py = self.find_main_py()
        if not main_py:
            print_flush(f"{Colors.RED}✗ Nenhum arquivo Python encontrado{Colors.END}")
            self.update_nota_md_error("Nenhum arquivo Python encontrado")
            return 0.0, {}

        print_flush(f"  Arquivo Python: {main_py.name}")

        # Encontra a gramática
        grammar_file = self.find_grammar_file()
        if not grammar_file:
            print_flush(f"{Colors.RED}✗ Nenhum arquivo de gramática encontrado{Colors.END}")
            self.update_nota_md_error("Arquivo de gramática não encontrado")
            return 0.0, {}

        print_flush(f"  Gramática: {grammar_file.name}")

        # Compila a gramática
        compiled, msg = self.compile_grammar()
        if not compiled:
            print_flush(f"{Colors.RED}✗ {msg}{Colors.END}")
            self.update_nota_md_error(msg)
            return 0.0, {}

        print_flush(f"{Colors.GREEN}✓ Gramática compilada com sucesso{Colors.END}")

        # Lista de testes
        tests = ["teste1.c", "teste2.c", "teste3.c", "teste4.c", "teste5.c",
                 "teste6.c", "teste7.c", "teste8.c", "teste9.c", "teste10.c"]

        results = {}

        # --- Testes de Aceitação ---
        print_flush(f"\n{Colors.BOLD}--- Testes de Aceitação ---{Colors.END}")
        for i, test_file in enumerate(tests, 1):
            output, has_error = self.run_test(test_file, "Aceitacao")

            # Aceitação: esperamos que NÃO tenha erro
            passed = not has_error
            score = 0.5 if passed else 0.0
            obs = "certo" if passed else "não atingiu o resultado esperado"

            results[f"aceitacao_{i}"] = {
                "file": test_file,
                "passed": passed,
                "score": score,
                "obs": obs,
                "output": output[:300],
            }

            status = f"{Colors.GREEN}✓{Colors.END}" if passed else f"{Colors.RED}✗{Colors.END}"
            print_flush(f"  {status} {test_file}: {score:.1f} - {obs}")

        # --- Testes de Rejeição ---
        print_flush(f"\n{Colors.BOLD}--- Testes de Rejeição ---{Colors.END}")
        for i, test_file in enumerate(tests, 1):
            output, has_error = self.run_test(test_file, "Rejeicao")

            # Rejeição: esperamos que TENHA erro
            passed = has_error
            score = 0.5 if passed else 0.0
            obs = "certo" if passed else "não atingiu o resultado esperado"

            results[f"rejeicao_{i}"] = {
                "file": test_file,
                "passed": passed,
                "score": score,
                "obs": obs,
                "output": output[:300],
            }

            status = f"{Colors.GREEN}✓{Colors.END}" if passed else f"{Colors.RED}✗{Colors.END}"
            print_flush(f"  {status} {test_file}: {score:.1f} - {obs}")

        # Calcula nota final
        total_score = sum(r["score"] for r in results.values())
        print_flush(f"\n{Colors.BOLD}Nota final: {total_score:.1f}/10.0{Colors.END}")

        # Atualiza o nota.md do aluno
        self.update_nota_md(results)

        return total_score, results

    # ================================================================
    # NOTA.MD
    # ================================================================
    def update_nota_md_error(self, error_msg):
        """Atualiza o nota.md com mensagem de erro (zera tudo)"""
        nota_path = self.student_dir / "nota.md"

        content = "# Análise sintática da Linguagem MiniC\n\n"

        content += "## Aceitação:\n\n"
        for i in range(1, 11):
            content += f"### Teste {i}:\nPonto: 0<br>\nObservação: {error_msg}<br>\n\n"

        content += "## Rejeição:\n\n"
        for i in range(1, 11):
            content += f"### Teste {i}:\nPonto: 0<br>\nObservação: {error_msg}<br>\n\n"

        content += f"## Considerações:\n{error_msg}\n\n## Nota Final: 0.0\n"

        nota_path.write_text(content, encoding='utf-8')

    def update_nota_md(self, results):
        """Atualiza o arquivo nota.md do aluno com os resultados"""
        nota_path = self.student_dir / "nota.md"

        content = "# Análise sintática da Linguagem MiniC\n\n"

        # --- Aceitação ---
        content += "## Aceitação:\n\n"
        for i in range(1, 11):
            key = f"aceitacao_{i}"
            if key in results:
                r = results[key]
                content += f"""### Teste {i}:

Ponto: {r['score']:.1f}<br>
Observação: {r['obs']}<br>

"""
            else:
                content += f"### Teste {i}:\nPonto: 0<br>\nObservação: não executado<br>\n\n"

        # --- Rejeição ---
        content += "## Rejeição:\n\n"
        for i in range(1, 11):
            key = f"rejeicao_{i}"
            if key in results:
                r = results[key]
                content += f"""### Teste {i}:

Ponto: {r['score']:.1f}<br>
Observação: {r['obs']}<br>

"""
            else:
                content += f"### Teste {i}:\nPonto: 0<br>\nObservação: não executado<br>\n\n"

        # --- Considerações ---
        total = sum(r['score'] for r in results.values() if 'score' in r)
        content += f"""## Considerações:


## Nota Final: {total:.1f}
"""

        nota_path.write_text(content, encoding='utf-8')


# ================================================================
# MAIN
# ================================================================
def main():
    base_dir = Path.cwd()

    print_flush(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print_flush(f"{Colors.BOLD}Corretor Automático - Atividade 04 (Análise Sintática MiniC){Colors.END}")
    print_flush(f"{Colors.CYAN}{'='*60}{Colors.END}")

    # Verifica o ANTLR JAR na pasta principal
    antlr_jar = base_dir / "antlr-4.13.2-complete.jar"
    if not antlr_jar.exists():
        antlr_jar = base_dir.parent / "antlr-4.13.2-complete.jar"
    if not antlr_jar.exists():
        print_flush(f"{Colors.RED}✗ ANTLR JAR não encontrado!{Colors.END}")
        return
    print_flush(f"{Colors.GREEN}✓ ANTLR JAR encontrado: {antlr_jar.name}{Colors.END}")

    # Verifica o nota.md modelo
    nota_modelo = base_dir / "nota.md"
    if not nota_modelo.exists():
        print_flush(f"{Colors.RED}✗ nota.md não encontrado na pasta atual!{Colors.END}")
        return
    print_flush(f"{Colors.GREEN}✓ nota.md encontrado{Colors.END}")

    # Verifica a pasta Testes
    testes_dir = base_dir / "Testes"
    if not testes_dir.exists():
        print_flush(f"{Colors.RED}✗ Pasta 'Testes' não encontrada!{Colors.END}")
        return
    print_flush(f"{Colors.GREEN}✓ Pasta 'Testes' encontrada{Colors.END}")

    # Verifica a pasta Alunos
    alunos_dir = base_dir / "Alunos"
    if not alunos_dir.exists():
        print_flush(f"{Colors.RED}✗ Pasta 'Alunos' não encontrada!{Colors.END}")
        return

    # Lista alunos
    students = [d for d in alunos_dir.iterdir()
                if d.is_dir() and not d.name.startswith('.')]

    if not students:
        print_flush(f"{Colors.YELLOW}Nenhum aluno encontrado na pasta Alunos.{Colors.END}")
        return

    print_flush(f"\nEncontrados {len(students)} alunos")

    # ============================================================
    # COPIA ANTLR JAR E NOTA.MD PARA CADA ALUNO
    # ============================================================
    print_flush(f"\n{Colors.BOLD}Copiando ANTLR JAR e nota.md...{Colors.END}")

    antlr_copiados = 0
    antlr_ja_tinha = 0
    nota_copiados = 0

    for i, sd in enumerate(students, 1):
        try:
            nome_curto = sd.name[:40] + "..." if len(sd.name) > 40 else sd.name

            # Copia ANTLR JAR (só se não existir)
            dest_antlr = sd / "antlr-4.13.2-complete.jar"
            if dest_antlr.exists():
                antlr_ja_tinha += 1
                antlr_status = f"{Colors.YELLOW}ANTLR✓{Colors.END}"
            else:
                shutil.copy(antlr_jar, dest_antlr)
                antlr_copiados += 1
                antlr_status = f"{Colors.GREEN}ANTLR+{Colors.END}"

            # Copia nota.md (sempre sobrescreve)
            shutil.copy(nota_modelo, sd / "nota.md")
            nota_copiados += 1
            nota_status = f"{Colors.GREEN}NOTA+{Colors.END}"

            print_flush(f"  [{i}/{len(students)}] {nome_curto} - {antlr_status} | {nota_status}")

        except Exception as e:
            print_flush(f"  [{i}/{len(students)}] {Colors.RED}✗ {e}{Colors.END}")

    print_flush(f"\n{Colors.GREEN}✓ Resumo:{Colors.END}")
    print_flush(f"  ANTLR: {antlr_copiados} copiados, {antlr_ja_tinha} já tinham")
    print_flush(f"  NOTA: {nota_copiados} copiados (sobrescritos)")

    # ============================================================
    # AVALIAÇÃO
    # ============================================================
    print_flush(f"\n{Colors.BOLD}Iniciando correção...{Colors.END}")

    results = {}

    for i, student_dir in enumerate(students, 1):
        try:
            print_flush(f"\n[{i}/{len(students)}] ", end="")
            grader = MiniCGrader(student_dir)
            score, details = grader.grade_student()
            results[student_dir.name] = {
                "score": score,
                "details": details,
            }
        except Exception as e:
            print_flush(f"{Colors.RED}Erro ao avaliar {student_dir.name}: {e}{Colors.END}")
            results[student_dir.name] = {
                "score": 0.0,
                "details": {"error": str(e)},
            }

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

    print_flush(f"{'ALUNO':<45} {'NOTA':<8} {'STATUS':<10}")
    print_flush("-" * 65)

    for aluno, data in sorted(results.items(), key=lambda x: x[1]['score'], reverse=True):
        score = data['score']
        status = "Aprovado" if score >= 5.0 else "Reprovado"
        status_color = Colors.GREEN if score >= 5.0 else Colors.RED
        print_flush(f"{aluno:<45} {score:<8.1f} {status_color}{status:<10}{Colors.END}")

    scores = [data['score'] for data in results.values()]
    if scores:
        print_flush(f"\n{Colors.BOLD}ESTATÍSTICAS{Colors.END}")
        print_flush(f"{'Média:':<45} {sum(scores)/len(scores):.1f}")
        print_flush(f"{'Maior:':<45} {max(scores):.1f}")
        print_flush(f"{'Menor:':<45} {min(scores):.1f}")
        print_flush(f"{'Aprovados:':<45} {sum(1 for s in scores if s >= 5.0)}/{len(scores)}")
        print_flush(f"{'Taxa:':<45} {sum(1 for s in scores if s >= 5.0)/len(scores)*100:.0f}%")

    print_flush(f"\nCSV: {csv_file}")


if __name__ == "__main__":
    main()
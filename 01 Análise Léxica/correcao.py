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

PYTHON_EXEC = sys.executable


class URLGrader:
    def __init__(self, student_dir):
        self.student_dir = Path(student_dir)
        self.student_name = self.student_dir.name
        
    def find_grammar_file(self):
        for f in self.student_dir.glob("*.g*"):
            if f.suffix in ['.g', '.g4']:
                return f
        return None
    
    def find_main_py(self):
        py_files = list(self.student_dir.glob("*.py"))
        if not py_files:
            return None
        
        antlr_generated_suffixes = ['Lexer', 'Parser', 'Listener', 'Visitor']
        
        priority_names = [
            "main.py", "Main.py", "principal.py", "Principal.py",
            "teste.py", "testar_url.py", "url_test.py",
            "analisar_url.py", "analisador.py", "analisador_url.py",
            "analisador_lexico_url.py", "programa.py", "compiladorurl.py",
            "main_erick.py", "testa_url.py"
        ]
        
        for py_file in py_files:
            if py_file.name in priority_names:
                return py_file
        
        grammar_file = self.find_grammar_file()
        grammar_name = grammar_file.stem if grammar_file else None
        
        for py_file in py_files:
            name = py_file.stem
            is_antlr_generated = any(name.endswith(suffix) for suffix in antlr_generated_suffixes)
            if grammar_name and name == grammar_name:
                is_antlr_generated = True
            if not is_antlr_generated:
                return py_file
        
        return py_files[0]
    
    def detect_input_method(self, main_py):
        try:
            with open(main_py, 'r', encoding='utf-8') as f:
                content = f.read()
            has_input = 'input(' in content
            has_argv = 'sys.argv' in content
            if has_input and not has_argv:
                return 'input'
            elif has_argv and not has_input:
                return 'argv'
            elif has_input and has_argv:
                return 'both'
            return 'unknown'
        except:
            return 'unknown'
    
    def compile_grammar(self):
        grammar_file = self.find_grammar_file()
        if not grammar_file:
            return False, "Arquivo de gramática não encontrado"
        
        antlr_jar = self.student_dir / "antlr-4.13.2-complete.jar"
        if not antlr_jar.exists():
            return False, "ANTLR JAR não encontrado"
        
        try:
            cmd = ["java", "-jar", str(antlr_jar), "-Dlanguage=Python3", str(grammar_file)]
            result = subprocess.run(cmd, cwd=self.student_dir, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return False, f"Erro na compilação: {result.stderr}"
            return True, "Compilado com sucesso"
        except subprocess.TimeoutExpired:
            return False, "Timeout na compilação (30s)"
        except Exception as e:
            return False, f"Erro: {str(e)}"
    
    def run_test(self, url, should_accept):
        main_py = self.find_main_py()
        if not main_py:
            return None
        
        python_path = PYTHON_EXEC
        main_py_path = str(self.student_dir / main_py.name)
        
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.student_dir)
        
        input_method = self.detect_input_method(main_py)
        
        output = None
        
        if input_method in ('argv', 'both', 'unknown'):
            try:
                cmd = [python_path, main_py_path, url]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                                       cwd=str(self.student_dir), env=env)
                output = result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                output = "Timeout"
            except Exception:
                pass
        
        needs_stdin = (
            input_method in ('input', 'both') 
            or not output 
            or len(output.strip()) < 5 
            or output.strip().endswith('? ')
        )
        
        if needs_stdin:
            try:
                cmd = [python_path, main_py_path]
                result = subprocess.run(cmd, input=url + '\n', capture_output=True, text=True, timeout=10,
                                       cwd=str(self.student_dir), env=env)
                new_output = result.stdout + result.stderr
                if not output or len(new_output.strip()) > len(output.strip()):
                    output = new_output
            except subprocess.TimeoutExpired:
                if not output:
                    output = "Timeout"
            except Exception:
                pass
        
        return output
    
    def classify_output(self, output, url, should_accept):
        if output is None:
            return False
        
        output_lower = output.lower()
        output_stripped = output.strip()
        
        if not output_stripped:
            return not should_accept
        
        # ===== ERRO FORTE =====
        strong_error_keywords = [
            'traceback (most recent call last)',
            'attributeerror', 'importerror', 'modulenotfounderror',
            'syntaxerror', 'typeerror', 'nameerror',
        ]
        has_strong_error = any(kw in output_lower for kw in strong_error_keywords)
        
        # ===== AVISO DE REJEIÇÃO =====
        rejection_phrases = [
            'aviso:', 'warning:', 'atenção:', 'atencao:',
            'não foi reconhecid', 'nao foi reconhecid',
            'não reconhecid', 'nao reconhecid',
            'url completa não', 'url completa nao',
            'token principal não', 'token principal nao',
            'subtokens reconhecidos', 'sub-tokens reconhecidos',
            'sub tokens reconhecidos',
            'identificando as partes',
            'partes separadamente',
            'entrada nao foi reconhecida', 'entrada não foi reconhecida',
            'a url informada não', 'a url informada nao',
            'url inválida', 'url invalida',
            'token principal (url',
            'não reconheceu a entrada', 'nao reconheceu a entrada',
        ]
        has_rejection_phrase = any(phrase in output_lower for phrase in rejection_phrases)
        
        # ===== SUCESSO =====
        success_keywords = [
            'url válid', 'url valid', 'url válida', 'url valida',
            'reconhecid', 'reconheceu', 'aceit',
            'token: url', 'token url', 'token principal',
            'sucesso', 'ok:', 'válid', 'valid', 'correto',
        ]
        has_success = any(kw in output_lower for kw in success_keywords)
        
        # ===== URL COMPLETA =====
        has_full_url = url in output
        
        # ===== ÁRVORE SINTÁTICA =====
        # Estrutura MÍNIMA de URL: (url (protocolo http|https|ftp) ... (dominio ...)
        has_minimal_url_tree = bool(re.search(
            r'\(url\s+\(protocolo\s+(http|https|ftp).*?\(dominio\s+', 
            output_lower, re.DOTALL
        ))
        
        # Qualquer árvore de URL (mesmo incompleta)
        has_any_url_tree = bool(re.search(r'\(url\s', output_lower))
        
        # ===== DECISÃO =====
        if should_accept:
            if has_strong_error:
                return False
            if has_rejection_phrase:
                return False
            # Estrutura mínima de URL = reconhecida
            if has_minimal_url_tree:
                return True
            if has_full_url or has_success:
                return True
            return False
        else:
            if has_rejection_phrase or has_strong_error:
                return True
            # Árvore de URL SEM estrutura mínima = rejeitada (passou!)
            if has_any_url_tree and not has_minimal_url_tree:
                return True
            if not has_full_url and not has_success and not has_any_url_tree:
                return True
            return False
    
    def run_test_accept_flexible(self, url):
        output = self.run_test(url, should_accept=True)
        passed = self.classify_output(output, url, should_accept=True)
        if passed:
            return output, True
        
        if not url.startswith(('http://', 'https://', 'ftp://')):
            for proto in ['http://', 'https://', 'ftp://']:
                url_with_protocol = proto + url
                output2 = self.run_test(url_with_protocol, should_accept=True)
                passed2 = self.classify_output(output2, url_with_protocol, should_accept=True)
                if passed2:
                    return output2, True
        
        return output, False
    
    def grade_student(self):
        print_flush(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
        print_flush(f"{Colors.BOLD}Avaliando: {self.student_name}{Colors.END}")
        print_flush(f"{Colors.CYAN}{'='*60}{Colors.END}")
        
        main_py = self.find_main_py()
        if not main_py:
            print_flush(f"{Colors.RED}✗ Nenhum arquivo Python encontrado{Colors.END}")
            self.update_nota_md_all_fail()
            return 0.0
        
        print_flush(f"  Arquivo Python: {main_py.name}")
        
        input_method = self.detect_input_method(main_py)
        print_flush(f"  Método de entrada: {input_method}")
        
        grammar_file = self.find_grammar_file()
        if not grammar_file:
            print_flush(f"{Colors.RED}✗ Nenhum arquivo de gramática encontrado{Colors.END}")
            self.update_nota_md_all_fail()
            return 0.0
        
        print_flush(f"  Gramática: {grammar_file.name}")
        
        print_flush(f"\n{Colors.BOLD}Compilando gramática...{Colors.END}")
        compiled, msg = self.compile_grammar()
        if not compiled:
            print_flush(f"{Colors.RED}✗ {msg}{Colors.END}")
            self.update_nota_md_all_fail()
            return 0.0
        print_flush(f"{Colors.GREEN}✓ {msg}{Colors.END}")
        
        accept_tests = [
            "www.ufes.br",
            "https://github.com:443/user/repo?tab=projects#readme",
            "ftp://ftp.example.com/files/arquivo.txt",
            "http://localhost:8080/path/to/page",
            "https://192.168.1.1/admin?login=true",
            "ftp://downloads.site.com:2121/pub/software.zip",
            "http://site.com/pagina.html?search=compiladores#intro",
            "https://api.service.org/v1/data?limit=10",
            "https://ecampus.ufam.edu.br/ecampus/home/login",
            "mirror.ufes.br/iso/ubuntu.iso?mirror=br"
        ]
        
        reject_tests = [
            "httpx://site.invalido.com",
            "http:/site.com",
            "https//google.com",
            "ftp:example.com",
            "http://@@@.com",
            "https://site..com/path",
            "http://site.com:porta",
            "ftp://site.com/path?query=value#erro?#%",
            "http://site.com/path?=semchave",
            "https://site.com/path#!section"
        ]
        
        results = {}
        
        print_flush(f"\n{Colors.BOLD}--- Testes de Aceitação ---{Colors.END}")
        for i, url in enumerate(accept_tests, 1):
            output, passed = self.run_test_accept_flexible(url)
            score = 0.5 if passed else 0.0
            
            status = f"{Colors.GREEN}✓{Colors.END}" if passed else f"{Colors.RED}✗{Colors.END}"
            print_flush(f"  {status} Teste {i}: {url[:55]}")
            
            if not passed and output:
                preview = output[:120].replace('\n', ' ').strip()
                print_flush(f"      Saída: {preview}")
            
            results[f"aceitacao_{i}"] = {"url": url, "passed": passed, "score": score}
        
        print_flush(f"\n{Colors.BOLD}--- Testes de Rejeição ---{Colors.END}")
        for i, url in enumerate(reject_tests, 1):
            output = self.run_test(url, should_accept=False)
            passed = self.classify_output(output, url, should_accept=False)
            score = 0.5 if passed else 0.0
            
            status = f"{Colors.GREEN}✓{Colors.END}" if passed else f"{Colors.RED}✗{Colors.END}"
            print_flush(f"  {status} Teste {i}: {url[:55]}")
            
            if not passed and output:
                preview = output[:120].replace('\n', ' ').strip()
                print_flush(f"      Saída: {preview}")
            
            results[f"rejeicao_{i}"] = {"url": url, "passed": passed, "score": score}
        
        total_score = sum(r["score"] for r in results.values())
        print_flush(f"\n{Colors.BOLD}Nota final: {total_score:.1f}/10.0{Colors.END}")
        
        self.update_nota_md(results)
        return total_score
    
    def update_nota_md_all_fail(self):
        nota_path = self.student_dir / "NOTA.md"
        content = """# 01 Análise Léxica

## Aceitação:

### Teste 1
Ponto: 0<br>

### Teste 2
Ponto: 0<br>

### Teste 3
Ponto: 0<br>

### Teste 4
Ponto: 0<br>

### Teste 5
Ponto: 0<br>

### Teste 6
Ponto: 0<br>

### Teste 7
Ponto: 0<br>

### Teste 8
Ponto: 0<br>

### Teste 9
Ponto: 0<br>

### Teste 10
Ponto: 0<br>

## Rejeição:

### Teste 1
Ponto: 0<br>

### Teste 2
Ponto: 0<br>

### Teste 3
Ponto: 0<br>

### Teste 4
Ponto: 0<br>

### Teste 5
Ponto: 0<br>

### Teste 6
Ponto: 0<br>

### Teste 7
Ponto: 0<br>

### Teste 8
Ponto: 0<br>

### Teste 9
Ponto: 0<br>

### Teste 10
Ponto: 0<br>

# Nota Final: 0.0

Observação:
"""
        with open(nota_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def update_nota_md(self, results):
        nota_path = self.student_dir / "NOTA.md"
        if not nota_path.exists():
            print_flush(f"{Colors.YELLOW}⚠ NOTA.md não encontrado em {self.student_name}{Colors.END}")
            return
        
        with open(nota_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        test_index = 0
        in_acceptance = True
        
        for line in lines:
            if "## Rejeição:" in line:
                in_acceptance = False
                test_index = 0
                new_lines.append(line)
                continue
            
            if "Ponto:" in line:
                key = f"{'aceitacao' if in_acceptance else 'rejeicao'}_{test_index + 1}"
                if key in results:
                    new_lines.append(f"Ponto: {results[key]['score']:.1f}\n")
                    test_index += 1
                    continue
                new_lines.append(line)
            else:
                new_lines.append(line)
        
        total = sum(r['score'] for r in results.values() if 'score' in r)
        for i, line in enumerate(new_lines):
            if "# Nota Final:" in line:
                new_lines[i] = f"# Nota Final: {total:.1f}\n"
                break
        
        with open(nota_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)


def main():
    base_dir = Path.cwd()
    
    print_flush(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print_flush(f"{Colors.BOLD}Corretor Automático - Trabalho 01 (Análise Léxica de URLs){Colors.END}")
    print_flush(f"{Colors.CYAN}{'='*60}{Colors.END}")
    
    antlr_jar = base_dir / "antlr-4.13.2-complete.jar"
    if not antlr_jar.exists():
        antlr_jar = base_dir.parent / "antlr-4.13.2-complete.jar"
    if not antlr_jar.exists():
        print_flush(f"{Colors.RED}✗ ANTLR JAR não encontrado!{Colors.END}")
        return
    print_flush(f"{Colors.GREEN}✓ ANTLR JAR encontrado: {antlr_jar.name}{Colors.END}")
    
    nota_modelo = base_dir / "NOTA.md"
    if not nota_modelo.exists():
        print_flush(f"{Colors.RED}✗ NOTA.md não encontrado!{Colors.END}")
        return
    print_flush(f"{Colors.GREEN}✓ NOTA.md encontrado: {nota_modelo.name}{Colors.END}")
    
    alunos_dir = base_dir / "Alunos"
    if not alunos_dir.exists():
        print_flush(f"{Colors.RED}✗ Pasta 'Alunos' não encontrada!{Colors.END}")
        return
    
    students = [item for item in alunos_dir.iterdir() if item.is_dir() and not item.name.startswith('.')]
    
    if not students:
        print_flush(f"{Colors.YELLOW}Nenhum aluno encontrado.{Colors.END}")
        return
    
    print_flush(f"\nEncontrados {len(students)} alunos")
    print_flush(f"\n{Colors.BOLD}Copiando ANTLR JAR e NOTA.md...{Colors.END}")
    
    antlr_copied = 0
    antlr_skipped = 0
    nota_copied = 0
    
    for i, student_dir in enumerate(students, 1):
        try:
            nome_curto = student_dir.name[:40] + "..." if len(student_dir.name) > 40 else student_dir.name
            
            dest_antlr = student_dir / "antlr-4.13.2-complete.jar"
            if dest_antlr.exists():
                antlr_skipped += 1
                antlr_status = f"{Colors.YELLOW}ANTLR✓{Colors.END}"
            else:
                shutil.copy(antlr_jar, dest_antlr)
                antlr_copied += 1
                antlr_status = f"{Colors.GREEN}ANTLR+{Colors.END}"
            
            dest_nota = student_dir / "NOTA.md"
            shutil.copy(nota_modelo, dest_nota)
            nota_copied += 1
            nota_status = f"{Colors.GREEN}NOTA+{Colors.END}"
            
            print_flush(f"  [{i}/{len(students)}] {nome_curto} - {antlr_status} | {nota_status}")
        except Exception as e:
            print_flush(f"  [{i}/{len(students)}] {Colors.RED}✗ Erro: {e}{Colors.END}")
    
    print_flush(f"\n{Colors.GREEN}✓ Resumo:{Colors.END}")
    print_flush(f"  ANTLR: {antlr_copied} copiados, {antlr_skipped} já tinham")
    print_flush(f"  NOTA: {nota_copied} copiados")
    
    print_flush(f"\n{Colors.BOLD}Iniciando correção...{Colors.END}")
    results = {}
    
    for i, student_dir in enumerate(students, 1):
        try:
            print_flush(f"\n[{i}/{len(students)}] ", end="")
            grader = URLGrader(student_dir)
            score = grader.grade_student()
            results[student_dir.name] = score
        except Exception as e:
            print_flush(f"{Colors.RED}Erro ao avaliar {student_dir.name}: {e}{Colors.END}")
            results[student_dir.name] = 0.0
    
    csv_file = base_dir / "notas_finais.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Aluno", "Nota Final", "Status"])
        for aluno, score in sorted(results.items(), key=lambda x: x[1], reverse=True):
            status = "Aprovado" if score >= 5.0 else "Reprovado"
            writer.writerow([aluno, f"{score:.1f}", status])
    
    print_flush(f"\n{Colors.CYAN}{'#'*80}{Colors.END}")
    print_flush(f"{Colors.BOLD}RELATÓRIO FINAL{Colors.END}")
    print_flush(f"{Colors.CYAN}{'#'*80}{Colors.END}\n")
    print_flush(f"{'ALUNO':<55} {'NOTA':<8} {'STATUS':<10}")
    print_flush("-" * 75)
    
    for aluno, score in sorted(results.items(), key=lambda x: x[1], reverse=True):
        status = "Aprovado" if score >= 5.0 else "Reprovado"
        status_color = Colors.GREEN if score >= 5.0 else Colors.RED
        nome_exibicao = aluno[:52] + "..." if len(aluno) > 55 else aluno
        print_flush(f"{nome_exibicao:<55} {score:<8.1f} {status_color}{status:<10}{Colors.END}")
    
    scores = list(results.values())
    if scores:
        print_flush(f"\n{Colors.BOLD}ESTATÍSTICAS{Colors.END}")
        print_flush(f"{'Média:':<35} {sum(scores)/len(scores):.1f}")
        print_flush(f"{'Maior nota:':<35} {max(scores):.1f}")
        print_flush(f"{'Menor nota:':<35} {min(scores):.1f}")
        print_flush(f"{'Aprovados:':<35} {sum(1 for s in scores if s >= 5.0)}/{len(scores)}")
        print_flush(f"{'Taxa de aprovação:':<35} {sum(1 for s in scores if s >= 5.0)/len(scores)*100:.0f}%")
    
    print_flush(f"\nCSV: {csv_file}")


if __name__ == "__main__":
    main()
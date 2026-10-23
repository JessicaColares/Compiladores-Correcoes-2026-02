# Avaliação do trabalho 06 - Verificação de Variáveis, Tipos e Funções

### T1

```
int main() {
    x = 10; 
    return 0;
}
```

Ponto:

T2

```
int main() {
    int x;
    char x;
    return 0;
}
```

Ponto:

T3

```
int foo(int a, int b) { 
    return a + b; 
}

int main() {
    foo(1); 
    return 0;
}
```

Ponto:

T4

```
int foo(int a) { 
    return a; 
}

int main() {
    char c;
    c = 'a';
    foo(c); 
    return 0;
}
```

Ponto:

T5

```
int main() {
    int x;
    x = 2;
    char c;
    c = 'a';
    x = c;  
    c = x;   
    x += c;  
    c += x; 
    x *= c;
    return 0;
}
```

Ponto:

T6

```
int main() {
    int x;
    x = 5;
    char c;
    c = 'a'; 
    x = c + x;   
    x = c * x; 
    return 0;
}
```

Ponto:

T7

```
int main() {
    char c;
    int r;
    c = 'B';
    r = 10;
    return 0;
}
```

Ponto:

T8

```
int main() {
    int i;
    i = 0;
    while (i < 10) {
        if (i == 5) {
            break;
        }
        if (i % 2 == 0) {
            continue;
        }
        ++i;
    }
    return 0;
}
```

Ponto:

T9

```
int main() {
    if (1) {
        break;
    }
    continue;
    return 0;
}
```

Ponto:

T10

```
int calcular(int base, int incremento) {
    int resultado;
    resultado = base + incremento * 2;
    return resultado;
}
int main() {
    int val;
    char inicial;
    inicial = 'X';
    val = calcular(5, 3);
    return 0;
}
```

Ponto:

## Nota Final:

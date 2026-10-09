# Análise sintática da Linguagem MiniC

## Aceitação:

### Teste 1:

```
int x;
```

Ponto:  <br>
Observação: <br>

### Teste 2:

```
int a, b, c;
```

Ponto:  <br>
Observação: <br>

### Teste 3:

```
int main() {
    return 0;
}
```

Ponto:  <br>
Observação: <br>

### Teste 4:

```
int soma(int a, int b) {
    return a + b;
}
```

Ponto:  <br>
Observação: <br>

### Teste 5:

```
int multiplica(int a, int b) {
    int resultado;
    resultado = a * b;
    return resultado;
}
```

Ponto:  <br>
Observação: <br>

### Teste 6:

```
int verifica(int x) {
    int x;
    int y;
    if (x > 5) {
        x = 0;
    } else {
        x = 1;
    }

    return x;
}
```

Ponto:<br>
Observação: <br>

### Teste 7:

```
int incrementa() {
    int x;
    x = 0;
    while (x < 10) {
        ++x;  
    }
    return x;
}
```

Ponto:  <br>
Observação: <br>

### Teste 8:

```
int atualiza() {
    int y;
    y = 10;
    y *= 2; 
    return y;
}
```

Ponto:  <br>
Observação: <br>

### Teste 9:

```
int dummy() {
    ;  
}
```

Ponto:  <br>
Observação: <br>

### Teste 10:

```
int unarios(int x) {
    int x,y,z;  
    ++x;
    --y;
    return x/y*z;
  
}
```

Ponto:  <br>
Observação: <br>

## Rejeição:

### Teste 1:

```
int x;
x = 10;
x + 5;
```

Ponto:  <br>
Observação: <br>

### Teste 2:

```
while (x < 10) { x++; }
```

Ponto:  <br>
Observação: <br>

### Teste 3:

```
func(!) { }
```

Ponto:  <br>
Observação: <br>

### Teste 4:

```
int soma(a, b) [ ]
```

Ponto:  <br>
Observação: <br>

### Teste 5:

```
void erro() {
    5 = x;  
}
```

### Teste 6:

```
int teste() {
    if x > 5 { }  
}
```

Ponto:  <br>
Observação: <br>

### Teste 7:

```
int calcula() {
    int z; 
    z = x @ 2;  
    return z;
}
```

Ponto:  <br>
Observação: <br>

### Teste 8:

```
void exemplo() {
    int x  
}
```

Ponto:  <br>
Observação: <br>

### Teste 9:

```
return 0;
```

Ponto:  <br>
Observação: <br>

### Teste 10:

```
int teste() {
    soma(1, 2;  
}
```

Ponto:  <br>
Observação: <br>

## Considerações:

## Nota Final:


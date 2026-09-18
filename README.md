# Como usar o Antlr (versão linux)

### 1. Criar Variável de ambiente

```
python3 -m venv venv
```

### 2. Ativar variável de ambiente

```
source venv/bin/activate
```

### 3. Atualizar o pip

```
pip install update
```

### 4. Instalar as ferramentas Antlr

```
pip install antlr4-tools
```

### 5. Instalar o runtime

```
pip install antlr4-python3-runtime
```

### 6. Gerar os tokens

```
java -jar antlr-4.13.2-complete.jar -Dlanguage=Python3 URLLexer.g4
```

```
java -jar antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor -listener URL.g4
```

...

### 7. Conversor de MD para HTML

[https://markdowntohtml.com/](https://)

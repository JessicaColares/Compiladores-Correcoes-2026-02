**Este trabalho pode ser feito individual ou em duplas.**

Este trabalho deve considerar o analisador sintático feito para a linguagem ​**MiniC**​.

**O que deve ser feito:**

(1) A gramática atual do MiniC só tem o tipo int. Altere a gramática para incluir o tipo char. Portanto, inclua na regra "​**primary**​" mais uma opção, no caso, "char";

(2) Faça um analisador semântico que verifique:

**Parte 1 (cada questão vale um ponto)**

a) verificação de variáveis não declaradas;

b) verificação de variáveis declaradas mais de uma vez;

c) verificação do número de argumentos de chamadas de função;

d) verificação dos tipos dos argumentos (definidos e usados) nas chamadas de funções;

**Parte 2 (cada questão vale dois pontos)**

e) compatibilidade dos tipos na atribuição, incluindo as operações binárias (por exemplo, "+=", "\*=", etc);

f) operandos de operadores aritméticos como +, -, \*, /, % devem ser do tipo ​**int**​;

g) comandos BREAK e CONTINUE devem aparecer apenas dentro de laços WHILE.

#### **O que deve ser entregue:**

A gramática modificada, o novo Visitor/Listener e o programa principal. Compacte usando o ZIP. **Coloque o seu nome + "\_06" como nome do arquivo zipado.**

#### **OBSERVAÇÕES:**

(1) Coloque todos os erros em uma lista e imprima a lista no final da análise.

(2) Mostre a linha e a posição na linha onde ocorreu o erro;

(3) Sugiro que você resolva o problema por partes e depois faça a integração;

**(4) Use a linguagem de programação Python.**


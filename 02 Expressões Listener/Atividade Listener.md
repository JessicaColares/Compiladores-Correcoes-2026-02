Este trabalho é individual.

Baseado nos slides e na gramática a seguir, use o padrão de projeto LISTENER para implementar a execução das operações da gramática, ou seja, fatorial, valor absoluto, potenciação, divisão, multiplicação, soma e subtração, sendo que as expressões podem estar entre parêntesis.

Entregue o programa que implementa o LISTENER e o programa principal que instancia o léxico, sintático e o avaliador de expressões (LISTENER). 

Comprima todos os arquivos em um único arquivo zipado. Coloque o nome do arquivo o nome o aluno.

- - - - - - -

grammar Expr;

root: expr EOF;

expr: '(' expr ')' # Parent

    | expr '^' expr # Pot

    | expr ('*'|'/') expr # MultDiv

    | expr ('+'|'-') expr # SomaSub

    | (abs_ | fact) # Func

    | ('-')? NUM # Number

    ;

abs_ : 'abs' '(' expr ')';

fact : 'fat' '(' expr ')';

NUM : [0-9]+('.'[0-9]+)?;

WS : [ \n\r\t]+ -> skip;

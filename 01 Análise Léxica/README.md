Em um compilador, o analisador léxico funciona em conjunto com o analisador sintático. Neste trabalho vamos desenvolver somente um **analisador léxico** para identificar URLs, incluindo: protocolo (opcional), domínio, porta (opcional), caminho (opcional), parâmetros de consulta (opcional) e fragmentos (opcional).

As URLs servem para identificar recursos na Internet e são compostas por várias partes distintas, cada uma com sua funcionalidade e sintaxe específica.

* ​**Protocolo**(opicional)​: indicam o método ou o tipo de serviço utilizado para acessar o recurso na web. Vamos considerar somente os protocolos http, https e ftp.
* ​**Domínio**​: Nome do host ou IP que indica o servidor onde o recurso está localizado.
* **Porta** (opcional): Número da porta no servidor para conexão, padrão é 80 para HTTP e 443 para HTTPS.
* ​**Caminho**​: Caminho no servidor onde o recurso específico está localizado.
* **Query** (opcional): Uma string de consulta que contém parâmetros adicionais para o servidor. Geralmente é formatada como chave=valor e separada por &. Eles são importantes em muitas aplicações web para filtrar conteúdo, identificar sessões, passar configurações, entre outros. Alguns exemplos comuns incluem:

o   ?user\_id=123: Identifica um usuário específico.

o   ?page=4: Indica uma página específica nos resultados.

o   ?search=keyword: Passa uma palavra-chave de busca.

o   ?sort=asc&field=price: Instruções para ordenação de conteúdo.

* ·       **Fragmento** (opcional): Uma âncora para ir a uma seção específica dentro do recurso.

**Exemplos de URLs válidas**

Exemplo 1: URL com HTTP

​**[http://www.example.com:80/path/to/file?search=query&sort=ascending#section2](http://www.example.com/path/to/file?search=query&sort=ascending#section2)**​. Nesta URL o protocolo é http; o domínio é [www.example.com](http://www.example.com/); a porta é 80; o caminho é /path/to/file; a query é search=query&sort=ascending; e o fragmento é section2.

Exemplo 2: URL com HTTPS

​**[https://secure.example.com/register?user=abc&token=123#signup](https://secure.example.com/register?user=abc&token=123#signup)**​. Nesta URL o protocolo é https; domínio é secure.example.com; caminho é /register; Query é user=abc&token=123; e fragmento é signup.

Exemplo 3: URL com FTP

​**ftp://example.com/downloads/file.zip**​. Nesta URL o protocolo é ftp; domínio é example.com; e caminho é /downloads/file.zip.

Gere uma gramática para este analisador léxico que contenha um token principal, que obviamente deve ser composto de outros tokens secundários. Use **expressões regulares** para identificar cada item das URLs.

Gere um programa Python que instancie a(s) classe(s) do analisador léxico (gerado(s) pelo ANTLR), receba o texto da URL a ser testada como parâmetro do programa e imprima o TOKEN e o VALOR, caso o token principal seja reconhecido.

Caso o token principal não tenha sido reconhecido, imprimir cada sub-token reconhecido.

**Observações:**

1. As saídas devem ser impressas no terminal, ou seja, não devem ser gerados arquivos de saída;
2. Lembre que **não é objetivo** verificar se a URL está sintaticamente correta. Por exemplo, query e fragmento não são comuns em URLs FTP, mas você aceitará, caso seja fornecido. Não esqueça que a análise **efetiva** será feita somente nas análises sintática e semântica;
3. Use “lexer grammar <NOME-DA-SUA-GRAMÁTICA>” no início da gramática;
4. Gerar uma mensagem de **erro** (ou ​**aviso**​) caso o token principal não seja reconhecido;
5. Entregue somente ​**dois arquivos**​: a gramática e o programa em Python. Comprima os dois arquivos utilizando o compactador ZIP e coloque seu nome como nome do arquivo ​**zipado**​;
6. Geralmente utilizamos scripts para ajudar na correção. Se você não seguir as recomendações acima o teu trabalho pode não ser corrigido e, neste caso o teu trabalho valerá no máximo 5 pontos.


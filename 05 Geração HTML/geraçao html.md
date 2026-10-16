Baseado nas aulas e slides sobre como gerar páginas web, altere o parser para, além de verificar se a entrada está de acordo com a gramática, que também inclua **três** funcionalidades descritas a seguir.

(1) um menu de seleção simples. A entrada fornecerá o identificador do menu, o rótulo do menu, os identificadores e rótulos de cada opção do menu. Veja o exemplo abaixo.

```
<label for="cars">Choose a car:</label>
<select name="cars" id="cars">
  <option value="volvo">Volvo</option>
  <option value="saab">Saab</option>
  <option value="mercedes">Mercedes</option>
  <option value="audi">Audi</option>
</select>
```

(2) um botão que receba da entrada o rótulo do botão e ação quando clicar deve ser necessariamente um alerta. Para tanto, a entrada também fornecerá o que será mostrado no alerta. Veja o exemplo abaixo.

```
<button type="button" onclick="alert('Hello world!')">Click Me!</button>
```

(3) uma tabela que inclua uma linha de cabeçalho (header) + linhas da tabela + legenda (caption). O exemplo abaixo mostra uma definição de uma tabela em HTML com todos esses elementos.

```
<table>
  <caption>Monthly savings</caption>
  <tr>
    <th>Month</th>
    <th>Savings</th>
  </tr>
  <tr>
    <td>January</td>
    <td>$100</td>
  </tr>
  <tr>
    <td>February</td>
    <td>$50</td>
  </tr>
</table>
```

Altere a gramática dos slides para incluir as **três** funcionalidades acima da seguinte forma:

```
qMenu: 'MENU' str_ str_ menuOpcoes;
menuOpcoes: '(' menuOpcao (',' menuOpcao)* ')';
menuOpcao: str_ ':' str_;
```

```
qBotao: 'BOTAO' str_ str_;
```

```
qTabela: 'TABELA' str_ linhaCabecalho linhaDados;
linhaCabecalho: '(' str_ (',' str_)* ')';
linhaDados: '(' linha (',' linha)* ')';
linha: '(' str_ (',' str_)* ')';
```

No site [https://www.w3schools.com/tags/tag\_select.asp](https://www.w3schools.com/tags/tag_select.asp) é possível testar as tuas próprias tags HTML.

**Entregável:**

Implementar um analisador léxico + sintático + semântico que, a partir da gramática, gere uma página HTML usando VISITOR ou LISTENER. **Use obrigatoriamente a linguagem de programação Python.**

Gere uma entrada e experimente para verificar se o gerador de página HTML está funcionando.

Entregue cinco arquivos: a gramática, o visitor (ou listener), o programa principal, a entrada de teste e a página HTML resultante Comprima os arquivos usando o "zip" (tem que ser zip). **Coloque o seu nome + "\_05" como nome do arquivo zipado.**

Para facilitar, segue em anexo a gramática e o visitor que mostrei em sala de aula.



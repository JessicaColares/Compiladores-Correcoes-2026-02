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
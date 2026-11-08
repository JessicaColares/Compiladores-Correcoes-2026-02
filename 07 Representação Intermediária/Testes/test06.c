int verifica(int x) {
    if (x > 5) {
        x = 0;
    } else {
        x = 1;
    }

    return x;
}

int main(){
    verifica(5);

}

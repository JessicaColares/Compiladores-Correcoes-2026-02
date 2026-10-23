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
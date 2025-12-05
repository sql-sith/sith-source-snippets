#include <stdio.h>

int main() {
    int x = 0;
    int y = x++ + x; // what are x and y after this line?
    printf("x = %d, y = %d\n", x, y);
    return 0;
}

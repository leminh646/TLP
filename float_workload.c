#include <stdio.h>
#include <math.h>

#define SIZE 10000000

int main() {
    double sum = 0.0;

    for (int i = 1; i <= SIZE; i++) {
        double val = sin(i) * cos(i) + sqrt(i);
        sum += val / tan(i);
    }

    printf("Final sum: %f\n", sum);
    return 0;
}

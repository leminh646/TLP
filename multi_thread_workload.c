#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <math.h>
#include <sched.h>
#include <string.h>
#include <unistd.h>

#define THREADS 2
#define CACHE_LINE_SIZE 64
#define PREFETCH_DIST 16

struct ThreadData {
    int thread_id;
    double *a;
    double *b;
    double *c;
    double alpha;
    int start;
    int end;
};

void* daxpy_thread(void* arg) {
    struct ThreadData *data = (struct ThreadData*)arg;
    int i;
    
    // Set thread affinity
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(data->thread_id, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);

    // Process data in chunks with prefetching
    for (i = data->start; i < data->end; i++) {
        // Prefetch next elements
        if (i + PREFETCH_DIST < data->end) {
            __builtin_prefetch(&data->a[i + PREFETCH_DIST], 0, 0);
            __builtin_prefetch(&data->b[i + PREFETCH_DIST], 0, 0);
            __builtin_prefetch(&data->c[i + PREFETCH_DIST], 1, 0);
        }
        
        // Perform DAXPY operation
        data->c[i] = data->alpha * data->a[i] + data->b[i];
    }
    
    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <vector_size>\n", argv[0]);
        return 1;
    }

    int vector_size = atoi(argv[1]);
    if (vector_size <= 0) {
        fprintf(stderr, "Vector size must be positive\n");
        return 1;
    }

    double alpha = 2.0;
    
    // Allocate aligned memory for vectors
    double *a = (double*)aligned_alloc(CACHE_LINE_SIZE, vector_size * sizeof(double));
    double *b = (double*)aligned_alloc(CACHE_LINE_SIZE, vector_size * sizeof(double));
    double *c = (double*)aligned_alloc(CACHE_LINE_SIZE, vector_size * sizeof(double));

    if (!a || !b || !c) {
        fprintf(stderr, "Memory allocation failed\n");
        return 1;
    }

    // Initialize vectors
    for (int i = 0; i < vector_size; i++) {
        a[i] = i * 0.1;
        b[i] = i * 0.2;
        c[i] = 0.0;
    }

    // Create thread data structures
    pthread_t threads[THREADS];
    struct ThreadData thread_data[THREADS];
    int chunk_size = (vector_size + THREADS - 1) / THREADS;

    // Create and start threads
    for (int i = 0; i < THREADS; i++) {
        thread_data[i].thread_id = i;
        thread_data[i].a = &a[i * chunk_size];
        thread_data[i].b = &b[i * chunk_size];
        thread_data[i].c = &c[i * chunk_size];
        thread_data[i].alpha = alpha;
        thread_data[i].start = 0;
        thread_data[i].end = (i == THREADS - 1) ? vector_size - (i * chunk_size) : chunk_size;

        if (pthread_create(&threads[i], NULL, daxpy_thread, &thread_data[i]) != 0) {
            fprintf(stderr, "Failed to create thread %d\n", i);
            return 1;
        }
    }

    // Wait for all threads to complete
    for (int i = 0; i < THREADS; i++) {
        if (pthread_join(threads[i], NULL) != 0) {
            fprintf(stderr, "Failed to join thread %d\n", i);
            return 1;
        }
    }

    // Verify results (optional)
    double expected = 0.0;
    for (int i = 0; i < vector_size; i++) {
        expected = alpha * a[i] + b[i];
        if (fabs(c[i] - expected) > 1e-6) {
            fprintf(stderr, "Verification failed at index %d: got %f, expected %f\n", i, c[i], expected);
            return 1;
        }
    }

    // Clean up
    free(a);
    free(b);
    free(c);

    return 0;
}

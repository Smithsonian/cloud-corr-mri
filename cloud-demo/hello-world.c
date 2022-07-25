#include <stdio.h>
#include <mpi.h>

int main(int argc, char **argv)
{
   int core;
   
   MPI_Init(&argc,&argv);
   MPI_Comm_rank(MPI_COMM_WORLD, &core);
     
   printf("Hello World from Core %d\n", core);
            
   MPI_Finalize();
}

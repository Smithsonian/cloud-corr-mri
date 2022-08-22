#include <stdio.h>
#include <mpi.h>
#include <unistd.h>
#include <limits.h>

int main(int argc, char **argv)
{
   int core;
   char hostname[HOST_NAME_MAX+1];
   
   MPI_Init(&argc,&argv);
   MPI_Comm_rank(MPI_COMM_WORLD, &core);

   gethostname(hostname, HOST_NAME_MAX+1);
   printf("Hello World from Core %d hostname %s\n", core, hostname);
            
   MPI_Finalize();
}

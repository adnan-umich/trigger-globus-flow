/*
 "Hello World" MPI converted to test program!
*/
#include <mpi.h>

#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>

#include <unistd.h> // gethostname

typedef unsigned long long u64; 

#define _GNU_SOURCE
#define __USE_GNU
#include <assert.h>
#include <sched.h>
#include <stdbool.h>
#include <stdlib.h>
#include <unistd.h>
typedef struct {
	int NodeIndex;
	int CoreIndex;
	u64 cpumask;
	pid_t pid;
	char Name[512];	
} RankCoreInfo;

pid_t pid;
u64 bitmask=0;

void collect_affinity()
{
    // This function is very senative to type size or number of bits!
    cpu_set_t mask;
    u64 nproc, i;
    char str[1024];

    pid = getpid();
  
    //printf("pid: %lu \n", pid);
    sprintf(str, "taskset -p %lu \n", pid);
    system(str);
    if (sched_getaffinity(pid, sizeof(cpu_set_t), &mask) == -1)
    {
        perror("sched_getaffinity");
        assert(false);
    }
    nproc = sysconf(_SC_NPROCESSORS_ONLN);
    //printf("pid: %lu, Core count: %lu, Affinity mask is: 0b", pid, nproc);
    bitmask = 0;
    for (i = 0; i < nproc; i++) 
    { // This does not work if there are more than 64 cores!
        int bit = 0;
        if(CPU_ISSET(i, &mask))
        {
          u64 b = 1;
          bit=1;
          bitmask += b << i;
	  //printf("[%d]", i);
        }
        //printf("%d", bit); 
    }
    //printf("  , 0x%09x\n", bitmask);
}

int HBitCount(u64 n)
{
	int count = 0;
	while (n)
	{
		if(n & 1) count++;
        	n >>= 1;
	}
	return count;
}

// The is risk of buffer over flow with this function:
int run(char *cmd, char *out)
{
	int i,s;
	char *buf;
	FILE *ms;
	buf = out;

	//printf("cmd:%s\n",cmd);
	ms = popen(cmd, "r");
	setvbuf(ms, NULL, _IONBF, 0);
	
	if(ms)
	{
		s=0;
		i = fgetc(ms);
		while ( i != EOF )
		{
			//putchar(i);
			buf[s] = i; s++;
			i = fgetc(ms);
		}
		buf[s] = '\0';
		pclose(ms);
		return 0;
	}
	return -1;
}


#define JOB_LOCAL 1
#define JOB_PBS 2
#define JOB_SLURM 3
int JobType =  JOB_LOCAL;
int NodeCount = 1;
int NodeIndex = -1;
int CoreIndex = -1;

int GetIntEnv(const char *var)
{
#if 0
	char cmd[1024];
	char out[10240];
	sprintf( cmd, "echo $%s\n", var);
	run(cmd, out);
#else
	const char *out = getenv(var);
#endif
	if(out) return atoi(out);
	return 0;
}

void collect_job_info()
{
	int i;

	i = GetIntEnv("SLURM_JOB_NUM_NODES");
	if(i>0)
	{
		NodeCount = i;
		JobType = JOB_SLURM;
		
		i = GetIntEnv("SLURM_NODEID");
		if(i>-1) NodeIndex=i;
		CoreIndex = GetIntEnv("SLURM_PROCID");
		return;
	}
	i = GetIntEnv("PBS_NUM_NODES");
	if(i>0)
	{
		NodeCount = i;
		JobType = JOB_PBS;
		
		i = GetIntEnv("PBS_O_NODENUM");
		if(i>-1) NodeIndex=i;
		CoreIndex = GetIntEnv("PBS_O_VNODENUM");
		return;
	}
	NodeIndex = 0;
	MPI_Comm_rank(MPI_COMM_WORLD,&CoreIndex);
}


#define BUFSIZE 512
#define TAG 0
#define TAG_NODEINFO 1


int main(int argc, char *argv[])
{
	char idstr[BUFSIZE];
	char *node;
	char buff[BUFSIZE];
	int numprocs;
	int myid;
	int i,ret=0;
	int bSleep = 0;
	RankCoreInfo myInfo;
	RankCoreInfo *RankInfo = NULL;
	MPI_Status stat;
	
	setbuf(stdout, NULL); // This removes the buffer for stdout!
	// Now there no delay in the output.
	
	/* MPI programs start with MPI_Init; all 'N' processes exist thereafter */
	MPI_Init(&argc,&argv);
	/* find out how big the SPMD world is */
	MPI_Comm_size(MPI_COMM_WORLD,&numprocs);
	/* and this processes' rank is */
	MPI_Comm_rank(MPI_COMM_WORLD,&myid);

	gethostname(myInfo.Name, BUFSIZE); // get name of node
	node = myInfo.Name;
	sleep(myid);
	collect_affinity();
	collect_job_info();
	
	printf("% 4d: NodeCount=% 3d NodeIndex=% 3d CoreIndex=% 3d\n", myid, NodeCount, NodeIndex, CoreIndex); 
 	//system("printenv | grep SLURM_NODEID; printenv | grep SLURM_GTIDS\n"); // Usefull for debugging!
	myInfo.NodeIndex = NodeIndex;
	myInfo.CoreIndex = CoreIndex;
	myInfo.cpumask = bitmask;
	myInfo.pid = pid;

	if(numprocs<2)
	{
		printf("Error: invalid test, 2 ranks are required for MPI test!\n"); 
		ret=-2;
	}else if(myid == 0)
	{
		RankInfo = (RankCoreInfo *) calloc(numprocs, sizeof(RankCoreInfo));
		 
		if(RankInfo)
		{
			RankInfo[0] = myInfo;
		}else
			printf("Error: calloc failed(RankInf)!\n");
	}

	/* At this point, all programs are running equivalently, the rank
	distinguishes the roles of the programs in the SPMD model, with
	rank 0 often used specially... */
	if(myid == 0)
	{
		sleep(numprocs); // Wait for other ranks!
		printf("% 4d: We have %d ranks\n", myid, numprocs);
		printf("% 4d:         Rank % 4d on %s , (PID: % 8d, CPU_Mask: 0x%012llx) \n", myid, myid, node, pid, bitmask);
		for(i=1;i<numprocs;i++)
		{
			sprintf(buff, "Rank % 4d. Are you there?", i);
			MPI_Send(buff, BUFSIZE, MPI_CHAR, i, TAG, MPI_COMM_WORLD);
		}
		for(i=1;i<numprocs;i++)
		{
			if(MPI_Recv(buff, BUFSIZE, MPI_CHAR, i, TAG, MPI_COMM_WORLD, &stat) == MPI_SUCCESS)
			{
				printf("% 4d: %s\n", myid, buff);
				if(MPI_Recv(&(RankInfo[i]), sizeof(RankCoreInfo), MPI_CHAR, i, TAG_NODEINFO, MPI_COMM_WORLD, &stat) == MPI_SUCCESS)
				{
					printf("      Node = % 3d, Core = % 3d, PID = % 9lu, CPUmask = 0x%012llx \n", RankInfo[i].NodeIndex, RankInfo[i].CoreIndex, RankInfo[i].pid, RankInfo[i].cpumask);
				} else ret=-1;
			}else ret=-1;
		}
	}
	else
	{
		/* receive from rank 0: */
		MPI_Recv(buff, BUFSIZE, MPI_CHAR, 0, TAG, MPI_COMM_WORLD, &stat);
		sprintf(idstr, "\n% 4d: Yes'm.  Rank % 4d on %s , (PID: % 8d, CPU_Mask: 0x%012llx) ", myid, myid, node, pid, bitmask);
		strncat(buff, idstr, BUFSIZE-1);
		strncat(buff, "reporting for duty", BUFSIZE-1);
		/* send to rank 0: */
		MPI_Send(buff, BUFSIZE, MPI_CHAR, 0, TAG, MPI_COMM_WORLD);
		MPI_Send(&myInfo, sizeof(RankCoreInfo), MPI_CHAR, 0, TAG_NODEINFO, MPI_COMM_WORLD);
	}
	if(myid == 0)
	{
		if(ret==0)
		{
			printf("% 4d: Everybody's here. Let's get this show on the road.\n", myid);
			if(bSleep) printf("I will sleep for 60 seconds.\n");
			if(RankInfo)
			{
				int N = NodeCount;
				int cores[N];
				int ranks[N];
				u64 masks[N];
				char *host[N];
				int n, fn, i, AffinErr=0, hcErr=0;
				
				printf("Testing to see if all rank have at least one CPU core on each node:\n");
				for(n=0;n<N;n++)
				{
					cores[n] = 0;
					ranks[n] = 0;
					masks[n] = 0;
					host[n] = NULL;
				}
				
				for(i=0;i<numprocs;i++)
				{
					char *name = NULL;
			 		n = RankInfo[i].NodeIndex;
					name = RankInfo[i].Name;
					if(n >= N) n=0;
					if(host[n] == NULL) host[n] = name;
					
					if(strcmp(host[n], name) != 0)
					{ // Index mismatch: 
						hcErr++;
						n = 0; fn = 0;
						while(n<N) // find correct index
						{
							fn = n;
							if(host[n] == NULL) // empty index
								n=N;
							else if(strcmp(host[n], name) == 0) //found
								n=N;
							n++;
						}
						n = fn;
						if(host[n] == NULL)
							host[n] = name;
					}
					
					masks[n] |=  RankInfo[i].cpumask;
					ranks[n]++;

				}
				for(n=0;n<N;n++)
				{
					cores[n] = HBitCount(masks[n]);
					printf("Node[% 4d] : ranks = % 4d, cores = % 4d, host=%s\n", n, ranks[n], cores[n], host[n]);
					if(ranks[n] > cores[n])
					{ 
						AffinErr++;
					} else if((ranks[n]<1) || (cores[n]<1))
					{
						AffinErr++;
					}
								
				}
				if(hcErr)
				{
					printf("Warning: The node index is wrong on %d ranks!\n", hcErr);
				}
				if(AffinErr)
				{
					printf("Error: CPU affinity is wrong on %d nodes!\n", AffinErr);
				}
									
			}
		}
		else
			printf("We have a problem, something went wrong!\n");
	}

	if(RankInfo)
	{
		free(RankInfo);
		RankInfo=NULL;
	}

	if(bSleep) sleep(60);
	/* MPI programs end with MPI Finalize; this is a weak synchronization point */
	MPI_Finalize();
	return ret;
}


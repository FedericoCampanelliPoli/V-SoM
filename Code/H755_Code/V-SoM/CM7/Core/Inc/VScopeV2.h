#define VSCOPE_WIDTH 20
#define VSCOPE_SIZE 10
#define VSCOPE_SHM_BASE   0x38000000UL   // example shared RAM
#define VScope_common    (*(volatile VScope_common_t *)VSCOPE_SHM_BASE)

typedef struct{
				float Buffer[VSCOPE_WIDTH];
				int ch;
				float val;
				}VScope_common_t;

typedef struct{
	volatile float* buffer[VSCOPE_WIDTH];
	volatile float  buffer_send[VSCOPE_SIZE][VSCOPE_WIDTH];
	volatile int trig;
	volatile float dereference[VSCOPE_WIDTH];
	volatile int counter;
}VScope_t;

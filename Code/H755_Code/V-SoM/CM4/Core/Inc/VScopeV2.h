#define VSCOPE_WIDTH 20
#define VSCOPE_SIZE 10
#define VSCOPE_SHM_BASE   0x38000000UL   // example shared RAM
#define VScope_common    (*(volatile VScope_common_t *)VSCOPE_SHM_BASE)

typedef struct{
				float Buffer[20];
				int ch;
				float val;
				}VScope_common_t;

typedef struct{
	volatile float* buffer[VSCOPE_WIDTH];
	volatile int trig;
	volatile float dereference[VSCOPE_WIDTH];
}VScope_t;

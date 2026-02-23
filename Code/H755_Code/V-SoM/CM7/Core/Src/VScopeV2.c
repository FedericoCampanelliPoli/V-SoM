#include "main.h"

#include "cmsis_os.h"
#include "lwip.h"
#include "lwip/apps/lwiperf.h"
#include "lwip/udp.h"

#include "VScopeV2.h"

#include "FreeRTOS.h"	// notify method
#include "task.h"		// notify method

volatile TaskHandle_t vscopeTaskH = NULL;// notify method

#ifndef HSEM_ID_0
#define HSEM_ID_0 (0U) /* HW semaphore 0*/
#endif

void VScope_Stream(void);
void my_rx_cb(void *arg, struct udp_pcb *pcb, struct pbuf *p, const ip_addr_t *addr, u16_t port);
VScope_t VScope;




void my_rx_cb(void *arg, struct udp_pcb *pcb, struct pbuf *p,
		const ip_addr_t *addr, u16_t port)
{
	volatile uint8_t dbg_ch;
	volatile float   dbg_val;
	volatile uint8_t dbg_raw[8];
	volatile uint16_t dbg_len;

	if (!p) return;
	dbg_len = p->tot_len;
	if (dbg_len > 7) dbg_len = 7;

	pbuf_copy_partial(p, (void*)dbg_raw, dbg_len, 0);

	dbg_ch = dbg_raw[2];
	memcpy((void*)&dbg_val, (void*)&dbg_raw[3], 4);

	HAL_HSEM_FastTake(1);

	VScope_common.ch=dbg_ch;
	VScope_common.val=dbg_val;
	SCB_CleanDCache_by_Addr((uint32_t*)VSCOPE_SHM_BASE, 1000);
	__DSB();
	HAL_HSEM_Release(1, 0);

	*VScope.buffer[dbg_ch]=dbg_val;
	pbuf_free(p);
}

void VScope_Stream(void)
{
	ip_addr_t PC_IPADDR;
	IP_ADDR4(&PC_IPADDR, 10, 0, 0, 100);

	struct udp_pcb* my_udp = udp_new();
	udp_connect(my_udp, &PC_IPADDR, 5005);

	// ---- control RX pcb ----
	struct udp_pcb* my_udp_rx = udp_new();
	udp_bind(my_udp_rx, IP_ADDR_ANY, 5006);    // STM32 listens here
	udp_recv(my_udp_rx, my_rx_cb, NULL);

	struct pbuf* udp_buffer = NULL;

	vscopeTaskH = xTaskGetCurrentTaskHandle();// notify method

	const char data_align[2] = { 'V', 'S' };
	/* Infinite loop */
	for (;;) {
		/* !! PBUF_RAM is critical for correct operation !! */
		udp_buffer = pbuf_alloc(PBUF_TRANSPORT, 2 + sizeof(float)*VSCOPE_SIZE*VSCOPE_WIDTH, PBUF_RAM);
		if (udp_buffer != NULL)
		{
			uint8_t *dst = (uint8_t*)udp_buffer->payload;
			memcpy(dst, data_align, 2);
//			while(VScope.trig){} 	// wait method
//			VScope.trig=1;			// wait method
			ulTaskNotifyTake(pdTRUE, portMAX_DELAY); // notify method
			memcpy(dst + 2 , VScope.buffer_send, sizeof(float)*VSCOPE_WIDTH*VSCOPE_SIZE);
			udp_send(my_udp, udp_buffer);
			__DMB();
			pbuf_free(udp_buffer);

			static uint32_t k=0;
			if (++k >= 10000) { k=0; osDelay(1); }
		}
	}
}

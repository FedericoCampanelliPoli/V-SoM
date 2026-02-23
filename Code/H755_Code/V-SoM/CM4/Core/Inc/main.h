/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2022 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32h7xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */
#include "VScopeV2.h"
#include "ISR.h"
#ifdef GLOBAL_VARS
#define EXTERN
#else
#define EXTERN extern
#endif

EXTERN VScope_t VScope;
EXTERN uint32_t CR;
EXTERN uint32_t ADC1_RC;
EXTERN float ADC1_RC_r;
EXTERN float ADC1_JC_r[2];

#define HRTIM_SET_COMPARE(HRTIMx, duty) 	CR=duty*ARR/2.0f; 					\
				if (CR<ARR/2.0f - 0x31) 					\
				{ 						\
					HRTIM1->sTimerxRegs[HRTIMx].CMP1xR = ARR/2.0f-CR; 	\
					HRTIM1->sTimerxRegs[HRTIMx].CMP2xR = ARR/2.0f+CR; 	\
				} 						\
				else						 \
				{ 						\
					HRTIM1->sTimerxRegs[HRTIMx].CMP1xR = 0x31;		 \
					HRTIM1->sTimerxRegs[HRTIMx].CMP2xR = 0xFFFF; 		\
				}

/* USER CODE END EM */

void HAL_HRTIM_MspPostInit(HRTIM_HandleTypeDef *hhrtim);

void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);
void MX_GPIO_Init(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define ARR 40000
#define ISR1_Pin GPIO_PIN_11
#define ISR1_GPIO_Port GPIOB
#define ISR_Pin GPIO_PIN_0
#define ISR_GPIO_Port GPIOE

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */

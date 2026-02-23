/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 *
 * File: ISR.h
 *
 * Code generated for Simulink model 'ISR'.
 *
 * Model version                  : 1.3
 * Simulink Coder version         : 23.2 (R2023b) 01-Aug-2023
 * C/C++ source code generated on : Mon Jan 26 11:29:33 2026
 *
 * Target selection: ert.tlc
 * Embedded hardware selection: Intel->x86-64 (Windows64)
 * Code generation objectives: Unspecified
 * Validation result: Not run
 */

#ifndef RTW_HEADER_ISR_h_
#define RTW_HEADER_ISR_h_
#ifndef ISR_COMMON_INCLUDES_
#define ISR_COMMON_INCLUDES_
#include <stdbool.h>
#include <stdint.h>
#endif                                 /* ISR_COMMON_INCLUDES_ */

/* Macros for accessing real-time model data structure */
#ifndef rtmGetErrorStatus
#define rtmGetErrorStatus(rtm)         ((rtm)->errorStatus)
#endif

#ifndef rtmSetErrorStatus
#define rtmSetErrorStatus(rtm, val)    ((rtm)->errorStatus = (val))
#endif

/* Forward declaration for rtModel */
typedef struct tag_RTM_ISR_T RT_MODEL_ISR_T;

/* Block states (default storage) for system '<Root>' */
typedef struct {
  float Integrator_DSTATE;             /* '<S3>/Integrator' */
  bool Initial_FirstOutputTime;        /* '<S3>/Initial' */
} DW_ISR_T;

/* Real-time Model Data Structure */
struct tag_RTM_ISR_T {
  const char * volatile errorStatus;
};

/* Block states (default storage) */
extern DW_ISR_T ISR_DW;

/* Model entry point functions */
extern void ISR_initialize(void);
extern void ISR_step(void);
extern void ISR_terminate(void);

/* Exported data declaration */

/* Data with Exported storage */
extern float ISR_M_d;                  /* '<Root>/M' */
extern float ISR_frequency;            /* '<Root>/frequency' */
extern float ISR_sine_r[3];            /* '<Root>/sine_r' */

/* Real-time Model object */
extern RT_MODEL_ISR_T *const ISR_M;

/*-
 * The generated code includes comments that allow you to trace directly
 * back to the appropriate location in the model.  The basic format
 * is <system>/block_name, where system is the system number (uniquely
 * assigned by Simulink) and block_name is the name of the block.
 *
 * Note that this particular code originates from a subsystem build,
 * and has its own system numbers different from the parent model.
 * Refer to the system hierarchy for this subsystem below, and use the
 * MATLAB hilite_system command to trace the generated code back
 * to the parent model.  For example,
 *
 * hilite_system('Control/ISR')    - opens subsystem Control/ISR
 * hilite_system('Control/ISR/Kp') - opens and selects block Kp
 *
 * Here is the system hierarchy for this model
 *
 * '<Root>' : 'Control'
 * '<S1>'   : 'Control/ISR'
 * '<S2>'   : 'Control/ISR/Integrator with Wrapped State (Discrete or Continuous)'
 * '<S3>'   : 'Control/ISR/Integrator with Wrapped State (Discrete or Continuous)/Discrete'
 * '<S4>'   : 'Control/ISR/Integrator with Wrapped State (Discrete or Continuous)/Discrete/Compare To Constant'
 * '<S5>'   : 'Control/ISR/Integrator with Wrapped State (Discrete or Continuous)/Discrete/Compare To Constant1'
 * '<S6>'   : 'Control/ISR/Integrator with Wrapped State (Discrete or Continuous)/Discrete/Reinitialization'
 */
#endif                                 /* RTW_HEADER_ISR_h_ */

/*
 * File trailer for generated code.
 *
 * [EOF]
 */

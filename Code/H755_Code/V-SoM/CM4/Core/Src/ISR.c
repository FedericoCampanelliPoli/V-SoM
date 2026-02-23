/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 *
 * File: ISR.c
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

#include "ISR.h"
#include <math.h>

/* Exported data definition */

/* Data with Exported storage */
float ISR_M_d;                         /* '<Root>/M' */
float ISR_frequency;                   /* '<Root>/frequency' */
float ISR_sine_r[3];                   /* '<Root>/sine_r' */

/* Block states (default storage) */
DW_ISR_T ISR_DW;

/* Real-time model */
static RT_MODEL_ISR_T ISR_M_;
RT_MODEL_ISR_T *const ISR_M = &ISR_M_;

/* Model step function */
void ISR_step(void)
{
  float Initial;

  /* Outputs for Atomic SubSystem: '<Root>/ISR' */
  /* InitialCondition: '<S3>/Initial' */
  if (ISR_DW.Initial_FirstOutputTime) {
    ISR_DW.Initial_FirstOutputTime = false;

    /* InitialCondition: '<S3>/Initial' */
    Initial = 0.0F;
  } else {
    /* InitialCondition: '<S3>/Initial' incorporates:
     *  Bias: '<S6>/Bias'
     *  Gain: '<S6>/Gain'
     *  Gain: '<S6>/Gain1'
     *  Rounding: '<S6>/Rounding Function'
     *  Sum: '<S6>/Sum1'
     */
    Initial = ISR_DW.Integrator_DSTATE - floorf(0.159154937F *
      ISR_DW.Integrator_DSTATE) * 6.28318548F;
  }

  /* End of InitialCondition: '<S3>/Initial' */

  /* DiscreteIntegrator: '<S3>/Integrator' incorporates:
   *  Constant: '<S4>/Constant'
   *  Constant: '<S5>/Constant'
   *  Logic: '<S3>/Logical Operator'
   *  RelationalOperator: '<S4>/Compare'
   *  RelationalOperator: '<S5>/Compare'
   */
  if ((ISR_DW.Integrator_DSTATE < 0.0F) || (ISR_DW.Integrator_DSTATE >=
       6.28318548F)) {
    ISR_DW.Integrator_DSTATE = Initial;
  }

  /* Outport: '<Root>/sine_r' incorporates:
   *  Bias: '<S1>/Bias'
   *  Bias: '<S1>/Bias1'
   *  DiscreteIntegrator: '<S3>/Integrator'
   *  Inport: '<Root>/M'
   *  Product: '<S1>/Product'
   *  Trigonometry: '<S1>/Sin'
   */
  ISR_sine_r[0] = (ISR_M_d + 1.0F) * sinf(ISR_DW.Integrator_DSTATE);
  ISR_sine_r[1] = (ISR_M_d + 1.0F) * sinf(ISR_DW.Integrator_DSTATE + 2.09439516F);
  ISR_sine_r[2] = (ISR_M_d + 1.0F) * sinf(ISR_DW.Integrator_DSTATE - 2.09439516F);

  /* Update for DiscreteIntegrator: '<S3>/Integrator' incorporates:
   *  Gain: '<S1>/Gain'
   *  Inport: '<Root>/frequency'
   */
  ISR_DW.Integrator_DSTATE += 6.28318548F * ISR_frequency * 5.0E-5F;

  /* End of Outputs for SubSystem: '<Root>/ISR' */
}

/* Model initialize function */
void ISR_initialize(void)
{
  /* SystemInitialize for Atomic SubSystem: '<Root>/ISR' */
  /* Start for InitialCondition: '<S3>/Initial' */
  ISR_DW.Initial_FirstOutputTime = true;

  /* End of SystemInitialize for SubSystem: '<Root>/ISR' */
}

/* Model terminate function */
void ISR_terminate(void)
{
  /* (no terminate code required) */
}

/*
 * File trailer for generated code.
 *
 * [EOF]
 */

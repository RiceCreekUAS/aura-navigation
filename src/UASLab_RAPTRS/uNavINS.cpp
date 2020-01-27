/*
Updated to be a class, use Eigen, and compile as an Arduino library.
Added methods to get gyro and accel bias. Added initialization to
estimated angles rather than assuming IMU is level.

Copyright (c) 2016 - 2019 Regents of the University of Minnesota and Bolder Flight Systems Inc.
MIT License; See LICENSE.md for complete details
Author: Brian Taylor
*/

/*
Adapted from earlier version
Copyright 2011 Regents of the University of Minnesota. All rights reserved.
Original Author: Adhika Lie
*/

#include "uNavINS.h"

#include <iostream>
using std::cout;
using std::endl;

void uNavINS::Configure() {
  // Observation matrix (H)
  H_.setZero();
  H_.block(0,0,5,5) = I5;

  // Covariance of the Sensor Noise (associated with TimeUpdate())
  Rw_.setZero();
  Rw_.block(0,0,3,3) = (aNoiseSigma_mps2 * aNoiseSigma_mps2) * I3;
  Rw_.block(3,3,3,3) = (wNoiseSigma_rps * wNoiseSigma_rps) * I3;
  Rw_.block(6,6,3,3) = 2.0f * (aMarkovSigma_mps2 * aMarkovSigma_mps2) / aMarkovTau_s * I3;
  Rw_.block(9,9,3,3) = 2.0f * (wMarkovSigma_rps * wMarkovSigma_rps) / wMarkovTau_s * I3;

  // Covariance of the Observation Noise (associated with MeasUpdate())
  R_.setZero();
  R_.block(0,0,2,2) = (pNoiseSigma_NE_m * pNoiseSigma_NE_m) * I2;
  R_(2,2) = (pNoiseSigma_D_m * pNoiseSigma_D_m);
  R_.block(3,3,2,2) = (vNoiseSigma_NE_mps * vNoiseSigma_NE_mps) * I2;
  R_(5,5) = (vNoiseSigma_D_mps * vNoiseSigma_D_mps);

  // Initial Covariance Estimate (P)
  P_.setZero();
  P_.block(0,0,3,3) = (pErrSigma_Init_m * pErrSigma_Init_m) * I3;
  P_.block(3,3,3,3) = (vErrSigma_Init_mps * vErrSigma_Init_mps) * I3;
  P_.block(6,6,2,2) = (attErrSigma_Init_rad * attErrSigma_Init_rad) * I2;
  P_(8,8) = (hdgErrSigma_Init_rad * hdgErrSigma_Init_rad);
  P_.block(9,9,3,3) = (aBiasSigma_Init_mps2 * aBiasSigma_Init_mps2) * I3;
  P_.block(12,12,3,3) = (wBiasSigma_Init_rps * wBiasSigma_Init_rps) * I3;
}

void uNavINS::Initialize(Vector3f wMeas_rps, Vector3f aMeas_mps2, Vector3f magMeas, Vector3d pMeas_D_rrm, Vector3f vMeas_L_mps) {
  // Initialize sensor biases
  wBias_rps_ = wMeas_rps;
  aBias_mps2_.setZero();

  // initial attitude, roll and pitch
  euler_BL_rad_(1) = asinf(aMeas_mps2(0) / G);
  euler_BL_rad_(0) = asinf(-aMeas_mps2(1) / (G * cosf(euler_BL_rad_(1))));

  // magnetic heading correction due to roll and pitch angle
  float Bxc = magMeas(0) * cosf(euler_BL_rad_(1)) + (magMeas(1) * sinf(euler_BL_rad_(0)) + magMeas(2) * cosf(euler_BL_rad_(0))) * sinf(euler_BL_rad_(1));
  float Byc = magMeas(1) * cosf(euler_BL_rad_(0)) - magMeas(2) * sinf(euler_BL_rad_(0));

  // find initial heading
  if (-Byc > 0) {
    euler_BL_rad_(2) = M_PI / 2.0f - atanf(Bxc / -Byc);
  } else {
    euler_BL_rad_(2) = 3.0f * M_PI / 2.0f - atanf(Bxc / -Byc);
  }
  euler_BL_rad_(2) = WrapToPi(euler_BL_rad_(2));

  // Euler to quaternion
  quat_BL_ = Euler2Quat(euler_BL_rad_);

  // Initialize states with GPS Data
  pEst_D_rrm_ = pMeas_D_rrm;
  vEst_L_mps_ = vMeas_L_mps;

  // New Specific forces and Rotation Rate
  aEst_mps2_ = aMeas_mps2 - aBias_mps2_;
  wEst_rps_ = wMeas_rps - wBias_rps_;

  // set initialized flag
  initialized_ = true;
}

void uNavINS::Update(uint64_t t_us, unsigned long timeWeek, Vector3f wMeas_rps, Vector3f aMeas_mps2, Vector3f magMeas, Vector3d pMeas_D_rrm, Vector3f vMeas_L_mps) {
  // change in time
  dt_s_ = ((float)(t_us - tPrev_us_)) / 1e6;
  if (dt_s_ > 0.1) {dt_s_ = 0.1;} // Catch large dt
  tPrev_us_ = t_us;

  // Kalman Time Update (Prediction)
  TimeUpdate(wMeas_rps, aMeas_mps2);

  // Gps measurement update, if TOW increased
  if ((timeWeek - timeWeekPrev_) > 0) {
    timeWeekPrev_ = timeWeek;

    // Kalman Measurement Update
    MeasUpdate(pMeas_D_rrm, vMeas_L_mps);
  }

  // Euler angles from quaternion
  euler_BL_rad_ = Quat2Euler(quat_BL_);
  track_rad = atan2f(vEst_L_mps_(1), vEst_L_mps_(0));

  // Post-priori accel and rotation rate estimate
  aEst_mps2_ = aMeas_mps2 - aBias_mps2_;
  wEst_rps_ = wMeas_rps - wBias_rps_;
}

void uNavINS::TimeUpdate(Vector3f wMeas_rps, Vector3f aMeas_mps2) {
  // A-priori accel and rotation rate estimate
  aEst_mps2_ = aMeas_mps2 - aBias_mps2_;
  wEst_rps_ = wMeas_rps - wBias_rps_;

  // Compute DCM (Body to/from NED) Transformations from Quaternion
  Matrix3f T_L2B = Quat2DCM(quat_BL_);
  Matrix3f T_B2L = T_L2B.transpose();

  // Attitude Update
  Quaternionf dQuat_BL = Quaternionf(1.0, 0.5f*wEst_rps_(0)*dt_s_, 0.5f*wEst_rps_(1)*dt_s_, 0.5f*wEst_rps_(2)*dt_s_);
  quat_BL_ = (quat_BL_ * dQuat_BL).normalized();

  // Avoid quaternion flips sign
  if (quat_BL_.w() < 0) {
    quat_BL_ = Quaternionf(-quat_BL_.w(), -quat_BL_.x(), -quat_BL_.y(), -quat_BL_.z());
  }

  // Velocity Update
  Vector3f aGrav_mps2 = Vector3f(0.0, 0.0, G);
  vEst_L_mps_ += dt_s_ * (T_B2L * aEst_mps2_ + aGrav_mps2);

  // Position Update
  Vector3f pDot_D = L2D_Rate(vEst_L_mps_, pEst_D_rrm_);
  pEst_D_rrm_ += (dt_s_ * pDot_D).cast <double> ();

  // Assemble the Jacobian (state update matrix)
  Matrix<float, 15, 15> Fs;
  Fs.setZero();
  Fs.block(0,3,3,3) = I3; // ... pos2gs
  Fs(5,2) = -2.0f * G / EARTH_RADIUS; // ... gs2pos
  Fs.block(3,6,3,3) = -2.0f * T_B2L * Skew(aEst_mps2_); // ... gs2att
  Fs.block(3,9,3,3) = -T_B2L; // ... gs2acc
  Fs.block(6,6,3,3) = -Skew(wEst_rps_); // ... att2att
  Fs.block(6,12,3,3) = -0.5f * I3; // ... att2gyr
  Fs.block(9,9,3,3) = -1.0f / aMarkovTau_s * I3; // ... Accel Markov Bias
  Fs.block(12,12,3,3) = -1.0f / wMarkovTau_s * I3; // ... Rotation Rate (gyro) Markov Bias

  Matrix<float, 15, 15> PHI = I15 + Fs * dt_s_; // State Transition Matrix

  // Process Noise
  Matrix<float,15,12> Gs;
  Gs.setZero();
  Gs.block(3,0,3,3) = -T_B2L;
  Gs.block(6,3,3,3) = -0.5f * I3;
  Gs.block(9,6,6,6) = I6;

  // Process Noise Covariance
  Matrix<float, 15, 15> Q;
  Q.setZero();
  Q = PHI * dt_s_ * Gs * Rw_ * Gs.transpose();
  Q = 0.5f * (Q + Q.transpose());

  // Covariance Time Update
  P_ = PHI * P_ * PHI.transpose() + Q;
  P_ = 0.5f * (P_ + P_.transpose());
}

// Measurement Update
void uNavINS::MeasUpdate(Vector3d pMeas_D_rrm, Vector3f vMeas_L_mps) {
  // Position Error, converted to NED
  // Vector3d pErr_L_m = E2L(D2E(pMeas_D_rrm) - D2E(pEst_D_rrm_), pEst_D_rrm_);
  Matrix3d T_E2L = TransE2L(pEst_D_rrm_);
  Vector3d pErr_L_m = T_E2L * (D2E(pMeas_D_rrm) - D2E(pEst_D_rrm_));

  // Velocity Error
  Vector3f vErr_L_mps = vMeas_L_mps - vEst_L_mps_;

  // Create measurement Y, as difference between Measures and Outputs
  Matrix<float, 6, 1> y;
  y.setZero();
  y.segment(0, 3) = pErr_L_m.cast <float> ();
  y.segment(3, 3) = vErr_L_mps;

  // Innovation covariance
  Matrix<float,6,6> S;
  S.setZero();
  S = H_ * P_ * H_.transpose() + R_;

  // Kalman gain
  Matrix<float,15,6> K;
  K.setZero();
  K = P_ * H_.transpose() * S.inverse();

  // Covariance update, P = (I + K * H) * P * (I + K * H)' + K * R * K'
  P_ = (I15 - K * H_) * P_ * (I15 - K * H_).transpose() + K * R_ * K.transpose();

  // State update, x = K * y
  Matrix<float, 15, 1> x = K * y;

  // Pull apart x terms to update the Position, velocity, orientation, and sensor biases
  Vector3f pDeltaEst_D = x.segment(0, 3); // Position Deltas in LLA
  Vector3f vDeltaEst_L = x.segment(3, 3); // Velocity Deltas in NED
  Vector3f quatDelta = x.segment(6, 3); // Quaternion Delta
  Vector3f aBiasDelta = x.segment(9, 3); // Accel Bias Deltas
  Vector3f wBiasDelta = x.segment(12, 3); // w Bias Deltas

  // Position update
  double Rew, Rns;
  EarthRad(pEst_D_rrm_(0), &Rew, &Rns);

  pEst_D_rrm_(2) += -pDeltaEst_D(2);
  pEst_D_rrm_(0) += pDeltaEst_D(0) / (Rew + pEst_D_rrm_(2));
  pEst_D_rrm_(1) += pDeltaEst_D(1) / (Rns + pEst_D_rrm_(2)) / cos(pEst_D_rrm_(0));

  // Velocity update
  vEst_L_mps_ += vDeltaEst_L;

  // Attitude correction
  Quaternionf dQuat_BL = Quaternionf(1.0, quatDelta(0), quatDelta(1), quatDelta(2));
  quat_BL_ = (quat_BL_ * dQuat_BL).normalized();

  // Update biases from states
  aBias_mps2_ += aBiasDelta;
  wBias_rps_ += wBiasDelta;
}
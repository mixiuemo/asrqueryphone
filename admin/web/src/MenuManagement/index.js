import React from 'react';
import { Routes, Route } from 'react-router-dom';
import TeleManagement from '../componments/TeleManagement';
import PersonManagement from '../componments/PersonManagement';
import Auto114Result from '../componments/Auto114Result';
import Ai114Keywords from '../componments/Ai114Keywords';
import ServiceStatus from '../componments/ServiceStatus';
import ParaConfig from '../componments/ParaConfig';
import TrainConfig from '../componments/TrainConfig';
import WelConfig from '../componments/WelConfig';
import MqTest from '../componments/MqTest';
import RoleRoute from '../componments/RoleRoute';

const wrap = (el) => <RoleRoute>{el}</RoleRoute>;

const MenuManagement = () => {
  return (
    <Routes>
      <Route path="/tele" element={wrap(<TeleManagement />)} />
      <Route path="/logs" element={wrap(<Auto114Result />)} />
      <Route path="/users" element={wrap(<PersonManagement />)} />
      <Route path="/keywords" element={wrap(<Ai114Keywords />)} />
      <Route path="/serviceStatus" element={wrap(<ServiceStatus />)} />
      <Route path="/paraConfig" element={wrap(<ParaConfig />)} />
      <Route path="/trainConfig" element={wrap(<TrainConfig />)} />
      <Route path="/welConfig" element={wrap(<WelConfig />)} />
      <Route path="/mqtest" element={wrap(<MqTest />)} />
      <Route path="/" element={wrap(<TeleManagement />)} />
    </Routes>
  );
};

export default MenuManagement;

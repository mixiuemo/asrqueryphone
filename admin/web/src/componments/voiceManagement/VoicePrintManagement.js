import React, { useState } from 'react';
import { Tabs } from 'antd';
import VoicePrintList from './VoicePrintList'; // 原有声纹列表组件
import VoiceRegister from './VoiceRegister'; // 新增的声纹注册组件
import VoiceAsr from './VoiceAsr'; // 新增的声音转文字组件

const { TabPane } = Tabs;

const VoicePrintManagement = () => {
  const [activeKey, setActiveKey] = useState('list');

  return (
    <div style={{ padding: 24, backgroundColor: '#fff' }}>
      <Tabs activeKey={activeKey} onChange={setActiveKey} animated>
        <TabPane tab="声纹列表" key="list">
          <VoicePrintList />
        </TabPane>
        <TabPane tab="声纹注册" key="register">
          <VoiceRegister switchToVoiceList={() => setActiveKey('list')} />
        </TabPane>
        <TabPane tab="声音转文字" key="voiceasr">
          <VoiceAsr switchToVoiceList={() => setActiveKey('list')} />
        </TabPane>
      </Tabs>
    </div>
  );
};

export default VoicePrintManagement;
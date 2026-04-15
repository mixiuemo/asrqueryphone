import axios from 'axios';
import config from '../config';
const API_BASE_URL = process.env.NODE_ENV === 'development' ? config.baseUrl.dev : config.baseUrl.pro
// console.log('API_BASE_URL', API_BASE_URL)

// 用户相关 API
export const getUsers = async (searchQuery = '') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/users`, {
      params: { search: searchQuery }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching users:', error);
    throw error;
  }
};

export const createUser = async (data) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/users/add`, data);
    return response.data;
  } catch (error) {
    console.error('Error creating user:', error);
    throw error;
  }
};

export const updateUser = async (employee_id, data) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/users/${employee_id}`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating user:', error);
    throw error;
  }
};

export const deleteUser = async (employee_id) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/users/${employee_id}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting user:', error);
    throw error;
  }
};

// 角色（ai114_role）
export const getRoles = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/roles`);
    return response.data;
  } catch (error) {
    console.error('Error fetching roles:', error);
    throw error;
  }
};

export const createRole = async (data) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/roles/add`, data);
    return response.data;
  } catch (error) {
    console.error('Error creating role:', error);
    throw error;
  }
};

export const updateRole = async (roleCode, data) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/roles/${roleCode}`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating role:', error);
    throw error;
  }
};

export const deleteRole = async (roleCode) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/roles/${roleCode}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting role:', error);
    throw error;
  }
};

// 登录相关 API
export const getloginer = async (credentials) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/auth/login`, credentials);
    return response.data;
  } catch (error) {
    console.error('Error logging in:', error);
    throw error;
  }
};

// 通讯录相关 API

// 文件上传API（用于Excel导入）
export const importTeleFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file); // 'file' 必须与后端 upload.single('file') 匹配

  try {
    const response = await axios.post(`${API_BASE_URL}/tele/importtele`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        // 如果需要认证
        Authorization: `Bearer ${localStorage.getItem('token')}`
      },
      // 添加上传进度监听（可选）
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        console.log(`上传进度: ${percentCompleted}%`);
      }
    });
    return response.data;
  } catch (error) {
    console.error('文件上传失败:', {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });
    throw error;
  }
};

// 批量导入数据
export const importTeleData = async (data) => {
  console.log('哈哈哈data',data)
  try {
    const response = await axios.post(`${API_BASE_URL}/tele/import`, data);
    return response.data;
  } catch (error) {
    console.error('Error importing tele data:', error);
    throw error;
  }
};

export const getTeleData = async (searchQuery = '') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/tele`, {
      params: { search: searchQuery }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching tele data:', error);
    throw error;
  }
};

export const createTele = async (data) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/tele/add`, data);
    return response.data;
  } catch (error) {
    console.error('Error creating tele data:', error);
    throw error;
  }
};

export const updateTele = async (id, data) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/tele/${id}`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating tele data:', error);
    throw error;
  }
};

// 前端修改
export const deleteTele = async (number) => {  // 参数名改为number
  try {
    const response = await axios.delete(`${API_BASE_URL}/tele/${number}`);
    return response.data;
  } catch (error) {
    console.error('删除失败:', error.response?.data || error.message);
    throw error;
  }
};

// 前端修改
export const deleteVoicePrint = async (number) => {  // 参数名改为number
  try {
    const response = await axios.delete(`${API_BASE_URL}/voice/${number}`);
    return response.data;
  } catch (error) {
    console.error('删除失败:', error.response?.data || error.message);
    throw error;
  }
};

export const updatepinyintele = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/tele/update_pinyin`);
    return response.data;
  } catch (error) {
    console.error('Error creating tele data:', error);
    throw error;
  }
};

// 数据写入功能 - 生成查询模板JSON
export const writeDataToJson = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/tele/write_data_to_json`);
    return response.data;
  } catch (error) {
    console.error('Error writing data to JSON:', error);
    throw error;
  }
};

// 写入热词功能 - 将tele表数据写入txt文件
export const writeHotwords = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/tele/write_hotwords`);
    return response.data;
  } catch (error) {
    console.error('Error writing hotwords:', error);
    throw error;
  }
};

// 用户相关 API
// export const getUsers = async () => {
//   try {
//     const response = await axios.get(`${API_BASE_URL}/auto114result`);
//     return response.data;
//   } catch (error) {
//     console.error('Error fetching users:', error);
//     throw error;
//   }
// };

export const getLogs = async (startDate = '', endDate = '') => {
  try {
    const params = {};
    if (startDate) params.startDate = startDate;
    if (endDate) params.endDate = endDate;
    const response = await axios.get(`${API_BASE_URL}/auto114result`, {
      params
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching logs by time range:', error);
    throw error;
  }
};

export const createLogs = async (data) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/auto114result`, data);
    return response.data;
  } catch (error) {
    console.error('Error creating user:', error);
    throw error;
  }
};

export const updateLogs = async (id, data) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/auto114result/${id}`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating user:', error);
    throw error;
  }
};

export const deleteLogs = async (id) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/auto114result/${id}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting user:', error);
    throw error;
  }
};

// 热词表
export const createKeywords = async (data) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/keywords/add`, data, {
      // 禁止重定向
      maxRedirects: 0 
    });
    return response.data;
  } catch (error) {
    console.error('Error creating hotkeys:', error);
    throw error;
  }
};

export const getKeywords = async (searchQuery = '') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/keywords`, {
      params: { search: searchQuery }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching hotkeys:', error);
    throw error;
  }
};

export const updateKeywords = async (key, data) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/keywords/${key}`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating hotkeys:', error);
    throw error;
  }
};

export const deleteKeywords = async (key) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/keywords/${key}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting hotkeys:', error);
    throw error;
  }
};

//服务后台配置
// 获取服务状态列表
export const getServiceStatuses = async (searchQuery = '') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/serviceStatusRoutes`, {
      params: { search: searchQuery }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching service statuses:', error);
    throw error;
  }
};

export const createServiceStatus = async (data) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/serviceStatusRoutes`, data);
    return response.data;
  } catch (error) {
    console.error('Error creating service status:', error);
    throw error;
  }
};


export const updateServiceStatus = async (id, data) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/serviceStatusRoutes/${id}`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating service status:', error);
    throw error;
  }
};
export const deleteServiceStatus = async (id) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/serviceStatusRoutes/${id}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting service status:', error);
    throw error;
  }
};

// 检查所有服务健康状态
export const checkAllServicesHealth = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/serviceStatusRoutes/check_all_services_health`);
    return response.data;
  } catch (error) {
    console.error('Error checking all services health:', error);
    throw error;
  }
};

// 声纹embedding相关 API
export const getEmbedding = async (searchQuery = '') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/embedding`, {
      params: { search: searchQuery }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching embedding:', error);
    throw error;
  }
};

export const createEmbedding = async (data) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/embedding/add`, data);
    return response.data;
  } catch (error) {
    console.error('Error creating embedding:', error);
    throw error;
  }
};

export const updateEmbedding = async (id, data) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/embedding/${id}`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating embedding:', error);
    throw error;
  }
};

export const deleteEmbedding = async (id) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/embedding/${id}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting embedding:', error);
    throw error;
  }
};

// 声纹识别接口
export const identifyVoice = async (currentVector) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/embedding/identify`,
      { currentVector }  // 直接传递对象作为请求体
    );
    return response.data;
  } catch (error) {
    console.error("Error identifying voice:", error);
    throw error;
  }
};

// 语音转文字接口
export const generateAudioToTxt = async (data) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/embedding/generateAudioToTxt`,
      { data }  // 直接传递对象作为请求体
    );
    return response.data;
  } catch (error) {
    console.error("Error generating audio to text:", error);
    throw error;
  }
};

// 查询AI大模型接口
export const queryAIModal = async (query_text) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/embedding/queryAIModal`,
      { query_text }  // 直接传递对象作为请求体
    );
    return response.data;
  } catch (error) {
    console.error("Error querying AI modal:", error);
    throw error;
  }
};

// 合成音频接口
export const generateAudio = async (datas) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/embedding/generateAudio`,
      { datas }  // 直接传递对象作为请求体
    );
    return response.data;
  } catch (error) {
    console.error("Error generating audio:", error);
    throw error;
  }
};

//服务后台配置
export const getParaConfig = async (searchQuery = '') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/paraConfig`, {
      params: { search: searchQuery }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching paraConfig:', error);
    throw error;
  }
};

export const createParaConfig = async (data) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/paraConfig/add`, data);
    return response.data;
  } catch (error) {
    console.error('Error creating paraConfig:', error);
    throw error;
  }
};

export const updateParaConfig = async (id, data) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/paraConfig/${id}`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating paraConfig:', error);
    throw error;
  }
};
export const deleteParaConfig = async (id) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/paraConfig/${id}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting paraConfig:', error);
    throw error;
  }
};

//训练配置
export const getAllTrainConfigs = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/trainConfig`);
    return response.data;
  } catch (error) {
    console.error('Error fetching all train configs:', error);
    throw error;
  }
};

export const getTrainConfigById = async (id) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/trainConfig/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching train config with id ${id}:`, error);
    throw error;
  }
};

export const getTrainConfig = async (searchQuery = '') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/trainConfig`, {
      params: { search: searchQuery }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching trainConfig:', error);
    throw error;
  }
};

export const createTrainConfig = async (data) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/trainConfig/add`, data);
    return response.data;
  } catch (error) {
    console.error('Error creating train config:', error);
    throw error;
  }
};

export const updateTrainConfig = async (id, data) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/trainConfig/${id}`, data);
    return response.data;
  } catch (error) {
    console.error(`Error updating train config with id ${id}:`, error);
    throw error;
  }
};

export const deleteTrainConfig = async (id) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/trainConfig/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error deleting train config with id ${id}:`, error);
    throw error;
  }
};

// 欢迎配置
export const getAllWelConfigs = async (searchQuery = '') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/welConfig`, {
      params: { search: searchQuery }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching all welcome configs:', error);
    throw error;
  }
};

export const getWelConfigById = async (id) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/welConfig/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching welcome config with id ${id}:`, error);
    throw error;
  }
};

export const getWelConfig = async (searchQuery = '') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/welConfig`, {
      params: { search: searchQuery }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching welcome config:', error);
    throw error;
  }
};

export const createWelConfig = async (data) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/welConfig/add`, data);
    return response.data;
  } catch (error) {
    console.error('Error creating welcome config:', error);
    throw error;
  }
};

export const updateWelConfig = async (id, data) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/welConfig/${id}`, data);
    return response.data;
  } catch (error) {
    console.error(`Error updating welcome config with id ${id}:`, error);
    throw error;
  }
};

export const deleteWelConfig = async (id) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/welConfig/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error deleting welcome config with id ${id}:`, error);
    throw error;
  }
};

// 声纹识别结果
export const getAllVoiceprintResults = async (searchQuery = '') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/voicePrint`,{
      params: { search: searchQuery }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching all voiceprint results:', error);
    throw error;
  }
};

export const getVoiceprintResultById = async (id) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/voicePrint/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching voiceprint result with id ${id}:`, error);
    throw error;
  }
};

export const getVoiceprintResult = async (searchQuery = '') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/voicePrint`, {
      params: { search: searchQuery }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching voiceprint result:', error);
    throw error;
  }
};
export const getAudioFiles = async (path) => {

  try {
    const response = await axios.post(`${API_BASE_URL}/embedding/audio-files`, {
      path: path 
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching audio files:', error);
    throw error;
  }
};
export const clipAudioFile = async (filePath, startTime, endTime) => { 
  try {
    const response = await axios.post(`${API_BASE_URL}/embedding/clip`, {
      filePath: filePath,
      startTime: startTime,
      endTime: endTime
    });
    return response.data;
  } catch (error) {
    console.error('Error clipping audio file:', error);
    throw error;
  }
};

export const updateUserPermissionInJson = async (userNumber, queryPermission) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/tele/update_user_permission_in_json`, {
      userNumber,
      queryPermission
    });
    return response.data;
  } catch (error) {
    console.error('Error updating user permission in JSON:', error);
    throw error;
  }
};

export const clearAllTeleData = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/tele/clear_all`);
    return response.data;
  } catch (error) {
    console.error('清空通讯录失败:', error.response?.data || error.message);
    throw error;
  }
};

// MQ 交互逻辑测试
export const sendMqTest = async (text, clientId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/mqtest/send`, {
      text,
      clientId
    });
    return response.data;
  } catch (error) {
    console.error('Error sending MQ test:', error);
    throw error;
  }
};

export const sendMqTestRecord = async (audio_b64, clientId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/mqtest/send_record`, {
      audio_b64,
      clientId
    });
    return response.data;
  } catch (error) {
    console.error('Error sending MQ record:', error);
    throw error;
  }
};

export const sendMqTestTts = async (text, clientId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/mqtest/send_tts`, {
      text,
      clientId
    });
    return response.data;
  } catch (error) {
    console.error('Error sending MQ tts:', error);
    throw error;
  }
};

// 读取热词文件
export const readHotwords = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/tele/read_hotwords`);
    return response.data;
  } catch (error) {
    console.error('Error reading hotwords:', error);
    throw error;
  }
};

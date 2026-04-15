import React, { useState, useEffect } from 'react';
import { getLogs, getTeleData } from '../services/api';

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [teleData, setTeleData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // 并行获取用户和 tele 数据
        const [usersResponse, teleResponse] = await Promise.all([
          getLogs(),
          getTeleData()
        ]);
        
        setUsers(usersResponse);
        setTeleData(teleResponse);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h2>Users Data</h2>
      <ul>
        {users.map(user => (
          <li key={user.id}>
            {user.name} - {user.email}
          </li>
        ))}
      </ul>

      <h2>Tele Data</h2>
      <ul>
        {teleData.map(item => (
          <li key={item.id}>
            {/* 根据你的实际数据结构调整显示 */}
            {JSON.stringify(item)}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default UserManagement;
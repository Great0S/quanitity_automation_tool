import React, { useState } from 'react';
import styled from 'styled-components';
import { toast } from 'react-toastify';

const SettingsContainer = styled.div`
  padding: 20px;
`;

const SettingsCard = styled.div`
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 20px;
`;

const SettingsTitle = styled.h3`
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
`;

const FormGroup = styled.div`
  margin-bottom: 20px;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
`;

const Input = styled.input`
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  
  &:focus {
    outline: none;
    border-color: #0f3460;
    box-shadow: 0 0 0 2px rgba(15, 52, 96, 0.2);
  }
`;

const Select = styled.select`
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  
  &:focus {
    outline: none;
    border-color: #0f3460;
    box-shadow: 0 0 0 2px rgba(15, 52, 96, 0.2);
  }
`;

const Button = styled.button`
  background-color: #0f3460;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 12px 20px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.3s;
  
  &:hover {
    background-color: #16213e;
  }
`;

const Settings: React.FC = () => {
  const [settings, setSettings] = useState({
    refreshInterval: 30,
    defaultPageSize: 20,
    theme: 'light',
    notifications: true,
  });
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    
    setSettings({
      ...settings,
      [name]: type === 'checkbox' 
        ? (e.target as HTMLInputElement).checked 
        : type === 'number' 
          ? Number(value) 
          : value
    });
  };
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Save settings to localStorage
    localStorage.setItem('appSettings', JSON.stringify(settings));
    
    toast.success('Settings saved successfully!');
  };
  
  return (
    <SettingsContainer>
      <h2>Settings</h2>
      <p>Configure application settings</p>
      
      <SettingsCard>
        <SettingsTitle>General Settings</SettingsTitle>
        
        <form onSubmit={handleSubmit}>
          <FormGroup>
            <Label htmlFor="refreshInterval">Data Refresh Interval (seconds)</Label>
            <Input
              type="number"
              id="refreshInterval"
              name="refreshInterval"
              value={settings.refreshInterval}
              onChange={handleChange}
              min={5}
              max={300}
            />
          </FormGroup>
          
          <FormGroup>
            <Label htmlFor="defaultPageSize">Default Page Size</Label>
            <Select
              id="defaultPageSize"
              name="defaultPageSize"
              value={settings.defaultPageSize}
              onChange={handleChange}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </Select>
          </FormGroup>
          
          <FormGroup>
            <Label htmlFor="theme">Theme</Label>
            <Select
              id="theme"
              name="theme"
              value={settings.theme}
              onChange={handleChange}
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </Select>
          </FormGroup>
          
          <FormGroup>
            <Label>
              <Input
                type="checkbox"
                name="notifications"
                checked={settings.notifications}
                onChange={handleChange}
              />
              {' '}Enable Notifications
            </Label>
          </FormGroup>
          
          <Button type="submit">Save Settings</Button>
        </form>
      </SettingsCard>
    </SettingsContainer>
  );
};

export default Settings;
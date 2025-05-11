import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { toast } from 'react-toastify';
import api from '../services/authService';
import { TASK_REFRESH_INTERVAL } from '../config';

const SyncContainer = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
`;

const Card = styled.div`
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 20px;
`;

const FormCard = styled(Card)`
  grid-column: 1;
`;

const HistoryCard = styled(Card)`
  grid-column: 2;
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
`;

const FormGroup = styled.div`
  margin-bottom: 20px;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
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

const CheckboxGroup = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
`;

const CheckboxLabel = styled.label`
  display: flex;
  align-items: center;
  cursor: pointer;
  
  input {
    margin-right: 5px;
  }
`;

const Button = styled.button`
  background-color: #0f3460;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 12px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.3s;
  
  &:hover {
    background-color: #16213e;
  }
  
  &:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
  }
`;

const HistoryTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  
  th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #eee;
  }
  
  th {
    background-color: #f9f9f9;
    font-weight: 500;
  }
  
  tr:hover {
    background-color: #f5f5f5;
  }
`;

const StatusBadge = styled.span<{ status: string }>`
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
  
  ${props => {
    switch (props.status.toLowerCase()) {
      case 'completed':
        return 'background-color: #e8f5e9; color: #2e7d32;';
      case 'failed':
        return 'background-color: #ffebee; color: #c62828;';
      case 'running':
        return 'background-color: #e3f2fd; color: #1565c0;';
      default:
        return 'background-color: #f5f5f5; color: #616161;';
    }
  }}
`;

const ProgressBar = styled.div`
  height: 8px;
  background-color: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
  margin-top: 20px;
`;

const ProgressFill = styled.div<{ progress: number }>`
  height: 100%;
  width: ${props => props.progress}%;
  background-color: #0f3460;
  transition: width 0.3s ease;
`;

const ProgressText = styled.div`
  text-align: center;
  font-size: 0.9rem;
  color: #666;
  margin-top: 5px;
`;

const ViewButton = styled.button`
  background-color: transparent;
  color: #0f3460;
  border: none;
  padding: 0;
  font-size: 0.9rem;
  cursor: pointer;
  text-decoration: underline;
  
  &:hover {
    color: #16213e;
  }
`;

const SyncDetailsModal = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
`;

const ModalContent = styled.div`
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  padding: 20px;
  width: 80%;
  max-width: 800px;
  max-height: 80vh;
  overflow-y: auto;
`;

const ModalHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
`;

const ModalTitle = styled.h3`
  margin: 0;
`;

const CloseButton = styled.button`
  background-color: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
  
  &:hover {
    color: #333;
  }
`;

const TabsContainer = styled.div`
  margin-bottom: 20px;
`;

const TabButton = styled.button<{ active: boolean }>`
  background-color: ${props => props.active ? '#0f3460' : 'transparent'};
  color: ${props => props.active ? 'white' : '#333'};
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 8px 16px;
  margin-right: 10px;
  cursor: pointer;
  
  &:hover {
    background-color: ${props => props.active ? '#0f3460' : '#f5f5f5'};
  }
`;

const Sync: React.FC = () => {
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [sourcePlatform, setSourcePlatform] = useState<string>('');
  const [targetPlatforms, setTargetPlatforms] = useState<string[]>([]);
  const [syncFields, setSyncFields] = useState<string[]>(['price', 'quantity', 'status']);
  const [syncHistory, setSyncHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [currentSyncTask, setCurrentSyncTask] = useState<string | null>(null);
  const [syncProgress, setSyncProgress] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [syncDetails, setSyncDetails] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('success');
  
  // Fetch platforms and sync history
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Fetch platforms
        const platformsResponse = await api.get('/platforms');
        const availablePlatforms = platformsResponse.data.platforms || [];
        setPlatforms(availablePlatforms);
        
        if (availablePlatforms.length > 0) {
          setSourcePlatform(availablePlatforms[0]);
        }
        
        // Fetch sync history
        const historyResponse = await api.get('/sync/history');
        setSyncHistory(historyResponse.data);
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching data:', err);
        toast.error('Failed to load data');
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  // Check sync task status
  useEffect(() => {
    if (!currentSyncTask) return;
    
    const checkTaskStatus = async () => {
      try {
        const response = await api.get(`/tasks/${currentSyncTask}`);
        const task = response.data;
        
        if (task.status === 'completed') {
          toast.success('Sync completed successfully');
          setCurrentSyncTask(null);
          setSyncing(false);
          setSyncProgress(100);
          
          // Refresh sync history
          const historyResponse = await api.get('/sync/history');
          setSyncHistory(historyResponse.data);
        } else if (task.status === 'failed') {
          toast.error(`Sync failed: ${task.error}`);
          setCurrentSyncTask(null);
          setSyncing(false);
        } else {
          // Still running
          setSyncProgress(task.progress ? task.progress * 100 : 0);
        }
      } catch (err) {
        console.error('Error checking task status:', err);
      }
    };
    
    const interval = setInterval(checkTaskStatus, TASK_REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [currentSyncTask]);
  
  // Handle platform selection
  const handleTargetPlatformChange = (platform: string) => {
    if (targetPlatforms.includes(platform)) {
      setTargetPlatforms(targetPlatforms.filter(p => p !== platform));
    } else {
      setTargetPlatforms([...targetPlatforms, platform]);
    }
  };
  
  // Handle field selection
  const handleFieldChange = (field: string) => {
    if (syncFields.includes(field)) {
      setSyncFields(syncFields.filter(f => f !== field));
    } else {
      setSyncFields([...syncFields, field]);
    }
  };
  
  // Start sync
  const handleStartSync = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!sourcePlatform) {
      toast.error('Please select a source platform');
      return;
    }
    
    if (targetPlatforms.length === 0) {
      toast.error('Please select at least one target platform');
      return;
    }
    
    if (syncFields.length === 0) {
      toast.error('Please select at least one field to sync');
      return;
    }
    
    try {
      setSyncing(true);
      setSyncProgress(0);
      
      const response = await api.post('/sync', {
        source_platform: sourcePlatform,
        target_platforms: targetPlatforms,
        fields: syncFields
      });
      
      setCurrentSyncTask(response.data.task_id);
      toast.info('Sync started');
    } catch (err) {
      console.error('Error starting sync:', err);
      toast.error('Failed to start sync');
      setSyncing(false);
    }
  };
  
  // View sync details
  const viewSyncDetails = async (syncId: number) => {
    try {
      const response = await api.get(`/sync/details/${syncId}`);
      setSyncDetails(response.data);
      setShowModal(true);
    } catch (err) {
      console.error('Error fetching sync details:', err);
      toast.error('Failed to load sync details');
    }
  };
  
  return (
    <div>
      <h2>Sync Products</h2>
      
      <SyncContainer>
        <FormCard>
          <h3>Start New Sync</h3>
          <Form onSubmit={handleStartSync}>
            <FormGroup>
              <Label htmlFor="sourcePlatform">Source Platform</Label>
              <Select
                id="sourcePlatform"
                value={sourcePlatform}
                onChange={e => setSourcePlatform(e.target.value)}
                disabled={syncing || loading}
              >
                <option value="">Select Source Platform</option>
                {platforms.map(platform => (
                  <option key={platform} value={platform}>
                    {platform}
                  </option>
                ))}
              </Select>
            </FormGroup>
            
            <FormGroup>
              <Label>Target Platforms</Label>
              <CheckboxGroup>
                {platforms
                  .filter(platform => platform !== sourcePlatform)
                  .map(platform => (
                    <CheckboxLabel key={platform}>
                      <input
                        type="checkbox"
                        checked={targetPlatforms.includes(platform)}
                        onChange={() => handleTargetPlatformChange(platform)}
                        disabled={syncing || loading}
                      />
                      {platform}
                    </CheckboxLabel>
                  ))}
              </CheckboxGroup>
            </FormGroup>
            
            <FormGroup>
              <Label>Fields to Sync</Label>
              <CheckboxGroup>
                <CheckboxLabel>
                  <input
                    type="checkbox"
                    checked={syncFields.includes('price')}
                    onChange={() => handleFieldChange('price')}
                    disabled={syncing || loading}
                  />
                  Price
                </CheckboxLabel>
                <CheckboxLabel>
                  <input
                    type="checkbox"
                    checked={syncFields.includes('quantity')}
                    onChange={() => handleFieldChange('quantity')}
                    disabled={syncing || loading}
                  />
                  Quantity
                </CheckboxLabel>
                <CheckboxLabel>
                  <input
                    type="checkbox"
                    checked={syncFields.includes('status')}
                    onChange={() => handleFieldChange('status')}
                    disabled={syncing || loading}
                  />
                  Status
                </CheckboxLabel>
              </CheckboxGroup>
            </FormGroup>
            
            <Button type="submit" disabled={syncing || loading}>
              {syncing ? 'Syncing...' : 'Start Sync'}
            </Button>
            
            {syncing && (
              <>
                <ProgressBar>
                  <ProgressFill progress={syncProgress} />
                </ProgressBar>
                <ProgressText>{syncProgress.toFixed(0)}% Complete</ProgressText>
              </>
            )}
          </Form>
        </FormCard>
        
        <HistoryCard>
          <h3>Sync History</h3>
          {syncHistory.length > 0 ? (
            <HistoryTable>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Source</th>
                  <th>Products</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {syncHistory.map(sync => (
                  <tr key={sync.id}>
                    <td>{new Date(sync.started_at).toLocaleString()}</td>
                    <td>{sync.source_platform_name || 'Unknown'}</td>
                    <td>{sync.success_count} / {sync.products_count}</td>
                    <td>
                      <StatusBadge status={sync.status}>
                        {sync.status}
                      </StatusBadge>
                    </td>
                    <td>
                      <ViewButton onClick={() => viewSyncDetails(sync.id)}>
                        View Details
                      </ViewButton>
                    </td>
                  </tr>
                ))}
              </tbody>
            </HistoryTable>
          ) : (
            <p>No sync history available</p>
          )}
        </HistoryCard>
      </SyncContainer>
      
      {showModal && syncDetails && (
        <SyncDetailsModal>
          <ModalContent>
            <ModalHeader>
              <ModalTitle>Sync Details</ModalTitle>
              <CloseButton onClick={() => setShowModal(false)}>&times;</CloseButton>
            </ModalHeader>
            
            <div>
              <p><strong>Source:</strong> {syncDetails.sync.source_platform_name || 'Unknown'}</p>
              <p><strong>Target:</strong> {syncDetails.sync.target_platform_name || 'Multiple'}</p>
              <p><strong>Started:</strong> {new Date(syncDetails.sync.started_at).toLocaleString()}</p>
              <p><strong>Completed:</strong> {syncDetails.sync.completed_at ? new Date(syncDetails.sync.completed_at).toLocaleString() : 'Not completed'}</p>
              <p><strong>Status:</strong> <StatusBadge status={syncDetails.sync.status}>{syncDetails.sync.status}</StatusBadge></p>
              <p><strong>Products:</strong> {syncDetails.sync.success_count} successful / {syncDetails.sync.products_count} total</p>
              
              <TabsContainer>
                <TabButton 
                  active={activeTab === 'success'} 
                  onClick={() => setActiveTab('success')}
                >
                  Success ({syncDetails.results.success.length})
                </TabButton>
                <TabButton 
                  active={activeTab === 'error'} 
                  onClick={() => setActiveTab('error')}
                >
                  Errors ({syncDetails.results.error.length})
                </TabButton>
                <TabButton 
                  active={activeTab === 'skipped'} 
                  onClick={() => setActiveTab('skipped')}
                >
                  Skipped ({syncDetails.results.skipped.length})
                </TabButton>
              </TabsContainer>
              
              {activeTab === 'success' && (
                <HistoryTable>
                  <thead>
                    <tr>
                      <th>SKU</th>
                      <th>Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {syncDetails.results.success.map((item: any, index: number) => (
                      <tr key={index}>
                        <td>{item.sku}</td>
                        <td>{item.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </HistoryTable>
              )}
              
              {activeTab === 'error' && (
                <HistoryTable>
                  <thead>
                    <tr>
                      <th>SKU</th>
                      <th>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {syncDetails.results.error.map((item: any, index: number) => (
                      <tr key={index}>
                        <td>{item.sku}</td>
                        <td>{item.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </HistoryTable>
              )}
              
              {activeTab === 'skipped' && (
                <HistoryTable>
                  <thead>
                    <tr>
                      <th>SKU</th>
                      <th>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {syncDetails.results.skipped.map((item: any, index: number) => (
                      <tr key={index}>
                        <td>{item.sku}</td>
                        <td>{item.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </HistoryTable>
              )}
            </div>
          </ModalContent>
        </SyncDetailsModal>
      )}
    </div>
  );
};

export default Sync;
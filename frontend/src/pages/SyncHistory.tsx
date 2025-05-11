import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { toast } from 'react-toastify';
import api from '../services/authService';

const SyncHistoryContainer = styled.div`
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 20px;
`;

const Header = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
`;

const Title = styled.h2`
  margin: 0;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
  
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

const StatusBadge = styled.span<{ $status: string }>`
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
  
  ${props => {
    switch (props.$status.toLowerCase()) {
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

const Button = styled.button`
  background-color: #0f3460;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  cursor: pointer;
  transition: background-color 0.3s;
  
  &:hover {
    background-color: #16213e;
  }
`;

const Modal = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
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
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
  
  &:hover {
    color: #333;
  }
`;

const DetailItem = styled.div`
  margin-bottom: 15px;
`;

const DetailLabel = styled.div`
  font-weight: 500;
  margin-bottom: 5px;
`;

const DetailValue = styled.div`
  color: #666;
`;

const ResultsTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  
  th, td {
    padding: 8px;
    text-align: left;
    border-bottom: 1px solid #eee;
    font-size: 0.9rem;
  }
  
  th {
    background-color: #f9f9f9;
    font-weight: 500;
  }
`;

const LoadingMessage = styled.div`
  text-align: center;
  padding: 20px;
  color: #666;
`;

const EmptyMessage = styled.div`
  text-align: center;
  padding: 20px;
  color: #666;
`;

interface SyncRecord {
  id: number;
  source_platform: string;
  target_platforms: string[];
  status: string;
  success_count: number;
  error_count: number;
  created_at: string;
  completed_at?: string;
  fields: string[];
}

interface SyncResult {
  sku: string;
  status: string;
  platforms: {
    platform: string;
    status: string;
    message: string;
  }[];
}

interface SyncDetails {
  sync: SyncRecord;
  results: SyncResult[];
}

const SyncHistory: React.FC = () => {
  const navigate = useNavigate();
  
  const [syncHistory, setSyncHistory] = useState<SyncRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedSync, setSelectedSync] = useState<SyncDetails | null>(null);
  const [showModal, setShowModal] = useState<boolean>(false);
  
  // Load sync history on mount
  useEffect(() => {
    const fetchSyncHistory = async () => {
      try {
        setLoading(true);
        const response = await api.get('/sync/history');
        setSyncHistory(response.data);
      } catch (err) {
        console.error('Error fetching sync history:', err);
        toast.error('Failed to load sync history');
      } finally {
        setLoading(false);
      }
    };
    
    fetchSyncHistory();
  }, []);
  
  // Format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };
  
  // Calculate duration
  const calculateDuration = (startDate: string, endDate?: string) => {
    if (!endDate) return 'In progress';
    
    const start = new Date(startDate).getTime();
    const end = new Date(endDate).getTime();
    const durationMs = end - start;
    
    // Format duration
    const seconds = Math.floor(durationMs / 1000);
    if (seconds < 60) return `${seconds} seconds`;
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (minutes < 60) return `${minutes} min ${remainingSeconds} sec`;
    
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours} hr ${remainingMinutes} min`;
  };
  
  // View sync details
  const viewSyncDetails = async (syncId: number) => {
    try {
      const response = await api.get(`/sync/history/${syncId}`);
      setSelectedSync(response.data);
      setShowModal(true);
    } catch (err) {
      console.error('Error fetching sync details:', err);
      toast.error('Failed to load sync details');
    }
  };
  
  // Close modal
  const closeModal = () => {
    setShowModal(false);
    setSelectedSync(null);
  };
  
  if (loading) {
    return <LoadingMessage>Loading sync history...</LoadingMessage>;
  }
  
  return (
    <SyncHistoryContainer>
      <Header>
        <Title>Sync History</Title>
        <Button onClick={() => navigate('/sync')}>New Sync</Button>
      </Header>
      
      {syncHistory.length === 0 ? (
        <EmptyMessage>No sync history found</EmptyMessage>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Source</th>
              <th>Targets</th>
              <th>Status</th>
              <th>Success</th>
              <th>Errors</th>
              <th>Started</th>
              <th>Duration</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {syncHistory.map(sync => (
              <tr key={sync.id}>
                <td>{sync.id}</td>
                <td>{sync.source_platform}</td>
                <td>{sync.target_platforms.join(', ')}</td>
                <td>
                  <StatusBadge $status={sync.status}>
                    {sync.status}
                  </StatusBadge>
                </td>
                <td>{sync.success_count}</td>
                <td>{sync.error_count}</td>
                <td>{formatDate(sync.created_at)}</td>
                <td>{calculateDuration(sync.created_at, sync.completed_at)}</td>
                <td>
                  <Button onClick={() => viewSyncDetails(sync.id)}>
                    Details
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      
      {showModal && selectedSync && (
        <Modal>
          <ModalContent>
            <ModalHeader>
              <ModalTitle>Sync Details #{selectedSync.sync.id}</ModalTitle>
              <CloseButton onClick={closeModal}>&times;</CloseButton>
            </ModalHeader>
            
            <DetailItem>
              <DetailLabel>Source Platform</DetailLabel>
              <DetailValue>{selectedSync.sync.source_platform}</DetailValue>
            </DetailItem>
            
            <DetailItem>
              <DetailLabel>Target Platforms</DetailLabel>
              <DetailValue>{selectedSync.sync.target_platforms.join(', ')}</DetailValue>
            </DetailItem>
            
            <DetailItem>
              <DetailLabel>Status</DetailLabel>
              <DetailValue>
                <StatusBadge $status={selectedSync.sync.status}>
                  {selectedSync.sync.status}
                </StatusBadge>
              </DetailValue>
            </DetailItem>
            
            <DetailItem>
              <DetailLabel>Fields Synced</DetailLabel>
              <DetailValue>{selectedSync.sync.fields.join(', ')}</DetailValue>
            </DetailItem>
            
            <DetailItem>
              <DetailLabel>Started</DetailLabel>
              <DetailValue>{formatDate(selectedSync.sync.created_at)}</DetailValue>
            </DetailItem>
            
            {selectedSync.sync.completed_at && (
              <DetailItem>
                <DetailLabel>Completed</DetailLabel>
                <DetailValue>{formatDate(selectedSync.sync.completed_at)}</DetailValue>
              </DetailItem>
            )}
            
            <DetailItem>
              <DetailLabel>Duration</DetailLabel>
              <DetailValue>
                {calculateDuration(selectedSync.sync.created_at, selectedSync.sync.completed_at)}
              </DetailValue>
            </DetailItem>
            
            <DetailItem>
              <DetailLabel>Results</DetailLabel>
              <DetailValue>
                {selectedSync.sync.success_count} successful, {selectedSync.sync.error_count} failed
              </DetailValue>
            </DetailItem>
            
            <DetailItem>
              <DetailLabel>Product Results</DetailLabel>
              {selectedSync.results.length === 0 ? (
                <DetailValue>No detailed results available</DetailValue>
              ) : (
                <ResultsTable>
                  <thead>
                    <tr>
                      <th>SKU</th>
                      <th>Status</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedSync.results.map((result, index) => (
                      <tr key={`${result.sku}-${index}`}>
                        <td>{result.sku}</td>
                        <td>
                          <StatusBadge $status={result.status}>
                            {result.status}
                          </StatusBadge>
                        </td>
                        <td>
                          {result.platforms.map((platform, i) => (
                            <div key={`${result.sku}-${platform.platform}-${i}`}>
                              {platform.platform}: {platform.status} - {platform.message}
                            </div>
                          ))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </ResultsTable>
              )}
            </DetailItem>
          </ModalContent>
        </Modal>
      )}
    </SyncHistoryContainer>
  );
};

export default SyncHistory;
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';
import { toast } from 'react-toastify';
import api from '../services/authService';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const DashboardContainer = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
`;

const Card = styled.div`
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 20px;
`;

const CardTitle = styled.h2`
  margin-top: 0;
  font-size: 1.2rem;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
`;

const PlatformCard = styled(Card)`
  display: flex;
  flex-direction: column;
`;

const PlatformStatus = styled.div<{ isActive: boolean }>`
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  
  &:before {
    content: '';
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background-color: ${props => props.isActive ? '#4caf50' : '#f44336'};
    margin-right: 8px;
  }
`;

const PlatformName = styled.span`
  font-weight: 500;
`;

const PlatformError = styled.div`
  color: #f44336;
  font-size: 0.9rem;
  margin-top: 5px;
`;

const ViewButton = styled(Link)`
  display: inline-block;
  background-color: #0f3460;
  color: white;
  text-decoration: none;
  padding: 8px 16px;
  border-radius: 4px;
  margin-top: auto;
  text-align: center;
  transition: background-color 0.3s;
  
  &:hover {
    background-color: #16213e;
  }
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
`;

const StatCard = styled(Card)`
  text-align: center;
`;

const StatValue = styled.div`
  font-size: 2rem;
  font-weight: bold;
  color: #0f3460;
  margin: 10px 0;
`;

const StatLabel = styled.div`
  color: #666;
  font-size: 0.9rem;
`;

const ChartContainer = styled(Card)`
  grid-column: 1 / -1;
  height: 300px;
`;

const LoadingMessage = styled.div`
  text-align: center;
  padding: 20px;
  color: #666;
`;

const ErrorMessage = styled.div`
  text-align: center;
  padding: 20px;
  color: #f44336;
`;

const Dashboard: React.FC = () => {
  const [platforms, setPlatforms] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({
    totalProducts: 0,
    lowStockProducts: 0,
    syncTasks: 0,
    completedSyncs: 0
  });
  const [syncHistory, setSyncHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
        // Fetch platforms
        const platformsResponse = await api.get('/platforms');
        const platformsData = platformsResponse.data;
        
        // Create platform objects
        const platformsList = Object.keys(platformsData.platforms).map(name => ({
          name,
          isActive: !platformsData.errors[name],
          error: platformsData.errors[name] || null
        }));
        
        setPlatforms(platformsList);
        
        // Fetch sync history for chart
        const syncHistoryResponse = await api.get('/sync/history');
        setSyncHistory(syncHistoryResponse.data);
        
        // Calculate stats
        let totalProducts = 0;
        let lowStockProducts = 0;
        
        // For demo purposes, we'll use placeholder data
        // In a real app, you would fetch this data from the API
        setStats({
          totalProducts: 1250,
          lowStockProducts: 45,
          syncTasks: 8,
          completedSyncs: 120
        });
        
        setError('');
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard data. Please try again.');
        toast.error('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };
    
    fetchDashboardData();
  }, []);
  
  // Prepare chart data
  const chartData = {
    labels: syncHistory.slice(0, 7).map((sync: any) => {
      const date = new Date(sync.started_at);
      return `${date.getMonth() + 1}/${date.getDate()}`;
    }).reverse(),
    datasets: [
      {
        label: 'Products Synced',
        data: syncHistory.slice(0, 7).map((sync: any) => sync.success_count).reverse(),
        backgroundColor: '#0f3460',
      },
      {
        label: 'Errors',
        data: syncHistory.slice(0, 7).map((sync: any) => sync.error_count).reverse(),
        backgroundColor: '#e94560',
      }
    ],
  };
  
  if (loading) {
    return <LoadingMessage>Loading dashboard data...</LoadingMessage>;
  }
  
  if (error) {
    return <ErrorMessage>{error}</ErrorMessage>;
  }
  
  return (
    <div>
      <h2>Dashboard</h2>
      
      <StatsGrid>
        <StatCard>
          <StatLabel>Total Products</StatLabel>
          <StatValue>{stats.totalProducts}</StatValue>
        </StatCard>
        
        <StatCard>
          <StatLabel>Low Stock Products</StatLabel>
          <StatValue>{stats.lowStockProducts}</StatValue>
        </StatCard>
        
        <StatCard>
          <StatLabel>Active Sync Tasks</StatLabel>
          <StatValue>{stats.syncTasks}</StatValue>
        </StatCard>
        
        <StatCard>
          <StatLabel>Completed Syncs</StatLabel>
          <StatValue>{stats.completedSyncs}</StatValue>
        </StatCard>
      </StatsGrid>
      
      <ChartContainer>
        <CardTitle>Sync History</CardTitle>
        {syncHistory.length > 0 ? (
          <Bar 
            data={chartData} 
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  position: 'top' as const,
                },
                title: {
                  display: false,
                },
              },
            }} 
          />
        ) : (
          <p>No sync history available</p>
        )}
      </ChartContainer>
      
      <h3>Platforms</h3>
      <DashboardContainer>
        {platforms.map((platform) => (
          <PlatformCard key={platform.name}>
            <CardTitle>{platform.name}</CardTitle>
            <PlatformStatus isActive={platform.isActive}>
              <PlatformName>{platform.isActive ? 'Active' : 'Inactive'}</PlatformName>
            </PlatformStatus>
            
            {platform.error && (
              <PlatformError>{platform.error}</PlatformError>
            )}
            
            <ViewButton to={`/products/${platform.name}`}>
              View Products
            </ViewButton>
          </PlatformCard>
        ))}
      </DashboardContainer>
    </div>
  );
};

export default Dashboard;
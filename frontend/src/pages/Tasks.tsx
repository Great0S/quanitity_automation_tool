import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import api from '../services/authService';
import { TASK_REFRESH_INTERVAL } from '../config';

const TasksContainer = styled.div`
  padding: 20px;
`;

const TaskCard = styled.div`
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 20px;
`;

const TaskHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
`;

const TaskTitle = styled.h3`
  margin: 0;
  color: #333;
`;

const TaskStatus = styled.span<{ status: string }>`
  padding: 5px 10px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  background-color: ${props => {
    switch (props.status) {
      case 'COMPLETED': return '#e8f5e9';
      case 'FAILED': return '#ffebee';
      case 'RUNNING': return '#e3f2fd';
      case 'PENDING': return '#fff8e1';
      default: return '#f5f5f5';
    }
  }};
  color: ${props => {
    switch (props.status) {
      case 'COMPLETED': return '#2e7d32';
      case 'FAILED': return '#c62828';
      case 'RUNNING': return '#1565c0';
      case 'PENDING': return '#f57f17';
      default: return '#757575';
    }
  }};
`;

const TaskDetails = styled.div`
  margin-top: 10px;
`;

const TaskProgress = styled.div`
  margin-top: 15px;
`;

const ProgressBar = styled.div`
  height: 8px;
  background-color: #e0e0e0;
  border-radius: 4px;
  margin-top: 5px;
  overflow: hidden;
`;

const ProgressFill = styled.div<{ progress: number }>`
  height: 100%;
  width: ${props => `${props.progress * 100}%`};
  background-color: #0f3460;
  border-radius: 4px;
  transition: width 0.3s ease;
`;

const TaskInfo = styled.div`
  display: flex;
  margin-top: 15px;
  font-size: 14px;
  color: #666;
`;

const TaskInfoItem = styled.div`
  margin-right: 20px;
`;

const NoTasks = styled.div`
  text-align: center;
  padding: 40px;
  color: #666;
`;

interface Task {
  id: string;
  name: string;
  description: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  progress: number;
  result: any;
  error: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
}

const Tasks: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const fetchTasks = async () => {
    try {
      const response = await api.get('/tasks');
      setTasks(response.data.tasks || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching tasks:', err);
      setError('Failed to load tasks. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchTasks();
    
    // Set up polling for task updates
    const interval = setInterval(fetchTasks, TASK_REFRESH_INTERVAL);
    
    return () => clearInterval(interval);
  }, []);
  
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };
  
  if (loading) {
    return <div className="loading-spinner"></div>;
  }
  
  if (error) {
    return <div className="alert alert-error">{error}</div>;
  }
  
  if (tasks.length === 0) {
    return <NoTasks>No tasks found. Start a task from the products or sync page.</NoTasks>;
  }
  
  return (
    <TasksContainer>
      <h2>Background Tasks</h2>
      <p>View the status of your background tasks</p>
      
      {tasks.map(task => (
        <TaskCard key={task.id}>
          <TaskHeader>
            <TaskTitle>{task.name}</TaskTitle>
            <TaskStatus status={task.status}>{task.status}</TaskStatus>
          </TaskHeader>
          
          <div>{task.description}</div>
          
          <TaskProgress>
            <div>Progress: {Math.round(task.progress * 100)}%</div>
            <ProgressBar>
              <ProgressFill progress={task.progress} />
            </ProgressBar>
          </TaskProgress>
          
          <TaskInfo>
            <TaskInfoItem>Created: {formatDate(task.created_at)}</TaskInfoItem>
            <TaskInfoItem>Updated: {formatDate(task.updated_at)}</TaskInfoItem>
            {task.metadata?.platform && (
              <TaskInfoItem>Platform: {task.metadata.platform}</TaskInfoItem>
            )}
          </TaskInfo>
          
          {task.status === 'FAILED' && task.error && (
            <TaskDetails>
              <div className="alert alert-error">Error: {task.error}</div>
            </TaskDetails>
          )}
          
          {task.status === 'COMPLETED' && task.result && (
            <TaskDetails>
              <div className="alert alert-success">
                Task completed successfully
                {task.metadata?.count && (
                  <div>Processed {task.metadata.count} items</div>
                )}
              </div>
            </TaskDetails>
          )}
        </TaskCard>
      ))}
    </TasksContainer>
  );
};

export default Tasks;
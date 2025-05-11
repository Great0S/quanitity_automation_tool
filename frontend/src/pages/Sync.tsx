import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { toast } from 'react-toastify';
import api from '../services/authService';
import { TASK_REFRESH_INTERVAL } from '../config';

const SyncContainer = styled.div`
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

const FormGroup = styled.div`
  margin-bottom: 20px;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
`;

const Select = styled.select`
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 10px;
`;

const CheckboxGroup = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
`;

const CheckboxLabel = styled.label`
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 5px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  
  &:hover {
    background-color: #f5f5f5;
  }
`;

const Checkbox = styled.input`
  margin-right: 5px;
`;

const Input = styled.input`
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 10px;
`;

const TextArea = styled.textarea`
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 10px;
  min-height: 100px;
`;

const Button = styled.button`
  background-color: #0f3460;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 10px 20px;
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

const TabContainer = styled.div`
  margin-bottom: 20px;
`;

const TabButtons = styled.div`
  display: flex;
  border-bottom: 1px solid #ddd;
  margin-bottom: 20px;
`;

const TabButton = styled.button<{ $active: boolean }>`
  padding: 10px 20px;
  background-color: ${props => props.$active ? '#0f3460' : 'transparent'};
  color: ${props => props.$active ? 'white' : '#333'};
  border: none;
  border-bottom: ${props => props.$active ? '2px solid #0f3460' : 'none'};
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    background-color: ${props => props.$active ? '#0f3460' : '#f5f5f5'};
  }
`;

const TabContent = styled.div`
  padding: 10px 0;
`;

const ProgressContainer = styled.div`
  margin-top: 20px;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 4px;
`;

const ProgressBar = styled.div`
  height: 10px;
  background-color: #eee;
  border-radius: 5px;
  margin-bottom: 10px;
  overflow: hidden;
`;

const ProgressFill = styled.div<{ $progress: number }>`
  height: 100%;
  width: ${props => props.$progress}%;
  background-color: #0f3460;
  border-radius: 5px;
  transition: width 0.3s ease;
`;

const ProgressText = styled.div`
  color: #666;
`;

const Sync: React.FC = () => {
  const navigate = useNavigate();
  
  // Platform state
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [sourcePlatform, setSourcePlatform] = useState<string>('');
  const [targetPlatforms, setTargetPlatforms] = useState<string[]>([]);
  
  // Sync options
  const [syncFields, setSyncFields] = useState<string[]>(['price', 'quantity', 'status']);
  const [batchSize, setBatchSize] = useState<number>(50);
  const [skuFilter, setSkuFilter] = useState<string>('');
  
  // Single product update
  const [singleSku, setSingleSku] = useState<string>('');
  const [singleProductData, setSingleProductData] = useState<string>('{\n  "price": 0,\n  "quantity": 0,\n  "status": "active"\n}');
  
  // Multi product update
  const [multiProductData, setMultiProductData] = useState<string>('[\n  {\n    "sku": "SKU1",\n    "data": {\n      "price": 10.99,\n      "quantity": 100\n    }\n  },\n  {\n    "sku": "SKU2",\n    "data": {\n      "price": 19.99,\n      "quantity": 50\n    }\n  }\n]');
  
  // Task state
  const [activeTab, setActiveTab] = useState<string>('platform-sync');
  const [loading, setLoading] = useState<boolean>(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskProgress, setTaskProgress] = useState<number>(0);
  const [taskMessage, setTaskMessage] = useState<string>('');
  
  // Load platforms on mount
  useEffect(() => {
    const fetchPlatforms = async () => {
      try {
        const response = await api.get('/platforms');
        const platformsList = response.data.platforms;
        
        setPlatforms(platformsList);
        
        if (platformsList.length > 0) {
          setSourcePlatform(platformsList[0]);
          setTargetPlatforms(platformsList.slice(1));
        }
      } catch (err) {
        console.error('Error fetching platforms:', err);
        toast.error('Failed to load platforms');
      }
    };
    
    fetchPlatforms();
  }, []);
  
  // Poll task status
  useEffect(() => {
    if (!taskId) return;
    
    const checkTaskStatus = async () => {
      try {
        const response = await api.get(`/tasks/${taskId}`);
        const task = response.data;
        
        setTaskProgress(task.progress || 0);
        
        if (task.status === 'completed') {
          setLoading(false);
          setTaskId(null);
          toast.success('Task completed successfully');
          
          // Show result summary
          if (task.result) {
            const result = task.result;
            toast.info(`Processed ${result.products} products: ${result.success} success, ${result.errors} errors`);
          }
        } else if (task.status === 'failed') {
          setLoading(false);
          setTaskId(null);
          toast.error(`Task failed: ${task.error}`);
        } else {
          // Still running
          setTaskMessage(task.metadata?.progress_message || 'Processing...');
        }
      } catch (err) {
        console.error('Error checking task status:', err);
      }
    };
    
    // Check immediately
    checkTaskStatus();
    
    // Set up polling
    const interval = setInterval(checkTaskStatus, TASK_REFRESH_INTERVAL);
    
    return () => {
      clearInterval(interval);
    };
  }, [taskId]);
  
  // Handle platform sync
  const handlePlatformSync = async () => {
    if (!sourcePlatform || targetPlatforms.length === 0) {
      toast.error('Please select source and target platforms');
      return;
    }
    
    try {
      setLoading(true);
      
      // Parse SKU filter
      const filterSkus = skuFilter.trim() ? skuFilter.split(',').map(sku => sku.trim()) : undefined;
      
      const response = await api.post('/sync', {
        source_platform: sourcePlatform,
        target_platforms: targetPlatforms,
        filter_skus: filterSkus,
        batch_size: batchSize,
        fields: syncFields
      });
      
      setTaskId(response.data.task_id);
      toast.info('Sync task started');
    } catch (err) {
      console.error('Error starting sync:', err);
      toast.error('Failed to start sync');
      setLoading(false);
    }
  };
  
  // Handle bulk update lowest stock
  const handleBulkUpdateLowestStock = async () => {
    try {
      setLoading(true);
      
      // Parse SKU filter
      const filterSkus = skuFilter.trim() ? skuFilter.split(',').map(sku => sku.trim()) : undefined;
      
      const response = await api.post('/sync/bulk-update-lowest-stock', {
        filter_skus: filterSkus
      });
      
      setTaskId(response.data.task_id);
      toast.info('Bulk update task started');
    } catch (err) {
      console.error('Error starting bulk update:', err);
      toast.error('Failed to start bulk update');
      setLoading(false);
    }
  };
  
  // Handle single product update
  const handleSingleProductUpdate = async () => {
    if (!singleSku) {
      toast.error('Please enter a SKU');
      return;
    }
    
    try {
      setLoading(true);
      
      // Parse product data
      let productData;
      try {
        productData = JSON.parse(singleProductData);
      } catch (e) {
        toast.error('Invalid JSON format for product data');
        setLoading(false);
        return;
      }
      
      const response = await api.post('/sync/update-product', {
        sku: singleSku,
        data: productData,
        target_platforms: targetPlatforms.length > 0 ? targetPlatforms : undefined
      });
      
      setLoading(false);
      
      // Show result
      if (response.data.status === 'success') {
        toast.success('Product updated successfully');
      } else if (response.data.status === 'partial') {
        toast.warning('Product partially updated (some platforms failed)');
      } else {
        toast.error('Failed to update product');
      }
    } catch (err) {
      console.error('Error updating product:', err);
      toast.error('Failed to update product');
      setLoading(false);
    }
  };
  
  // Handle multi product update
  const handleMultiProductUpdate = async () => {
    try {
      setLoading(true);
      
      // Parse product data
      let productsData;
      try {
        productsData = JSON.parse(multiProductData);
      } catch (e) {
        toast.error('Invalid JSON format for products data');
        setLoading(false);
        return;
      }
      
      const response = await api.post('/sync/update-products', {
        products: productsData,
        target_platforms: targetPlatforms.length > 0 ? targetPlatforms : undefined
      });
      
      setTaskId(response.data.task_id);
      toast.info('Multi-product update task started');
    } catch (err) {
      console.error('Error starting multi-product update:', err);
      toast.error('Failed to start multi-product update');
      setLoading(false);
    }
  };
  
  return (
    <SyncContainer>
      <Header>
        <Title>Product Synchronization</Title>
      </Header>
      
      <TabContainer>
        <TabButtons>
          <TabButton 
            $active={activeTab === 'platform-sync'} 
            onClick={() => setActiveTab('platform-sync')}
            disabled={loading}
          >
            Platform Sync
          </TabButton>
          <TabButton 
            $active={activeTab === 'bulk-update'} 
            onClick={() => setActiveTab('bulk-update')}
            disabled={loading}
          >
            Bulk Update
          </TabButton>
          <TabButton 
            $active={activeTab === 'single-product'} 
            onClick={() => setActiveTab('single-product')}
            disabled={loading}
          >
            Single Product
          </TabButton>
          <TabButton 
            $active={activeTab === 'multi-product'} 
            onClick={() => setActiveTab('multi-product')}
            disabled={loading}
          >
            Multi Product
          </TabButton>
        </TabButtons>
        
        {activeTab === 'platform-sync' && (
          <TabContent>
            <FormGroup>
              <Label>Source Platform</Label>
              <Select 
                value={sourcePlatform} 
                onChange={(e) => setSourcePlatform(e.target.value)}
                disabled={loading}
              >
                <option value="">Select Source Platform</option>
                {platforms.map(platform => (
                  <option key={platform} value={platform}>{platform}</option>
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
                      <Checkbox 
                        type="checkbox" 
                        checked={targetPlatforms.includes(platform)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setTargetPlatforms([...targetPlatforms, platform]);
                          } else {
                            setTargetPlatforms(targetPlatforms.filter(p => p !== platform));
                          }
                        }}
                        disabled={loading}
                      />
                      {platform}
                    </CheckboxLabel>
                  ))
                }
              </CheckboxGroup>
            </FormGroup>
            
            <FormGroup>
              <Label>Fields to Sync</Label>
              <CheckboxGroup>
                <CheckboxLabel>
                  <Checkbox 
                    type="checkbox" 
                    checked={syncFields.includes('price')}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSyncFields([...syncFields, 'price']);
                      } else {
                        setSyncFields(syncFields.filter(f => f !== 'price'));
                      }
                    }}
                    disabled={loading}
                  />
                  Price
                </CheckboxLabel>
                <CheckboxLabel>
                  <Checkbox 
                    type="checkbox" 
                    checked={syncFields.includes('quantity')}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSyncFields([...syncFields, 'quantity']);
                      } else {
                        setSyncFields(syncFields.filter(f => f !== 'quantity'));
                      }
                    }}
                    disabled={loading}
                  />
                  Quantity
                </CheckboxLabel>
                <CheckboxLabel>
                  <Checkbox 
                    type="checkbox" 
                    checked={syncFields.includes('status')}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSyncFields([...syncFields, 'status']);
                      } else {
                        setSyncFields(syncFields.filter(f => f !== 'status'));
                      }
                    }}
                    disabled={loading}
                  />
                  Status
                </CheckboxLabel>
              </CheckboxGroup>
            </FormGroup>
            
            <FormGroup>
              <Label>Batch Size</Label>
              <Input 
                type="number" 
                value={batchSize}
                onChange={(e) => setBatchSize(parseInt(e.target.value))}
                min="1"
                max="1000"
                disabled={loading}
              />
            </FormGroup>
            
            <FormGroup>
              <Label>SKU Filter (comma separated, leave empty for all)</Label>
              <Input 
                type="text" 
                value={skuFilter}
                onChange={(e) => setSkuFilter(e.target.value)}
                placeholder="SKU1, SKU2, SKU3"
                disabled={loading}
              />
            </FormGroup>
            
            <Button 
              onClick={handlePlatformSync}
              disabled={loading || !sourcePlatform || targetPlatforms.length === 0 || syncFields.length === 0}
            >
              {loading ? 'Processing...' : 'Start Sync'}
            </Button>
          </TabContent>
        )}
        
        {activeTab === 'bulk-update' && (
          <TabContent>
            <p>This will update all products with the lowest stock quantity found across all platforms.</p>
            
            <FormGroup>
              <Label>SKU Filter (comma separated, leave empty for all)</Label>
              <Input 
                type="text" 
                value={skuFilter}
                onChange={(e) => setSkuFilter(e.target.value)}
                placeholder="SKU1, SKU2, SKU3"
                disabled={loading}
              />
            </FormGroup>
            
            <Button 
              onClick={handleBulkUpdateLowestStock}
              disabled={loading || platforms.length < 2}
            >
              {loading ? 'Processing...' : 'Update Lowest Stock'}
            </Button>
          </TabContent>
        )}
        
        {activeTab === 'single-product' && (
          <TabContent>
            <FormGroup>
              <Label>Product SKU</Label>
              <Input 
                type="text" 
                value={singleSku}
                onChange={(e) => setSingleSku(e.target.value)}
                placeholder="Enter product SKU"
                disabled={loading}
              />
            </FormGroup>
            
            <FormGroup>
              <Label>Product Data (JSON)</Label>
              <TextArea 
                value={singleProductData}
                onChange={(e) => setSingleProductData(e.target.value)}
                disabled={loading}
              />
            </FormGroup>
            
            <FormGroup>
              <Label>Target Platforms</Label>
              <CheckboxGroup>
                {platforms.map(platform => (
                  <CheckboxLabel key={platform}>
                    <Checkbox 
                      type="checkbox" 
                      checked={targetPlatforms.includes(platform)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setTargetPlatforms([...targetPlatforms, platform]);
                        } else {
                          setTargetPlatforms(targetPlatforms.filter(p => p !== platform));
                        }
                      }}
                      disabled={loading}
                    />
                    {platform}
                  </CheckboxLabel>
                ))}
              </CheckboxGroup>
            </FormGroup>
            
            <Button 
              onClick={handleSingleProductUpdate}
              disabled={loading || !singleSku || !singleProductData}
            >
              {loading ? 'Processing...' : 'Update Product'}
            </Button>
          </TabContent>
        )}
        
        {activeTab === 'multi-product' && (
          <TabContent>
            <FormGroup>
              <Label>Products Data (JSON Array)</Label>
              <TextArea 
                value={multiProductData}
                onChange={(e) => setMultiProductData(e.target.value)}
                style={{ height: '200px' }}
                disabled={loading}
              />
            </FormGroup>
            
            <FormGroup>
              <Label>Target Platforms</Label>
              <CheckboxGroup>
                {platforms.map(platform => (
                  <CheckboxLabel key={platform}>
                    <Checkbox 
                      type="checkbox" 
                      checked={targetPlatforms.includes(platform)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setTargetPlatforms([...targetPlatforms, platform]);
                        } else {
                          setTargetPlatforms(targetPlatforms.filter(p => p !== platform));
                        }
                      }}
                      disabled={loading}
                    />
                    {platform}
                  </CheckboxLabel>
                ))}
              </CheckboxGroup>
            </FormGroup>
            
            <Button 
              onClick={handleMultiProductUpdate}
              disabled={loading || !multiProductData}
            >
              {loading ? 'Processing...' : 'Update Products'}
            </Button>
          </TabContent>
        )}
      </TabContainer>
      
      {loading && (
        <ProgressContainer>
          <ProgressBar>
            <ProgressFill $progress={taskProgress} />
          </ProgressBar>
          <ProgressText>
            {taskMessage || 'Processing...'}
          </ProgressText>
        </ProgressContainer>
      )}
    </SyncContainer>
  );
};

export default Sync;
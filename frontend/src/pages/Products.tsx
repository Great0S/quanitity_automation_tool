import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/authService';
import ProductTable from '../components/ProductTable';
import ProductEditModal from '../components/ProductEditModal';
import ImageModal from '../components/ImageModal';
import Pagination from '../components/Pagination';

const ProductsContainer = styled.div`
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
`;

const Header = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
`;

const Title = styled.h1`
  margin: 0;
  color: #0f3460;
`;

const PlatformSelector = styled.div`
  display: flex;
  background-color: #f5f5f5;
  border-radius: 8px;
  padding: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
`;

interface PlatformOptionProps {
  $active: boolean;
}

const PlatformOption = styled.button<PlatformOptionProps>`
  padding: 10px 16px;
  border-radius: 6px;
  border: none;
  background-color: ${props => props.$active ? '#0f3460' : 'transparent'};
  color: ${props => props.$active ? 'white' : '#333'};
  font-weight: ${props => props.$active ? '600' : '400'};
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background-color: ${props => props.$active ? '#0f3460' : '#e5e5e5'};
  }
  
  &:focus {
    outline: none;
    box-shadow: 0 0 0 2px rgba(15, 52, 96, 0.2);
  }
`;

const PlatformDropdown = styled.select`
  padding: 10px 16px;
  border-radius: 6px;
  border: 1px solid #ddd;
  background-color: white;
  font-size: 16px;
  cursor: pointer;
  
  &:focus {
    outline: none;
    border-color: #0f3460;
    box-shadow: 0 0 0 2px rgba(15, 52, 96, 0.2);
  }
  
  @media (min-width: 768px) {
    display: none;
  }
`;

const PlatformButtons = styled.div`
  display: none;
  
  @media (min-width: 768px) {
    display: flex;
  }
`;

const LoadingContainer = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 200px;
  width: 100%;
  gap: 16px;
`;

const LoadingSpinner = styled.div`
  border: 4px solid #f3f3f3;
  border-top: 4px solid #0f3460;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const LoadingText = styled.div`
  font-size: 16px;
  color: #333;
  text-align: center;
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 40px;
  color: #666;
`;

const PaginationContainer = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
`;

const PageSizeSelector = styled.div`
  display: flex;
  align-items: center;
`;

const PageSizeLabel = styled.label`
  margin-right: 10px;
  font-size: 14px;
  color: #666;
`;

const PageSizeSelect = styled.select`
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ddd;
`;

const ActionsContainer = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
`;

const FetchButton = styled.button`
  background-color: #0f3460;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(15, 52, 96, 0.2);
  
  &:hover {
    background-color: #16213e;
    transform: translateY(-2px);
    box-shadow: 0 6px 8px rgba(15, 52, 96, 0.3);
  }
  
  &:active {
    transform: translateY(0);
    box-shadow: 0 2px 4px rgba(15, 52, 96, 0.2);
  }
  
  &:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
  
  svg {
    width: 20px;
    height: 20px;
  }
`;

const DataSourceInfo = styled.div`
  font-size: 14px;
  color: #666;
  font-style: italic;
  background-color: #f9f9f9;
  padding: 8px 12px;
  border-radius: 6px;
  border-left: 4px solid #0f3460;
`;

interface Product {
  sku: string;
  data: {
    title?: string;
    price?: number;
    quantity?: number;
    status?: string;
    image_url?: string;
    [key: string]: any;
  };
}

interface ProductUpdateData {
  sku: string;
  data?: Record<string, any>;
}

const Products: React.FC = () => {
  const { platform } = useParams<{ platform: string }>();
  const navigate = useNavigate();
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [products, setProducts] = useState<Record<string, Product[]>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [fetchingFromApi, setFetchingFromApi] = useState<boolean>(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [totalItems, setTotalItems] = useState<number>(0);
  const [dataSource, setDataSource] = useState<Record<string, 'api' | 'db'>>({});
  
  // Fetch available platforms
  useEffect(() => {
    const fetchPlatforms = async () => {
      try {
        const response = await api.get('/platforms');
        setPlatforms(response.data.platforms);
        
        // Initialize loading state for each platform
        const loadingState: Record<string, boolean> = {};
        const dataSourceState: Record<string, 'api' | 'db'> = {};
        response.data.platforms.forEach((p: string) => {
          loadingState[p] = false;
          dataSourceState[p] = 'db'; // Default to database
        });
        setLoading(loadingState);
        setDataSource(dataSourceState);
        
        // If no platform is selected, navigate to the first one
        if (!platform && response.data.platforms.length > 0) {
          navigate(`/products/${response.data.platforms[0]}`);
        }
      } catch (error) {
        console.error('Error fetching platforms:', error);
      }
    };
    
    fetchPlatforms();
  }, []);
  
  // Fetch products for the selected platform
  useEffect(() => {
    if (platform) {
      fetchProducts(platform, false);
    }
  }, [platform, currentPage, pageSize]);
  
  const fetchProducts = async (platformName: string, forceRefresh: boolean = false) => {
    if (forceRefresh) {
      setFetchingFromApi(true);
    } else {
      setLoading(prev => ({ ...prev, [platformName]: true }));
    }
    
    try {
      // Build query parameters based on platform
      const params: Record<string, any> = {
        force_refresh: forceRefresh
      };
      
      // Add platform-specific pagination parameters
      switch (platformName) {
        case 'N11':
          params.page = currentPage;
          params.size = pageSize;
          break;
        case 'Trendyol':
          params.page = currentPage - 1; // Trendyol uses 0-based indexing
          params.size = pageSize;
          break;
        case 'Hepsiburada':
          params.page = currentPage;
          params.size = pageSize;
          break;
        default:
          params.page = currentPage;
          params.size = pageSize;
      }
      
      // Make the API request
      const response = await api.get(`/products/${platformName}`, { params });
      const taskId = response.data.task_id;
      
      // Poll for task completion
      const checkTask = async () => {
        try {
          const taskResponse = await api.get(`/tasks/${taskId}`);
          
          if (taskResponse.data.status === 'completed') {
            // Get the products from the task result
            const result = taskResponse.data.result || {};
            
            // Update state with the products and pagination info
            if (result.items && Array.isArray(result.items)) {
              setProducts(prev => ({
                ...prev,
                [platformName]: result.items
              }));
              
              setTotalItems(result.total || 0);
              
              // Update data source
              setDataSource(prev => ({
                ...prev,
                [platformName]: forceRefresh ? 'api' : 'db'
              }));
            } else {
              // Handle case where result is directly an array of products
              const productArray = Array.isArray(result) ? result : [];
              setProducts(prev => ({
                ...prev,
                [platformName]: productArray
              }));
              
              setTotalItems(productArray.length);
              
              // Update data source
              setDataSource(prev => ({
                ...prev,
                [platformName]: forceRefresh ? 'api' : 'db'
              }));
            }
            
            setLoading(prev => ({ ...prev, [platformName]: false }));
            setFetchingFromApi(false);
          } else if (taskResponse.data.status === 'failed') {
            console.error(`Failed to fetch products: ${taskResponse.data.error}`);
            setLoading(prev => ({ ...prev, [platformName]: false }));
            setFetchingFromApi(false);
          } else {
            // Still running, check again in 2 seconds
            setTimeout(checkTask, 2000);
          }
        } catch (error) {
          console.error('Error checking task status:', error);
          setLoading(prev => ({ ...prev, [platformName]: false }));
          setFetchingFromApi(false);
        }
      };
      
      checkTask();
    } catch (error) {
      console.error(`Error fetching ${platformName} products:`, error);
      setLoading(prev => ({ ...prev, [platformName]: false }));
      setFetchingFromApi(false);
    }
  };
  
  // Handle platform selection
  const handlePlatformChange = (platformName: string) => {
    setCurrentPage(1); // Reset to first page when changing platforms
    navigate(`/products/${platformName}`);
  };
  
  // Handle edit button click
  const handleEditClick = (product: Product) => {
    setSelectedProduct(product);
    setIsEditModalOpen(true);
  };
  
  // Handle image click to enlarge
  const handleImageClick = (imageUrl: string) => {
    setSelectedImage(imageUrl);
  };
  
  // Handle product update
  const handleProductUpdate = async (updatedProduct: ProductUpdateData) => {
    if (!platform) return;
    
    try {
      await api.post(`/products/${platform}`, [updatedProduct]);
      
      // Update local state
      setProducts(prev => {
        const updatedProducts = [...(prev[platform] || [])];
        const index = updatedProducts.findIndex(p => p.sku === updatedProduct.sku);
        if (index !== -1) {
          // Create a new product object with updated data
          const newProduct = { ...updatedProducts[index] };
          
          // Update all fields from updatedProduct.data
          if (updatedProduct.data) {
            Object.entries(updatedProduct.data).forEach(([key, value]) => {
              newProduct.data[key] = value;
            });
          }
          
          updatedProducts[index] = newProduct;
        }
        return {
          ...prev,
          [platform]: updatedProducts
        };
      });
      
      setIsEditModalOpen(false);
      setSelectedProduct(null);
    } catch (error) {
      console.error('Error updating product:', error);
    }
  };
  
  // Handle page change
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };
  
  // Handle page size change
  const handlePageSizeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newSize = parseInt(e.target.value);
    setPageSize(newSize);
    setCurrentPage(1); // Reset to first page when changing page size
  };
  
  // Handle fetch from API button click
  const handleFetchFromAPI = () => {
    if (platform) {
      fetchProducts(platform, true);
    }
  };
  
  // Get loading message based on platform and source
  const getLoadingMessage = () => {
    if (!platform) return "Loading...";
    
    if (fetchingFromApi) {
      return `Fetching products from ${platform} API...`;
    } else {
      return `Loading products from database for ${platform}...`;
    }
  };
  
  return (
    <ProductsContainer>
      <Header>
        <Title>Products</Title>
        
        <PlatformSelector>
          {/* Mobile dropdown selector */}
          <PlatformDropdown 
            value={platform || ''} 
            onChange={(e) => handlePlatformChange(e.target.value)}
          >
            {platforms.map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </PlatformDropdown>
          
          {/* Desktop button selector */}
          <PlatformButtons>
            {platforms.map(p => (
              <PlatformOption 
                key={p} 
                $active={p === platform}
                onClick={() => handlePlatformChange(p)}
              >
                {p}
              </PlatformOption>
            ))}
          </PlatformButtons>
        </PlatformSelector>
      </Header>
      
      {platform && (
        <ActionsContainer>
          {products[platform]?.length > 0 && (
            <DataSourceInfo>
              Data source: {dataSource[platform] === 'api' ? 'API (live data)' : 'Database (cached data)'}
            </DataSourceInfo>
          )}
          <FetchButton 
            onClick={handleFetchFromAPI} 
            disabled={fetchingFromApi}
          >
            {fetchingFromApi ? 'Fetching from API...' : 'Fetch from API'}
            {fetchingFromApi && (
              <LoadingSpinner style={{ width: '20px', height: '20px' }} />
            )}
            {!fetchingFromApi && (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 4V2.21c0-.45-.54-.67-.85-.35l-2.8 2.79c-.2.2-.2.51 0 .71l2.79 2.79c.32.31.86.09.86-.36V6c3.31 0 6 2.69 6 6 0 .79-.15 1.56-.44 2.25-.15.36-.04.77.23 1.04.51.51 1.37.33 1.64-.34.37-.91.57-1.91.57-2.95 0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-.79.15-1.56.44-2.25.15-.36.04-.77-.23-1.04-.51-.51-1.37-.33-1.64.34C4.2 9.96 4 10.96 4 12c0 4.42 3.58 8 8 8v1.79c0 .45.54.67.85.35l2.79-2.79c.2-.2.2-.51 0-.71l-2.79-2.79c-.31-.31-.85-.09-.85.36V18z"/>
              </svg>
            )}
          </FetchButton>
        </ActionsContainer>
      )}
      
      {platform && (loading[platform] || fetchingFromApi) ? (
        <LoadingContainer>
          <LoadingSpinner />
          <LoadingText>{getLoadingMessage()}</LoadingText>
        </LoadingContainer>
      ) : platform && products[platform]?.length > 0 ? (
        <>
          <ProductTable 
            products={products[platform] || []} 
            onEditClick={handleEditClick}
            onImageClick={handleImageClick}
            platform={platform}
          />
          
          <PaginationContainer>
            <PageSizeSelector>
              <PageSizeLabel>Items per page:</PageSizeLabel>
              <PageSizeSelect value={pageSize} onChange={handlePageSizeChange}>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={500}>500</option>
              </PageSizeSelect>
            </PageSizeSelector>
            
            <Pagination 
              currentPage={currentPage}
              totalItems={totalItems}
              pageSize={pageSize}
              onPageChange={handlePageChange}
            />
          </PaginationContainer>
        </>
      ) : platform ? (
        <EmptyState>
          <p>No products found for {platform}</p>
          <p>The database is empty. Click "Fetch from API" to initialize products.</p>
        </EmptyState>
      ) : null}
      
      {isEditModalOpen && selectedProduct && platform && (
        <ProductEditModal
          product={selectedProduct}
          onClose={() => setIsEditModalOpen(false)}
          onSave={handleProductUpdate}
          platform={platform}
        />
      )}
      
      {selectedImage && (
        <ImageModal
          imageUrl={selectedImage}
          onClose={() => setSelectedImage(null)}
        />
      )}
    </ProductsContainer>
  );
};

export default Products;
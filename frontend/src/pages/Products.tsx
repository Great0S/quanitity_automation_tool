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
  justify-content: center;
  align-items: center;
  height: 200px;
  width: 100%;
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
  [key: string]: any;
}

const Products: React.FC = () => {
  const { platform } = useParams<{ platform: string }>();
  const navigate = useNavigate();
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [products, setProducts] = useState<Record<string, Product[]>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [totalItems, setTotalItems] = useState<number>(0);
  
  // Fetch available platforms
  useEffect(() => {
    const fetchPlatforms = async () => {
      try {
        const response = await api.get('/platforms');
        setPlatforms(response.data.platforms);
        
        // Initialize loading state for each platform
        const loadingState: Record<string, boolean> = {};
        response.data.platforms.forEach((p: string) => {
          loadingState[p] = false;
        });
        setLoading(loadingState);
        
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
      fetchProducts(platform);
    }
  }, [platform, currentPage, pageSize]);
  
  const fetchProducts = async (platformName: string) => {
    setLoading(prev => ({ ...prev, [platformName]: true }));
    
    try {
      // Build query parameters based on platform
      const params: Record<string, any> = {};
      
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
          params.offset = (currentPage - 1) * pageSize;
          params.limit = pageSize;
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
            } else {
              // Handle case where result is directly an array of products
              const productArray = Array.isArray(result) ? result : [];
              setProducts(prev => ({
                ...prev,
                [platformName]: productArray
              }));
              
              setTotalItems(productArray.length);
            }
            
            setLoading(prev => ({ ...prev, [platformName]: false }));
          } else if (taskResponse.data.status === 'failed') {
            console.error(`Failed to fetch products: ${taskResponse.data.error}`);
            setLoading(prev => ({ ...prev, [platformName]: false }));
          } else {
            // Still running, check again in 2 seconds
            setTimeout(checkTask, 2000);
          }
        } catch (error) {
          console.error('Error checking task status:', error);
          setLoading(prev => ({ ...prev, [platformName]: false }));
        }
      };
      
      checkTask();
    } catch (error) {
      console.error(`Error fetching ${platformName} products:`, error);
      setLoading(prev => ({ ...prev, [platformName]: false }));
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
          
          // Update all fields from updatedProduct
          Object.entries(updatedProduct).forEach(([key, value]) => {
            if (key !== 'sku') {
              newProduct.data[key] = value;
            }
          });
          
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
      
      {platform && loading[platform] ? (
        <LoadingContainer>
          <LoadingSpinner />
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